"""Test cases for the authentication utility functions in nutri_app.utils.auth_utils"""

from freezegun import freeze_time
from itsdangerous import URLSafeTimedSerializer

from nutri_app.utils import generate_reset_token, verify_reset_token


def test_generate_reset_token_returns_token(app_with_secret, test_email):
    """
    GIVEN a valid email
    WHEN generate_reset_token is called
    THEN it should return a valid token string
    """
    token = generate_reset_token(test_email)
    assert isinstance(token, str)
    assert len(token) > 10

def test_token_can_be_decoded(app_with_secret, test_email, secret_key):
    """
    GIVEN a valid token generated from an email
    WHEN the token is decoded
    THEN it should return the original email
    """
    token = generate_reset_token(test_email)
    s = URLSafeTimedSerializer(secret_key)
    email = s.loads(token, salt="password-reset-salt")
    assert email == test_email

def test_verify_reset_token_with_valid_token(app_with_secret, test_email):
    """ 
    GIVEN a valid token generated from an email
    WHEN verify_reset_token is called
    THEN it should return the original email
    """ 
    token = generate_reset_token(test_email)
    email = verify_reset_token(token)
    assert email == test_email

def test_expired_token_returns_none(app_with_secret, test_email):
    """
    GIVEN a token that has expired
    WHEN verify_reset_token is called with max_age=0
    THEN it should return None      
    """
    with freeze_time("2025-03-01 12:00:00"):
        token = generate_reset_token(test_email)

    with freeze_time("2025-03-01 13:01:00"):
        result = verify_reset_token(token, max_age=3600)
    assert result is None

def test_invalid_token_returns_none(app_with_secret):
    """
    GIVEN an invalid token
    WHEN verify_reset_token is called
    THEN it should return None
    """
    bad_token = "this.is.not.valid"
    result = verify_reset_token(bad_token)
    assert result is None

def test_token_with_wrong_salt_returns_none(app_with_secret, test_email, secret_key):
    """
    GIVEN a token generated with a different salt
    WHEN verify_reset_token is called
    THEN it should return None
    """
    s = URLSafeTimedSerializer(secret_key)
    token = s.dumps(test_email, salt="different-salt")
    result = verify_reset_token(token)
    assert result is None