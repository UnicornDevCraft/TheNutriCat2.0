
import os
import pytest

from sqlalchemy.orm import scoped_session, sessionmaker

from nutri_app import create_app, db as test_db
from nutri_app.models import User

@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_CONFIG"] = "nutri_app.config.TestConfig"
    app = create_app()
    with app.app_context():
        yield app

@pytest.fixture(scope="session")
def db(app):
    with app.app_context():
        yield test_db

@pytest.fixture(scope="function")
def session(db):
    connection = db.engine.connect()
    transaction = connection.begin()

    Session = scoped_session(sessionmaker(bind=connection))
    db.session = Session
    yield Session

    transaction.rollback()
    connection.close()
    Session.remove()

@pytest.fixture(scope="function")
def test_client(app, session):
    return app.test_client()

@pytest.fixture
def secret_key():
    return "test-secret-key"

@pytest.fixture
def test_email():
    return "user@example.com"

@pytest.fixture
def app_with_secret(app, secret_key):
    app.config["SECRET_KEY"] = secret_key
    return app

@pytest.fixture(scope='module')
def new_user():
    user = User(username="testuser", email="test@example.com", password="")
    return user

@pytest.fixture(autouse=True)
def bind_factories(session):
    from tests.factories import RecipeFactory, TagFactory
    RecipeFactory._meta.sqlalchemy_session = session
    TagFactory._meta.sqlalchemy_session = session
