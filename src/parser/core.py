"""
Core parsing logic for AWR Reports.
"""

from pathlib import Path

from src.models.base import AWRReport


class AWRParser:
    """
    Main parser class responsible for extracting data from AWR HTML files.
    """

    def parse(self, file_path: str | Path) -> AWRReport:
        """
        Reads the AWR file and extracts all available metrics
        into a validated Pydantic model.

        Args:
            file_path: Absolute or relative path to the AWR HTML file.

        Returns:
            A validated AWRReport object.
        """
        # Feature: Ticket 1 simply validates the file can be opened.
        path_obj = Path(file_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"AWR file not found at: {path_obj}")

        # Read the file to ensure IO permissions and basic integrity
        with open(path_obj, "r", encoding="utf-8") as f:
            _content = f.read()  # Underscore prevents 'unused variable' warning

        # Return empty root model for now (To be expanded in Ticket 2/3)
        return AWRReport()
