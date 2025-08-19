import os
import pytest
from src.voice_to_text import transcribe_audio_whisper

def test_transcribe_audio_sample():
    sample_path = "tests/assets/sample.wav"
    assert os.path.exists(sample_path), "サンプル音声ファイルが存在しません"

    text = transcribe_audio_whisper(sample_path)
    assert isinstance(text, str)
    assert len(text) > 0
