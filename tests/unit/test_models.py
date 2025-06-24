


def test_new_user(new_user):
    """
    GIVEN a User model
    WHEN a new instance of User is created
    THEN check the email and password fields are defined correctly
    """
    new_user.set_password("secure123")

    assert new_user.email == "test@example.com"    
    assert new_user.password != "secure123"
    assert new_user.check_password("secure123") is True
    assert not new_user.check_password("wrongpass")