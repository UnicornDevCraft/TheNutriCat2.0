
from nutri_app.utils import organize_recipes_by_day, to_structured_list, build_shopping_info
from tests.factories import RecipeFactory, TagFactory

def test_organize_recipes_empty_inputs():
    """
    GIVEN empty lists for recipes, days, and meals
    WHEN organize_recipes_by_day is called
    THEN it should return an empty dictionary
    """
    result = organize_recipes_by_day([], [], [])
    assert result == {}

def test_organize_recipes_by_day_with_factories(session):
    """
    GIVEN a session with recipes and tags created using factories
    WHEN organize_recipes_by_day is called
    THEN it should return a structured dictionary with recipes organized by day and meal type
    """
    monday = TagFactory(name="Monday-test", type="day_of_week")
    tuesday = TagFactory(name="Tuesday-test", type="day_of_week")
    breakfast = TagFactory(name="Breakfast-test", type="meal_type")
    dinner = TagFactory(name="Dinner-test", type="meal_type")

    # Create recipes with the right tags
    r1 = RecipeFactory(title="pancakes", tags=[monday, breakfast])
    r2 = RecipeFactory(title="spaghetti", tags=[monday, dinner])
    r3 = RecipeFactory(title="salad", tags=[tuesday, dinner])

    session.commit()

    result = organize_recipes_by_day(
        recipes=[r1, r2, r3],
        days_of_week=[monday, tuesday],
        meal_types=[breakfast, dinner]
    )

    assert result == {
        "Monday-test": {
            "Breakfast-test": [{"id": r1.id, "title": "Pancakes"}],
            "Dinner-test": [{"id": r2.id, "title": "Spaghetti"}]
        },
        "Tuesday-test": {
            "Breakfast-test": [],
            "Dinner-test": [{"id": r3.id, "title": "Salad"}]
        }
    }

def test_recipe_missing_day_of_week_is_skipped(session):
    """
    GIVEN a recipe that does not have a day of the week tag
    WHEN organize_recipes_by_day is called
    THEN it should not be included in the result
    """
    tuesday = TagFactory(name="Tuesday-test", type="day_of_week")
    dinner = TagFactory(name="Dinner-test", type="meal_type")

    recipe = RecipeFactory(title="orphan", tags=[dinner])

    session.commit()

    result = organize_recipes_by_day(
        recipes=[recipe],
        days_of_week=[tuesday],
        meal_types=[dinner]
    )

    assert result == {
        "Tuesday-test": {
            "Dinner-test": []
        }
    }

def test_to_structured_list_multiple_categories():
    """
    GIVEN a list of lines with multiple categories and items
    WHEN to_structured_list is called
    THEN it should return a structured list with categories and their items
    """
    lines = [
        "FRUITS",
        "Apple",
        "Banana",
        "VEGETABLES",
        "Carrot",
        "Spinach"
    ]

    expected = [
        {"category": "FRUITS", "items": ["Apple", "Banana"]},
        {"category": "VEGETABLES", "items": ["Carrot", "Spinach"]}
    ]

    assert to_structured_list(lines) == expected

def test_to_structured_list_ignores_empty_lines():
    """
    GIVEN a list of lines with empty lines and spaces
    WHEN to_structured_list is called
    THEN it should ignore empty lines and spaces, returning a structured list
    """
    lines = [
        "",
        "FRUITS",
        "  Apple  ",
        "",
        "Banana",
        "  ",
        "VEGETABLES",
        "  Carrot ",
        "",
        "Spinach"
    ]

    expected = [
        {"category": "FRUITS", "items": ["Apple", "Banana"]},
        {"category": "VEGETABLES", "items": ["Carrot", "Spinach"]}
    ]

    assert to_structured_list(lines) == expected

def test_to_structured_list_no_categories():
    """
    GIVEN a list of lines with no uppercase category headers
    WHEN to_structured_list is called
    THEN it should return an empty list as no structured categories can be formed
    """
    lines = [
        "apple",
        "banana",
        "carrot"
    ]

    expected = []

    assert to_structured_list(lines) == expected


def test_build_shopping_info_full_structure():
    """
    GIVEN a mock menu shopping info object with all sections filled
    WHEN build_shopping_info is called
    THEN it should return a structured dictionary with all sections correctly parsed
    """

    class MockInfo:
        rules_and_tips_text = "* One\n* Two\nNormal line"
        preparations_text = "PREPARATIONS\n1) Chop\n2) Marinate"
        shopping_list_text = "SHOPPING LIST\nVEGETABLES AND FRUITS:\nCabbage – 500 g\nCarrot – 500 g"
        meat_marinades_text = "MEAT MARINADES\nFRENCH MARINADE:\nLemon juice – 2 tbsp"
        dressings_text = "DRESSINGS:\nFRENCH:\nOlive oil – 3 tbsp"

    result = build_shopping_info(MockInfo())

    assert result["rules_and_tips"] == ["* One", "* Two"]
    assert result["preparations"] == ["1) Chop", "2) Marinate"]
    assert result["shopping_list"] == [
        {"category": "VEGETABLES AND FRUITS:", "items": ["Cabbage – 500 g", "Carrot – 500 g"]}
    ]
    assert result["meat_marinades"] == [
        {"category": "FRENCH MARINADE:", "items": ["Lemon juice – 2 tbsp"]}
    ]
    assert result["dressings"] == [
        {"category": "FRENCH:", "items": ["Olive oil – 3 tbsp"]}
    ]

def test_build_shopping_info_empty_fields():
    """ 
    GIVEN a mock menu shopping info object with empty fields
    WHEN build_shopping_info is called
    THEN it should return a structured dictionary with empty strings for those fields
    """

    class EmptyMockInfo:
        rules_and_tips_text = ""
        preparations_text = ""
        shopping_list_text = ""
        meat_marinades_text = ""
        dressings_text = ""

    result = build_shopping_info(EmptyMockInfo())
    assert result["rules_and_tips"] == ""
    assert result["preparations"] == ""
    assert result["shopping_list"] == ""
    assert result["meat_marinades"] == ""
    assert result["dressings"] == ""

def test_build_shopping_info_none_input():
    """ 
    GIVEN None as input for menu shopping info
    WHEN build_shopping_info is called
    THEN it should return an empty dictionary
    """
    result = build_shopping_info(None)
    assert result == {}
