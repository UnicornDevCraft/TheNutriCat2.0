
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

@pytest.fixture(scope='module')
def new_user():
    user = User(username="testuser", email="test@example.com", password="")
    return user
