"""
Comprehensive tests for const module.
Tests security guard code constants and system prompts.
"""

import pytest
from nexuscore.utils.const import (
    TOOLS_CODE,
    write_denial_function,
    read_denial_function,
    class_denial,
    GUARD_CODE,
    CODE_INTERPRETER_SYSTEM_PROMPT,
)


# ==============================================================================
# TOOLS_CODE Tests
# ==============================================================================


class TestToolsCode:
    """Test TOOLS_CODE constant"""

    def test_tools_code_is_string(self):
        """TOOLS_CODE is a string"""
        assert isinstance(TOOLS_CODE, str)

    def test_tools_code_contains_imports(self):
        """TOOLS_CODE contains standard library imports"""
        assert "import numpy" in TOOLS_CODE
        assert "import pandas" in TOOLS_CODE
        assert "import matplotlib" in TOOLS_CODE
        assert "import seaborn" in TOOLS_CODE
        assert "from scipy import stats" in TOOLS_CODE

    def test_tools_code_contains_datetime(self):
        """TOOLS_CODE contains datetime import"""
        assert "from datetime import datetime" in TOOLS_CODE

    def test_tools_code_contains_torch(self):
        """TOOLS_CODE contains torch import"""
        assert "import torch" in TOOLS_CODE

    def test_tools_code_contains_web_scraping(self):
        """TOOLS_CODE contains web scraping libraries"""
        assert "import requests" in TOOLS_CODE
        assert "from bs4 import BeautifulSoup" in TOOLS_CODE

    def test_tools_code_contains_json(self):
        """TOOLS_CODE contains json import"""
        assert "import json" in TOOLS_CODE

    def test_tools_code_contains_sympy(self):
        """TOOLS_CODE contains sympy for symbolic math"""
        assert "from sympy import" in TOOLS_CODE

    def test_tools_code_not_empty(self):
        """TOOLS_CODE is not empty"""
        assert len(TOOLS_CODE.strip()) > 0


# ==============================================================================
# Denial Functions Tests
# ==============================================================================


class TestDenialFunctions:
    """Test denial function strings"""

    def test_write_denial_function_is_string(self):
        """write_denial_function is a string"""
        assert isinstance(write_denial_function, str)

    def test_write_denial_function_is_lambda(self):
        """write_denial_function is a lambda expression"""
        assert write_denial_function.startswith("lambda")

    def test_write_denial_function_raises_permission_error(self):
        """write_denial_function raises PermissionError"""
        assert "PermissionError" in write_denial_function
        assert "Writing to disk" in write_denial_function

    def test_read_denial_function_is_string(self):
        """read_denial_function is a string"""
        assert isinstance(read_denial_function, str)

    def test_read_denial_function_is_lambda(self):
        """read_denial_function is a lambda expression"""
        assert read_denial_function.startswith("lambda")

    def test_read_denial_function_raises_permission_error(self):
        """read_denial_function raises PermissionError"""
        assert "PermissionError" in read_denial_function
        assert "Reading from disk" in read_denial_function

    def test_class_denial_is_string(self):
        """class_denial is a string"""
        assert isinstance(class_denial, str)

    def test_class_denial_contains_class_definition(self):
        """class_denial contains class definition"""
        assert "Class Denial" in class_denial
        assert "__getattr__" in class_denial

    def test_class_denial_contains_safety_message(self):
        """class_denial contains safety message"""
        assert "not permitted due to safety reasons" in class_denial


# ==============================================================================
# GUARD_CODE Tests
# ==============================================================================


class TestGuardCode:
    """Test GUARD_CODE constant"""

    def test_guard_code_is_string(self):
        """GUARD_CODE is a string"""
        assert isinstance(GUARD_CODE, str)

    def test_guard_code_contains_os_module_guards(self):
        """GUARD_CODE guards os module dangerous functions"""
        assert "os.kill =" in GUARD_CODE
        assert "os.system =" in GUARD_CODE
        assert "os.remove =" in GUARD_CODE
        assert "os.rmdir =" in GUARD_CODE
        assert "os.chmod =" in GUARD_CODE
        assert "os.chown =" in GUARD_CODE

    def test_guard_code_contains_subprocess_guards(self):
        """GUARD_CODE guards subprocess module"""
        assert "subprocess.Popen =" in GUARD_CODE

    def test_guard_code_contains_shutil_guards(self):
        """GUARD_CODE guards shutil module"""
        assert "shutil.rmtree =" in GUARD_CODE
        assert "shutil.move =" in GUARD_CODE
        assert "shutil.chown =" in GUARD_CODE

    def test_guard_code_blocks_dangerous_modules(self):
        """GUARD_CODE blocks dangerous sys modules"""
        assert 'sys.modules["ipdb"]' in GUARD_CODE
        assert 'sys.modules["joblib"]' in GUARD_CODE
        assert 'sys.modules["resource"]' in GUARD_CODE
        assert 'sys.modules["psutil"]' in GUARD_CODE
        assert 'sys.modules["tkinter"]' in GUARD_CODE

    def test_guard_code_imports_required_modules(self):
        """GUARD_CODE imports required modules"""
        assert "import os" in GUARD_CODE
        assert "import shutil" in GUARD_CODE
        assert "import subprocess" in GUARD_CODE
        assert "import sys" in GUARD_CODE

    def test_guard_code_uses_denial_functions(self):
        """GUARD_CODE uses write_denial_function"""
        # The denial function should be interpolated into GUARD_CODE
        assert "lambda" in GUARD_CODE
        assert "PermissionError" in GUARD_CODE

    def test_guard_code_blocks_file_operations(self):
        """GUARD_CODE blocks file modification operations"""
        assert "os.unlink =" in GUARD_CODE
        assert "os.rename =" in GUARD_CODE
        assert "os.replace =" in GUARD_CODE
        assert "os.truncate =" in GUARD_CODE

    def test_guard_code_blocks_process_operations(self):
        """GUARD_CODE blocks process operations"""
        assert "os.fork =" in GUARD_CODE
        assert "os.forkpty =" in GUARD_CODE
        assert "os.killpg =" in GUARD_CODE

    def test_guard_code_blocks_directory_changes(self):
        """GUARD_CODE blocks directory manipulation"""
        assert "os.chdir =" in GUARD_CODE
        assert "os.fchdir =" in GUARD_CODE
        assert "os.getcwd =" in GUARD_CODE
        assert "os.chroot =" in GUARD_CODE

    def test_guard_code_not_empty(self):
        """GUARD_CODE is not empty"""
        assert len(GUARD_CODE.strip()) > 0


