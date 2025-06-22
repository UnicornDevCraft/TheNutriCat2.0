from nutri_app.forms import RegistrationForm
from nutri_app.models import User

def test_registration_form_valid(client, app):
    with app.app_context():
        form = RegistrationForm(data={
            'email': 'newuser@example.com',
            'password': 'secret123',
            'confirmation': 'secret123',
            'terms': True,
            # Recaptcha field might be disabled in tests or use test keys
        })
        assert form.validate() is True

def test_register_user_success(client, app):
    # This POST simulates submitting the registration form
    response = client.post("/auth/register", data={
        "email": "newuser@example.com",
        "password": "secret123",
        "confirmation": "secret123",
        "terms": True,
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"success." in response.data
    
    # Check user created in DB
    with app.app_context():
        for rule in app.url_map.iter_rules():
            print(rule)
        user = User.query.filter_by(email="newuser@example.com").first()
        assert user is not None


    
