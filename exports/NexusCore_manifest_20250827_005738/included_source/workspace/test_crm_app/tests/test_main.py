from app.main import add_user
import pytest


def test_add_user_valid_username():
    assert add_user("testuser") == True


def test_add_user_with_email():
    assert add_user("testuser", email="test@example.com") == True


def test_add_user_with_phone():
    assert add_user("testuser", phone="123-456-7890") == True


def test_add_user_with_address():
    assert add_user("testuser", address="123 Main St") == True


def test_add_user_with_all_info():
    assert add_user("testuser", email="test@example.com", phone="123-456-7890", address="123 Main St") == True


def test_add_user_invalid_username():
    # Assuming invalid username raises a TypeError
    with pytest.raises(TypeError):
        add_user(123)


def test_add_user_missing_username():
    # Assuming missing username raises a TypeError
    with pytest.raises(TypeError):
        add_user()


def test_add_user_duplicate_username():
  # Assuming attempting to add a duplicate username returns False
  add_user("duplicate_user")
  assert add_user("duplicate_user") == False