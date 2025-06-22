from nutri_app.models import User


def test_user_model(app):
    user = User(username="test", email="test@example.com")
    assert user.email == "test@example.com"