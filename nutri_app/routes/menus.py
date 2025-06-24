"""Routes for managing menus."""
import logging

from flask import Blueprint, jsonify, render_template
from sqlalchemy.orm import joinedload

from nutri_app.models import Recipe, Tag, MenuShoppingInfo
from nutri_app.utils import build_shopping_info, organize_recipes_by_day


bp = Blueprint("menus", __name__)
logger = logging.getLogger(__name__)


@bp.route('/menus')
def menus():
    """Render the menus page with a list of menu names."""
    return render_template("menus/menus.html")


@bp.route("/menus/<menu_name>", methods=["GET"])
def get_weekly_menu(menu_name):
    """Return structured weekly menu and shopping info for a given menu name."""
    menu_tag = Tag.query.filter_by(name=menu_name, type="menu_name").first()
    if not menu_tag:
        logger.warning(f"Menu '{menu_name}' not found.")
        return jsonify({"error": f"Menu '{menu_name}' not found."}), 404

    # Fetch the menu shopping information
    menu_shopping_info = MenuShoppingInfo.query.filter_by(menu_tag_id=menu_tag.id).first()

    # Preload tags for organizing recipes
    meal_types = Tag.query.filter_by(type="meal_type").all()
    days_of_week = Tag.query.filter_by(type="day_of_week").order_by(Tag.id).all()

    # Retrieve recipes matching the menu, day, and meal type
    recipes = (
        Recipe.query
        .join(Recipe.tags)
        .filter(
            Recipe.tags.any(id=menu_tag.id),
            Recipe.tags.any(Tag.type == "day_of_week"),
            Recipe.tags.any(Tag.type == "meal_type"),
            ~Recipe.tags.any(Tag.type == "my_recipe")
        )
        .options(joinedload(Recipe.tags))
        .all()
    )

    if recipes and meal_types and days_of_week:
        # Organize by day and meal type
        result = organize_recipes_by_day(recipes, days_of_week, meal_types)
    else:
        logger.warning(f"No recipes found for menu '{menu_name}'.")
        return jsonify({"error": f"Recipes for '{menu_name}' were not found."}), 404
    

    # Build shopping info if available        
    shopping_info = build_shopping_info(menu_shopping_info)
        
    # Return the JSON response including menu shopping info
    return jsonify({
        "menu": menu_name,
        "recipes_by_day": result,
        "shopping_info": shopping_info
    })


@bp.route("/menus/categories")
def get_categories():
    """Return a list of menu categories with associated images for search modal in nav.js."""
    categories = Tag.query.filter_by(type="menu_name").order_by(Tag.name.asc()).all()
    image_urls = [
        "https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/avocado_toast_with_egg_and_salad_compressed.jpg",
        "https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/chicken_lasagna_alla_genovese_compressed.jpg",
        "https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/guacamole_with_melon_and_lavash_nachos_compressed.jpg"
        ]

    fallback_image = "https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/avocado_toast_with_egg_and_salad_compressed.jpg"

    result = []
    for i, category in enumerate(categories):
        if i < len(image_urls):
            image_url = image_urls[i]
        else:
            logger.warning(f"No image available for menu category '{category.name}', using fallback image.")
            image_url = fallback_image

        result.append({
            "name": category.name,
            "image_url": image_url
        })

    return jsonify(result)
