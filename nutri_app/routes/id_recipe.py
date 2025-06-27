from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from nutri_app import db
from nutri_app.models import (
    Recipe,
    RecipeIngredient,
    Ingredient,
    Instruction,
    UserRecipeNote,
    Favorite,
    Tag,
)
from nutri_app.utils import (
    get_recipe_ingredients,
    update_ingredients,
    update_instructions,
    update_tags,
    update_notes,
    upload_image,
)

bp = Blueprint("recipe_id", __name__)


@bp.route("/recipe/<int:recipe_id>")
def recipe_id(recipe_id):
    """Render the recipe detail page."""
    # Fetch recipe and eager-load relationships
    recipe = Recipe.query.options(
        joinedload(Recipe.tags),
        joinedload(Recipe.instructions),
        joinedload(Recipe.ingredients),
    ).get(recipe_id)

    if not recipe:
        abort(404, description=f"Recipe with ID {recipe_id} not found.")

    # Instructions (already eager-loaded, but sorted just in case)
    instructions = sorted(recipe.instructions, key=lambda x: x.step_number)

    # Format ingredient data as needed
    ingredients = get_recipe_ingredients(recipe_id)

    # Set up initial values
    has_my_recipe_tag = False
    note = None
    favorite_recipe_ids_set = set()

    # Favorite recipes set and notes
    if current_user:
        favorite_recipe_ids_set = {
            fav.recipe_id
            for fav in Favorite.query.filter_by(user_id=current_user.id).all()
        }
        note = UserRecipeNote.query.filter_by(
            user_id=current_user.id, recipe_id=recipe_id
        ).first()

        # Check if this recipe has a 'my_recipe' tag to determine if it's editable
        has_my_recipe_tag = any(tag.type == "my_recipe" for tag in recipe.tags)

    return render_template(
        "recipes/recipe_id.html",
        recipe=recipe,
        ingredients=ingredients,
        instructions=instructions,
        favorite_recipe_ids_set=favorite_recipe_ids_set,
        note=note,
        user=current_user,
        editable=has_my_recipe_tag,
    )


@bp.route("/recipe/<int:recipe_id>/edit", methods=("GET", "POST"))
@login_required
def edit(recipe_id):
    """Edit an existing recipe."""
    recipe = Recipe.query.get_or_404(recipe_id)
    # Only allow edit if recipe has a 'my_recipe' tag
    if not any(tag.type == "my_recipe" for tag in recipe.tags):
        flash("You are not allowed to delete this recipe.", "error")
        return redirect(url_for("recipes.recipe_id", recipe_id=recipe.id))

    if request.method == "POST":
        title = request.form.get("title")
        servings = request.form.get("servings", type=int)
        prep_time = request.form.get("prep_time", type=int)
        cook_time = request.form.get("cook_time", type=int)
        notes = request.form.get("notes")

        # Get ingredients data
        ingredient_names = request.form.getlist("ingredient_name[]")
        quantities = request.form.getlist("quantity[]")
        units = request.form.getlist("unit[]")
        quantity_notes = request.form.getlist("quantity_notes[]")
        ingredient_notes = request.form.getlist("ingredient_notes[]")

        # Get instructions data
        steps = request.form.getlist("step[]")
        instructions = request.form.getlist("instruction[]")

        # Get tags
        tag_list = request.form.getlist("tag[]")

        # Check for basic required fields
        if not title or not servings or not prep_time or not cook_time:
            flash("All fields marked with * are required.", "error")
            return redirect(request.referrer)

        if not ingredient_names or not any(name.strip() for name in ingredient_names):
            flash("At least one ingredient is required.", "error")
            return redirect(request.referrer)

        if not tag_list or not any(tag.strip() for tag in tag_list):
            flash("At least one tag is required.", "error")
            return redirect(request.referrer)

        if not steps or not instructions or not any(i.strip() for i in instructions):
            flash("At least one instruction is required.", "error")
            return redirect(request.referrer)

        # Update recipe details
        recipe.title = title.strip()
        recipe.servings = servings
        recipe.prep_time = prep_time
        recipe.cook_time = cook_time

        # Remove existing ingredients first and update
        recipe.ingredients.clear()
        update_ingredients(
            ingredient_names,
            quantities,
            units,
            quantity_notes,
            ingredient_notes,
            recipe,
        )

        # Remove existing instructions first and update
        recipe.instructions.clear()
        update_instructions(instructions, steps, recipe)

        # Remove existing tags first and update
        recipe.tags.clear()
        update_tags(tag_list, recipe)

        # Update notes
        update_notes(notes, recipe, current_user.id)

        # Upload image
        image = request.files.get("image")
        upload_image(image, recipe)

        db.session.commit()
        flash("Recipe updated successfully!", "success")
        return redirect(url_for("recipes.recipe_id", recipe_id=recipe.id))

    # If GET request, render the edit recipe form and pre-fill with current data
    ingredients = (
        db.session.query(RecipeIngredient, Ingredient)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe.id)
        .order_by(Ingredient.name)
        .all()
    )

    instructions = (
        Instruction.query.filter_by(recipe_id=recipe.id)
        .order_by(Instruction.step_number)
        .all()
    )

    tags = Tag.query.order_by(Tag.name).all()

    notes = UserRecipeNote.query.filter_by(
        user_id=current_user.id, recipe_id=recipe.id
    ).first()

    return render_template(
        "recipes/edit.html",
        recipe=recipe,
        ingredients=ingredients,
        instructions=instructions,
        tags=tags,
        notes=notes,
        user=current_user,
    )


@bp.route("/recipe/<int:recipe_id>/note", methods=["POST"])
@login_required
def save_note(recipe_id):
    """Save a note for a recipe."""
    note_text = request.form.get("note", "")
    note = UserRecipeNote.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()

    if note:
        note.note = note_text
    else:
        note = UserRecipeNote(
            user_id=current_user.id, recipe_id=recipe_id, note=note_text
        )
        db.session.add(note)

    db.session.commit()
    flash("Note saved successfully.", "success")
    return redirect(url_for("recipes.recipe_id", recipe_id=recipe_id, note=note_text))


@bp.route("/recipe/<int:recipe_id>/note/edit", methods=["POST"])
@login_required
def edit_note(recipe_id):
    """Edit an existing note for a recipe."""
    note = UserRecipeNote.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if note:
        note.note = request.form["note"]
        db.session.commit()
        flash("Note updated successfully.", "success")
    return redirect(url_for("recipes.recipe_id", recipe_id=recipe_id))


@bp.route("/recipe/<int:recipe_id>/note/delete", methods=["POST"])
@login_required
def delete_note(recipe_id):
    """Delete a note for a recipe."""
    note = UserRecipeNote.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()
    if note:
        db.session.delete(note)
        db.session.commit()
        flash("Note deleted.", "success")
    return redirect(url_for("recipes.recipe_id", recipe_id=recipe_id))
