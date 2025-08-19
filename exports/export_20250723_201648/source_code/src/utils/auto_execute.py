import subprocess
import tempfile
import os
import logging

def execute_python_code(code_text, timeout=10):
    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as tmp:
        tmp.write(code_text)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            timeout=timeout,
            text=True
        )
        output = result.stdout
        error = result.stderr
    finally:
        os.unlink(tmp_path)

    return output.strip(), error.strip()