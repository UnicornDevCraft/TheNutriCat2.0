"""Utility functions for handling menus and their organization in the application."""


def organize_recipes_by_day(recipes: list, days_of_week: list, meal_types: list) -> dict:
    """
    Organize recipes by day of the week and meal type.
    Args:
        recipes (list): List of Recipe objects to be organized.
        days_of_week (list): List of day tags.
        meal_types (list): List of meal type tags.
    Returns:
        result (dict): A dictionary with days of the week as keys and meal types as sub-keys,
                       containing lists of recipe IDs and titles.
    """
    result = {}
    for day_tag in days_of_week:
        result[day_tag.name] = {mt.name: [] for mt in meal_types}

    for recipe in recipes:
        tag_types = {tag.type: tag.name for tag in recipe.tags}
        day = tag_types.get("day_of_week")
        meal = tag_types.get("meal_type")

        if day and meal and day in result and meal in result[day]:
            result[day][meal].append(
                {"id": recipe.id, "title": recipe.title.capitalize()}
            )

    return result


def to_structured_list(lines: list) -> list:
    """
    Convert a list of lines into a structured list of categories and items.
    Args:
        lines (list): List of lines to be structured.
    Returns:
        structured_list (list): Structured list of categories and items.
    """
    # Initialize the structured list
    structured_list = []
    current_category = None
    current_items = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.isupper():
            if current_category:
                structured_list.append(
                    {"category": current_category, "items": current_items}
                )
            # start a new category
            current_category = stripped
            current_items = []
        else:
            current_items.append(stripped)

    # Add the final category block
    if current_category and current_items:
        structured_list.append({"category": current_category, "items": current_items})

    return structured_list


def build_shopping_info(menu_shopping_info: object) -> dict:
    """
    Build structured shopping information from the menu shopping info object.
    Args:
        menu_shopping_info (MenuShoppingInfo): The menu shopping info object containing text data.
    Returns:
        shopping_info (dict): A dictionary containing structured shopping information.
    """
    shopping_info = {}

    if menu_shopping_info:
        shopping_info["rules_and_tips"] = (
            [
                line
                for line in menu_shopping_info.rules_and_tips_text.replace(
                    "\\n", "\n"
                ).split("\n")
                if line.strip().startswith("*")
            ]
            if menu_shopping_info.rules_and_tips_text
            else ""
        )

        shopping_info["preparations"] = (
            [
                line
                for line in menu_shopping_info.preparations_text.replace(
                    "\\n", "\n"
                ).split("\n")[1:]
                if line.strip()
            ]
            if menu_shopping_info.preparations_text
            else ""
        )

        shopping_info["shopping_list"] = (
            to_structured_list(
                menu_shopping_info.shopping_list_text.replace("\\n", "\n").split("\n")[
                    1:
                ]
            )
            if menu_shopping_info.shopping_list_text
            else ""
        )

        shopping_info["meat_marinades"] = (
            to_structured_list(
                menu_shopping_info.meat_marinades_text.replace("\\n", "\n").split("\n")[
                    1:
                ]
            )
            if menu_shopping_info.meat_marinades_text
            else ""
        )

        shopping_info["dressings"] = (
            to_structured_list(
                menu_shopping_info.dressings_text.replace("\\n", "\n").split("\n")[1:]
            )
            if menu_shopping_info.dressings_text
            else ""
        )

    return shopping_info
