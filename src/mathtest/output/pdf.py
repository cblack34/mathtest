"""PDF output generator stub for Mathtest."""

from __future__ import annotations

from typing import Any

from ..interface import OutputGenerator, Problem


class PDFOutput(OutputGenerator):
    """Placeholder PDF generator implementation."""

    def generate(self, problems: list[Problem], params: dict[str, Any]) -> None:
        """Generate a PDF from problems (not yet implemented)."""

        raise NotImplementedError("PDF generation is not implemented in the MVP setup phase.")
