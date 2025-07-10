import boto3
import logging
import mimetypes
import os
import uuid

from botocore.exceptions import ClientError
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from nutri_app import db
from nutri_app.models import (
    Tag,
    Ingredient,
    Instruction,
    RecipeIngredient,
    RecipeTag,
    UserRecipeNote,
)

logger = logging.getLogger(__name__)

# AWS S3 configuration
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
S3_FOLDER = os.getenv("AWS_S3_FOLDER")
# Image upload configuration
MAX_FILE_SIZE = 4 * 1024 * 1024


def get_tag_options(tag_types: list[tuple]) -> dict[str, list[str]]:
    """
    Get unique tag types and their names
    Args:
        tag_types (list[tuple]): List of tuples containing tag types.
    Returns:
        dict[str, list[str]]: Dictionary with tag type names as keys and lists of tag names as values.
    """
    tag_types = [t[0] for t in tag_types]
    tag_options = {}
    for t in tag_types:
        options = db.session.query(Tag.name).filter(Tag.type == t).distinct().all()
        options = [n[0] for n in options]
        if "day" in t:
            week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            options = sorted(
                options,
                key=lambda x: week_days.index(x) if x in week_days else len(week_days),
            )
            tag_name = "Day of the week"
        elif "meal" in t:
            meal_order = ["Breakfast", "Lunch", "Dinner", "Dessert"]
            options = sorted(
                options,
                key=lambda x: (
                    meal_order.index(x) if x in meal_order else len(meal_order)
                ),
            )
            tag_name = "Meals"
        elif "menu" in t:
            options = sorted(options)
            tag_name = "Menu"
        elif "my" in t:
            options = sorted(options)
            tag_name = "My recipes"
        else:
            tag_name = t

        tag_options[tag_name] = options
    return tag_options


def get_recipe_ingredients(recipe_id: int) -> list[str]:
    """
    Get ingredients for a recipe by its ID.
    Args:
        recipe_id (int): The ID of the recipe.
    Returns:
        list[str]: List of dictionaries containing ingredient details.
    """
    if not recipe_id:
        logger.error("Recipe ID is required to fetch ingredients.")
        return []

    recipe_ingredients = (
        RecipeIngredient.query.filter_by(recipe_id=recipe_id)
        .join(Ingredient)
        .add_entity(Ingredient)
        .all()
    )

    ingredients = [
        {
            "name": ingredient.name,
            "quantity": ri.quantity,
            "unit": ri.unit,
            "quantity_notes": ri.quantity_notes,
            "ingredient_notes": ri.ingredient_notes,
        }
        for ri, ingredient in recipe_ingredients
    ]

    return ingredients


def update_ingredients(
    ingredient_names: list, quantities: list, units: list, quantity_notes: list, ingredient_notes: list, recipe: object
) -> None:
    """
    Update the ingredients in the database.
    Args:
        ingredient_names (list): List of ingredient names.
        quantities (list): List of quantities for each ingredient.
        units (list): List of units for each ingredient.
        quantity_notes (list): List of notes for each quantity.
        ingredient_notes (list): List of notes for each ingredient.
        recipe (object): The recipe object to which the ingredients belong.
    """
    for i in range(len(ingredient_names)):
        name = ingredient_names[i].strip()
        if not name:
            continue
        ingredient = Ingredient.query.filter_by(name=name).first()
        if not ingredient:
            ingredient = Ingredient(name=name)
            db.session.add(ingredient)

        ri = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            quantity=quantities[i].strip() if i < len(quantities) else None,
            unit=units[i].strip() if i < len(units) else None,
            quantity_notes=(
                quantity_notes[i].strip() if i < len(quantity_notes) else None
            ),
            ingredient_notes=(
                ingredient_notes[i].strip() if i < len(ingredient_notes) else None
            ),
        )
        db.session.add(ri)

    logger.info("Ingredients updated successfully.")


