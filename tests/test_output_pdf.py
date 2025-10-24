"""Tests for the PDF output implementation introduced in MVP Phase 4."""

from __future__ import annotations

from pathlib import Path

import pytest

from mathtest.output import PdfOutputGenerator
from mathtest.plugins.addition import AdditionPlugin


@pytest.fixture()
def sample_problems() -> list:
    """Return a deterministic set of problems for PDF rendering tests."""

    plugin = AdditionPlugin({"random_seed": 123})
    return [plugin.generate_problem() for _ in range(3)]


def test_pdf_output_creates_file(tmp_path: Path, sample_problems: list) -> None:
    """PDF generator should produce a non-empty file with an answer section."""

    output_path = tmp_path / "worksheet.pdf"
    generator = PdfOutputGenerator()

    generator.generate(sample_problems, {"path": output_path})

    assert output_path.exists()
    assert output_path.stat().st_size > 0

    pdf_bytes = output_path.read_bytes()
    assert b"Answer Key" in pdf_bytes
    assert b"1. " in pdf_bytes  # Basic confirmation that answers are listed


def test_pdf_output_requires_path(sample_problems: list) -> None:
    """Missing required parameters should raise a ``ValueError``."""

    generator = PdfOutputGenerator()
    with pytest.raises(ValueError):
        generator.generate(sample_problems, {})
