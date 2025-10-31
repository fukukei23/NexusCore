# my-crm-app/app/main.py
"""
Main application module for the CRM.

This module contains the core business logic.
"""

def hello_world(username: str) -> str:
    """
    Greets the user by their name.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: The complete greeting message.
    """
    if not isinstance(username, str) or not username:
        return "Hello, anonymous!"
    return f"Hello, {username}!"

def simple_greeting() -> str:
    """
    Returns a simple greeting message.

    This function provides a basic greeting.

    Returns:
        str: A string in the format 'Hello!'.
    """
    return "Hello!"

def greet_user(username: str) -> str:
    """
    Returns a greeting message for the given username.

    This function provides a personalized greeting message.

    Args:
        username (str): The name of the user to greet.

    Returns:
        str: A greeting message in the format 'Hello, [username]!'
    """
    return f"Hello, {username}!"

def greet(username: str = None) -> str:
    """
    Greets the user with a personalized message or a default message if the username is empty or null.
    Handles special characters and long usernames gracefully.

    Args:
        username (str): The name of the user to greet. Can be empty, null, or contain special characters.

    Returns:
        str: A greeting string. 'Hello, [username]!' if the username is provided, 
             and a suitable default message if the username is empty or null.
    """
    if username is None or not username:
        return "Hello, there!"
    else:
        return f"Hello, {username}!"