"""UI test configuration — mock gradio if not installed."""
import sys
from unittest.mock import MagicMock

# Always ensure gradio is mockable before any UI module is imported.
# This runs at conftest collection time, before test files are imported.
try:
    import gradio as _real_gradio  # noqa: F401
except ImportError:
    _mock_gr = MagicMock()
    _mock_gr.themes = MagicMock()
    _mock_gr.themes.Soft = MagicMock(return_value=MagicMock())
    # Remove any failed-import sentinel, then set our mock
    sys.modules.pop("gradio", None)
    sys.modules["gradio"] = _mock_gr
    sys.modules["gradio.themes"] = _mock_gr.themes
    # Pre-import nexuscore.ui so __init__.py runs with the mock in place
    try:
        import nexuscore.ui  # noqa: F401
    except Exception:
        pass
