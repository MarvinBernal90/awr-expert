"""
Unit tests for the DB Info extraction module.
"""

from bs4 import BeautifulSoup

from src.parser.db_info import extract_db_info


def test_extract_db_info_valid_html() -> None:
    """
    GIVEN a valid AWR header HTML snippet
    WHEN extract_db_info is called
    THEN it should correctly parse and populate the DBInfoRaw model.
    """
    html = """
    <html><body><table>
        <tr><td>Release</td><td>19.0.0.0.0</td></tr>
        <tr><td>RAC</td><td>YES</td></tr>
        <tr><td>CPUs:</td><td>16</td></tr>
        <tr><td>Elapsed:</td><td>60.15 (mins)</td></tr>
        <tr><td>DB Time:</td><td>120.50 (mins)</td></tr>
    </table></body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    db_info = extract_db_info(soup)

    assert db_info.version == "19.0.0.0.0"
    assert db_info.is_rac is True
    assert db_info.cpus == 16
    assert db_info.elapsed_time_min == 60.15
    assert db_info.db_time_min == 120.50


def test_extract_db_info_missing_data() -> None:
    """
    GIVEN an AWR header with missing critical fields
    WHEN extract_db_info is called
    THEN it should not crash, returning None for missing fields.
    """
    html = "<html><body><table><tr><td>Random Data</td></tr></table></body></html>"
    soup = BeautifulSoup(html, "lxml")
    db_info = extract_db_info(soup)

    # Pydantic defaults should hold, no crash should occur
    assert db_info.version is None
    assert db_info.cpus is None
    assert db_info.is_rac is False
