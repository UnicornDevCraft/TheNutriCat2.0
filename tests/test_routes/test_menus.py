def test_menus_page_get(test_client):
    """
    GIVEN a Flask application
    WHEN the '/menus' page is requested (GET)
    THEN check that the response is valid
    """
    response = test_client.get('/menus')

    assert response.status_code == 200
    assert 'Fast menu' in response.text
    assert 'Italian Cuisine Recipes: Delicious and Healthy' in response.text
    assert 'Please press <b>"Show menu"</b> to view the details!' in response.text

def test_get_weekly_menu_success(test_client):
    """
    GIVEN a valid menu_name with associated tags and recipes
    WHEN the '/menus/<menu_name>' endpoint is requested
    THEN return 200 and structured JSON with recipes_by_day and shopping_info
    """
    response = test_client.get("/menus/Fast")
    assert response.status_code == 200

    data = response.get_json()
    assert data["menu"] == "Fast"
    assert "recipes_by_day" in data
    assert isinstance(data["recipes_by_day"], dict)

    assert "shopping_info" in data

def test_get_weekly_menu_not_found(test_client):
    """
    GIVEN an invalid menu_name
    WHEN the endpoint is requested
    THEN return 404 and an error message
    """
    response = test_client.get("/menus/ThisMenuDoesNotExist")
    assert response.status_code == 404

    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"]

def test_get_weekly_menu_empty_recipe_list_returns_404(test_client, session):
    """
    GIVEN an empty menu with no related recipes
    WHEN the endpoint is requested
    THEN return 404 and an error message
    """
    from nutri_app.models import Tag
    empty_menu = Tag(name="EmptyMenu", type="menu_name")
    session.add(empty_menu)
    session.commit()

    response = test_client.get("/menus/EmptyMenu")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_get_categories(test_client):
    """
    GIVEN a Flask application
    WHEN the '/menus/categories' endpoint is requested
    THEN check that the response contains the expected categories
    """
    response = test_client.get('/menus/categories')
    data = response.get_json()

    assert response.status_code == 200
    assert data[0]["name"] == "Fast"
    assert data[1]["name"] == "Italian"
    assert data[2]["name"] == "Summer"
    assert "image_url" in data[0]
    assert data[0]["image_url"].startswith("https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/")
    assert data[1]["image_url"].startswith("https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/")
    assert data[2]["image_url"].startswith("https://nutri-cat-images.s3.eu-central-1.amazonaws.com/compressed_images/")

def test_get_categories_handles_less_than_3_categories(test_client, session):
    """
    GIVEN only one category as Solo tag
    WHEN the '/menus/categories' endpoint is requested
    THEN check that the response contains the expected category name and image
    """
    from nutri_app.models import Tag
    session.query(Tag).filter_by(type="menu_name").delete()
    session.add(Tag(name="Solo", type="menu_name"))
    session.commit()

    response = test_client.get("/menus/categories")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert "Solo" in data[0]["name"]
