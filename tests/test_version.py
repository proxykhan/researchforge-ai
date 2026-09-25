"""Tests for package initialization."""

import researchforge


def test_version_exists():
    assert hasattr(researchforge, "__version__")


def test_version_format():
    parts = researchforge.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