def update_instructions(instructions: list[str], steps: list[str], recipe: object) -> None:
    """
    Update the instructions in the database.
    Args:
        instructions (list[str]): List of instruction strings.
        steps (list[str]): List of step numbers corresponding to each instruction.
        recipe (object): The recipe object to which the instructions belong.
    """
    for i in range(len(instructions)):
        line = instructions[i].strip()
        if not line:
            continue
        db.session.add(
            Instruction(
                recipe_id=recipe.id,
                step_number=steps[i].strip() if i < len(steps) else None,
                instruction=line,
            )
        )
    logger.info("Instructions updated successfully.")


def update_tags(tag_list: list[str], recipe: object) -> None:
    """
    Update the tags for a recipe.
    Args:
        tag_list (list[str]): List of tag names.
        recipe (object): The recipe object to which the tags belong.
    """
    for i in range(len(tag_list)):
        name = tag_list[i].strip()
        if not name:
            continue
        # Check if the tag already exists if it doesn't exist, create a new one
        tag = Tag.query.filter_by(name=name, type="my_recipe").first()
        if not tag:
            tag = Tag(name=name, type="my_recipe")
            db.session.add(tag)
        db.session.add(RecipeTag(recipe_id=recipe.id, tag_id=tag.id))
    logger.info("Tags updated successfully.")


def update_notes(recipe, notes: str, user_id: int) -> None:
    """Update the notes for a recipe.
    Args:
        recipe (object): The recipe object to which the notes belong.
        notes (str): The notes to be added or updated.
        user_id (int): The ID of the user adding the notes.
    """
    if notes:
        user_note = UserRecipeNote.query.filter_by(
            user_id=user_id, recipe_id=recipe.id
        ).first()
        if user_note:
            user_note.note = notes.strip()
        else:
            db.session.add(
                UserRecipeNote(user_id=user_id, recipe_id=recipe.id, note=notes.strip())
            )
    logger.info("Notes updated successfully.")


def upload_image(image: object, recipe: object) -> None:
    """
    Upload an image to S3 and update the recipe with the image URL.
    Args:
        image (object): The image file to be uploaded.
        recipe (object): The recipe object to which the image belongs.
    """
    if image and image.filename:
        image.seek(0, 2)  # Move cursor to end of file
        file_size = image.tell()  # Get current position (== file size in bytes)
        image.seek(0)  # Reset cursor back to beginning

        if file_size > MAX_FILE_SIZE:
            abort(400, description="File is too large. Maximum size is 4MB.")

        if recipe.quality_img_URL and recipe.compressed_img_URL:
            logger.info("Old images found, deleting them before uploading new ones.")
            # Delete old images from S3
            delete_s3_image(recipe.quality_img_URL)
            delete_s3_image(recipe.compressed_img_URL)

        filename = secure_filename(image.filename)

        # Get original extension
        original_name, ext = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4().hex}_{original_name}{ext}"

        # Get MIME type
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

        # Initialize S3 client
        s3 = boto3.client("s3", region_name=AWS_REGION)

        # Upload directly from memory using file-like object
        s3.upload_fileobj(
            image,
            S3_BUCKET_NAME,
            f"{S3_FOLDER}/{unique_filename}",
            ExtraArgs={"ContentType": content_type},
        )

        # Construct public URL
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{S3_FOLDER}/{unique_filename}"
        logger.info(f"✅ Upload successful! File URL: {file_url}")

        # Save to database
        recipe.quality_img_URL = file_url
        recipe.compressed_img_URL = file_url


def delete_s3_image(s3_url: str) -> None:
    """
    Delete an image from S3 given its public URL.
    Args:
        s3_url (str): The public URL of the image to be deleted.
    """
    s3 = boto3.client("s3")

    try:
        key = s3_url.split(f"{os.getenv("AWS_S3_BUCKET_LINK")}")[1]
        if not key:
            logger.error(f"Could not extract key from URL: {s3_url}")
            return

        logger.info(f"Attempting to delete key: {key} from bucket: {S3_BUCKET_NAME}")
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=key)
        logger.info(f"Successfully deleted {s3_url}!")

        # Confirm deletion
        s3.head_object(Bucket=S3_BUCKET_NAME, Key=key)
        logger.warning("File still exists after delete attempt!")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            logger.info("File is confirmed deleted.")
        else:
            logger.error(f"Error checking for deleted file: {e}")
    except Exception as e:
        logger.error(f"Failed to delete from S3: {e}")