# ==============================================================================
# CODE_INTERPRETER_SYSTEM_PROMPT Tests
# ==============================================================================


class TestCodeInterpreterSystemPrompt:
    """Test CODE_INTERPRETER_SYSTEM_PROMPT constant"""

    def test_prompt_is_string(self):
        """CODE_INTERPRETER_SYSTEM_PROMPT is a string"""
        assert isinstance(CODE_INTERPRETER_SYSTEM_PROMPT, str)

    def test_prompt_contains_role_definition(self):
        """Prompt defines AI code interpreter role"""
        assert "AI code interpreter" in CODE_INTERPRETER_SYSTEM_PROMPT

    def test_prompt_contains_goal(self):
        """Prompt contains goal statement"""
        assert "goal" in CODE_INTERPRETER_SYSTEM_PROMPT.lower()
        assert "Python code" in CODE_INTERPRETER_SYSTEM_PROMPT

    def test_prompt_contains_numbered_instructions(self):
        """Prompt contains numbered instructions"""
        assert "1." in CODE_INTERPRETER_SYSTEM_PROMPT
        assert "2." in CODE_INTERPRETER_SYSTEM_PROMPT
        assert "3." in CODE_INTERPRETER_SYSTEM_PROMPT
        assert "4." in CODE_INTERPRETER_SYSTEM_PROMPT
        assert "5." in CODE_INTERPRETER_SYSTEM_PROMPT

    def test_prompt_mentions_error_handling(self):
        """Prompt mentions error handling"""
        assert "error" in CODE_INTERPRETER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_requirements(self):
        """Prompt mentions understanding requirements"""
        assert "requirements" in CODE_INTERPRETER_SYSTEM_PROMPT.lower()

    def test_prompt_mentions_multilingual(self):
        """Prompt mentions responding in user's language"""
        assert "language" in CODE_INTERPRETER_SYSTEM_PROMPT.lower()

    def test_prompt_not_empty(self):
        """CODE_INTERPRETER_SYSTEM_PROMPT is not empty"""
        assert len(CODE_INTERPRETER_SYSTEM_PROMPT.strip()) > 0


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestConstIntegration:
    """Integration tests for const module"""

    def test_all_constants_defined(self):
        """All expected constants are defined"""
        from nexuscore.utils import const

        assert hasattr(const, "TOOLS_CODE")
        assert hasattr(const, "write_denial_function")
        assert hasattr(const, "read_denial_function")
        assert hasattr(const, "class_denial")
        assert hasattr(const, "GUARD_CODE")
        assert hasattr(const, "CODE_INTERPRETER_SYSTEM_PROMPT")

    def test_guard_code_references_denial_functions(self):
        """GUARD_CODE properly references denial functions"""
        # write_denial_function should be interpolated in GUARD_CODE
        assert write_denial_function in GUARD_CODE

    def test_constants_are_strings(self):
        """All constants are strings"""
        assert isinstance(TOOLS_CODE, str)
        assert isinstance(write_denial_function, str)
        assert isinstance(read_denial_function, str)
        assert isinstance(class_denial, str)
        assert isinstance(GUARD_CODE, str)
        assert isinstance(CODE_INTERPRETER_SYSTEM_PROMPT, str)

    def test_no_constants_are_empty(self):
        """No constants are empty strings"""
        assert TOOLS_CODE.strip()
        assert write_denial_function.strip()
        assert read_denial_function.strip()
        assert class_denial.strip()
        assert GUARD_CODE.strip()
        assert CODE_INTERPRETER_SYSTEM_PROMPT.strip()
