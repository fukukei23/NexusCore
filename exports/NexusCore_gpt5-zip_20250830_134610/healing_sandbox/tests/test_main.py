from app.main import greet
import pytest


def test_greet_valid_username():
    assert greet("John") == "Hello, John!"


def test_greet_empty_username():
    assert greet("") == "Hello, stranger!"


def test_greet_none_username():
    assert greet(None) == "Hello, stranger!"


def test_greet_special_characters():
    assert greet("!@#$%^&*") == "Hello, !@#$%^&*!"


def test_greet_long_username():
    long_username = "a" * 1000
    assert greet(long_username) == f"Hello, {long_username}!"


def test_greet_mixed_case_username():
    assert greet("jOhN") == "Hello, jOhN!"


def test_greet_username_with_spaces():
    assert greet("John Doe") == "Hello, John Doe!"