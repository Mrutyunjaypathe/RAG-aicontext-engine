"""
pytest configuration and shared fixtures.
"""
import pytest
import sys
from pathlib import Path

# Make sure the project root is on the Python path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch, tmp_path):
    """
    Override settings to use temp dirs during tests.
    Prevents tests from touching real data directories.
    """
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("VECTOR_DIR", str(tmp_path / "vectors"))
    monkeypatch.setenv("LOG_DIR",    str(tmp_path / "logs"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-placeholder")
    (tmp_path / "uploads").mkdir()
    (tmp_path / "vectors").mkdir()
    (tmp_path / "logs").mkdir()


@pytest.fixture
def sample_text():
    return (
        "Artificial Intelligence is transforming every industry. "
        "Machine learning models can now process vast amounts of data. "
        "Natural language processing enables computers to understand human text. "
        "Deep learning has achieved superhuman performance on many benchmarks. "
    ) * 20


@pytest.fixture
def sample_txt_file(tmp_path, sample_text):
    f = tmp_path / "sample.txt"
    f.write_text(sample_text, encoding="utf-8")
    return f
