from nexuscore.utils import cleaner


def test_clean_error_msg_basic():
    msg = (
        "An error occurred while executing the following cell\n------------------\nValueError: bad"
    )
    cleaned = cleaner.clean_error_msg(msg)
    assert "ValueError" in cleaned
