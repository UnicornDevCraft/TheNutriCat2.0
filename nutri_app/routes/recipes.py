"""Recipe management routes."""

import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import joinedload

from nutri_app import db
from nutri_app.models import (
    Favorite,
    Ingredient,
    Recipe,
    Tag,
)
from nutri_app.utils import (
    delete_s3_image,
    get_tag_options,
    update_instructions,
    update_ingredients,
    update_tags,
    update_notes,
    upload_image,
)


bp = Blueprint("recipes", __name__)
logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    """Render the index page with a list of first 7 recipes."""
    # Fetch first 7 recipes
    recipes = Recipe.query.limit(7).all()

    favorite_recipes = [
        {
            "name": recipe.title.capitalize(),
            "id": recipe.id,
            "time": (recipe.prep_time or 0) + (recipe.cook_time or 0),
            "image": recipe.compressed_img_URL
            or "/static/img/recipes/placeholder-image.jpeg",
        }
        for recipe in recipes
    ]

    return render_template("recipes/index.html", favorites=favorite_recipes)


@bp.route("/search")
def search():
    """Search for recipes by title."""
    q = request.args.get("q", "")
    if q:
        results = Recipe.query.filter(Recipe.title.ilike(f"%{q}%")).limit(10).all()
    else:
        results = []
        logger.warning("The recipes for this search were not found!")

    return jsonify(
        [
            {
                "title": r.title.capitalize(),
                "id": r.id,
                "thumbnail": r.compressed_img_URL,
            }
            for r in results
        ]
    )


@bp.route("/recipes")
def recipes():
    search_query = request.args.get("search", "")
    filter_tag = request.args.get("filter", None)
    tag_type = request.args.get("tag_type")
    sort_order = request.args.get("sort", "default")
    page = request.args.get("page", 1, type=int)
    per_page = 9

    if current_user.is_authenticated:
        favorite_recipes_ids = (
            Favorite.query.filter_by(user_id=current_user.id)
            .with_entities(Favorite.recipe_id)
            .all()
        )
        favorite_recipe_ids_set = {recipe_id for recipe_id, in favorite_recipes_ids}
    else:
        favorite_recipe_ids_set = set()

    tag_types = db.session.query(Tag.type).distinct().all()
    tag_options = get_tag_options(tag_types)

    # Full-text search query
    if search_query:
        # Search in title, ingredients, and instructions
        search_query_ts = func.websearch_to_tsquery("english", search_query)
        search_conditions = Recipe.title_search.op("@@")(search_query_ts)

        query = (
            db.session.query(Recipe)
            .join(Recipe.ingredients)
            .join(Recipe.instructions)
            .filter(search_conditions)
            .distinct(Recipe.id)
        )

    else:
        # Base query for recipes
        query = Recipe.query.options(joinedload(Recipe.tags))

    # Apply filter if a tag name is selected
    if filter_tag:
        if filter_tag == "favorites":
            query = query.filter(Recipe.id.in_(favorite_recipe_ids_set))
        else:
            query = query.join(Recipe.tags).filter(Tag.name == filter_tag)
    elif tag_type:
        query = query.join(Recipe.tags).filter(Tag.type == tag_type)

    # Apply sorting by title
    if sort_order == "asc":
        query = query.order_by(asc(Recipe.title))
    elif sort_order == "desc":
        query = query.order_by(desc(Recipe.title))
    else:
        query = query.order_by(Recipe.id.asc())

    # Pagination
    paginated_recipes = query.paginate(page=page, per_page=per_page, error_out=False)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "recipes": [
                    {
                        "title": recipe.title,
                        "compressed_img_URL": recipe.compressed_img_URL
                        or recipe.quality_img_URL
                        or recipe.local_image_path,
                        "prep_time": recipe.prep_time,
                        "cook_time": recipe.cook_time,
                        "tags": [{"name": tag.name} for tag in recipe.tags],
                        "favorite": recipe.id in favorite_recipe_ids_set,
                        "id": recipe.id,
                    }
                    for recipe in paginated_recipes.items
                ],
                "total_pages": paginated_recipes.pages,
                "user": True if current_user else False,
            }
        )
    # Render the recipes page
    return render_template(
        "recipes/recipes.html",
        recipes=paginated_recipes.items,
        tag_options=tag_options,
        page=page,
        total_pages=paginated_recipes.pages,
        sort_order=sort_order,
        favorite_recipe_ids_set=favorite_recipe_ids_set,
        user=current_user,
    )


@bp.route("/toggle_favorite/<int:recipe_id>", methods=["POST"])
@login_required
def toggle_favorite(recipe_id):
    """Toggle favorite status for a recipe."""
    recipe = Recipe.query.get(recipe_id)

    if not recipe:
        return jsonify({"success": False, "error": "Recipe not found"}), 404

    favorite = Favorite.query.filter_by(
        user_id=current_user.id, recipe_id=recipe_id
    ).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify(
            {"success": True, "favorite": False, "message": "Removed from favorites!"}
        )
    else:
        new_favorite = Favorite(user_id=current_user.id, recipe_id=recipe_id)
        db.session.add(new_favorite)
        db.session.commit()
        return jsonify(
            {"success": True, "favorite": True, "message": "Added to favorites!"}
        )


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new recipe."""
    if request.method == "POST":
        # Get form data
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

        # Fetch tags
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

        # Create new recipe
        recipe = Recipe(
            title=title.strip(),
            servings=servings,
            prep_time=prep_time,
            cook_time=cook_time,
        )
        # Add the recipe to the session
        db.session.add(recipe)
        db.session.flush()

        # Add ingredients
        update_ingredients(
            ingredient_names,
            quantities,
            units,
            quantity_notes,
            ingredient_notes,
            recipe,
        )
        # Add instructions
        update_instructions(instructions, steps, recipe)

        # Add tags
        update_tags(tag_list, recipe)

        # Add notes
        update_notes(notes, recipe, current_user.id)

        # Upload image
        image = request.files.get("image")
        upload_image(image, recipe)

        db.session.commit()
        flash("Recipe added successfully!", "success")
        return redirect(url_for("recipes.recipe_id", recipe_id=recipe.id))

    # If GET request, render the create recipe form
    ingredients = Ingredient.query.order_by(Ingredient.name).all()
    tags = Tag.query.order_by(Tag.name).all()
    return render_template("recipes/create.html", ingredients=ingredients, tags=tags)


@bp.route("/recipe/<int:recipe_id>/delete", methods=["POST"])
@login_required
def delete(recipe_id):
    """Delete a recipe."""
    recipe = Recipe.query.get_or_404(recipe_id)

    # Only allow delete if recipe has a 'my_recipe' tag
    if not any(tag.type == "my_recipe" for tag in recipe.tags):
        flash("You are not allowed to delete this recipe.", "error")
        return redirect(url_for("recipes.recipe_id", recipe_id=recipe.id))

    delete_s3_image(recipe.quality_img_URL)
    delete_s3_image(recipe.compressed_img_URL)

    db.session.delete(recipe)
    db.session.commit()
    flash("Recipe deleted successfully!", "success")
    return redirect(url_for("recipes.index"))
