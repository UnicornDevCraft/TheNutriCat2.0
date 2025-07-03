"""Token configuration for password reset"""

from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def generate_reset_token(user_email: str) -> str:
    """Generate a password reset token"""
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(user_email, salt="password-reset-salt")


def verify_reset_token(token: str, max_age=3600) -> str | None:
    """Verify the password reset token"""
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        return s.loads(token, salt="password-reset-salt", max_age=max_age)
    except Exception:
        return None
