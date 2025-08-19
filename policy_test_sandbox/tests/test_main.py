from app.main import debug_greet

def test_debug_greet(capsys):
    debug_greet('World')
    captured = capsys.readouterr()
    assert captured.out == 'Hello, World!\n'