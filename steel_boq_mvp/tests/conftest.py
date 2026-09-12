import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    path = PKG_DIR / "samples" / "sample_schedule.pdf"
    if not path.exists():
        pytest.skip("sample_schedule.pdf not generated yet (run samples/make_sample.py)")
    return path


@pytest.fixture(scope="session")
def sample_pdf_bytes(sample_pdf_path: Path) -> bytes:
    return sample_pdf_path.read_bytes()
