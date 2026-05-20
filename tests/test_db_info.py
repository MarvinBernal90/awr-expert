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
        <tr><th>DB Name</th><th>DB Id</th><th>Release</th><th>RAC</th><th>CPUs</th></tr>
        <tr><td>MARFA</td><td>12345</td><td>19.0.0.0.0</td><td>YES</td><td>16</td></tr>
    </table></body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    db_info = extract_db_info(soup)

    assert db_info.version == "19.0.0.0.0"
    assert db_info.db_id == 12345
    assert db_info.cpus == 16
    assert db_info.is_rac is True


def test_extract_db_info_missing_data() -> None:
    """
    GIVEN an AWR header with missing critical fields
    WHEN extract_db_info is called
    THEN it should not crash, returning UNKNOWN defaults.
    """
    html = "<html><body><table><tr><td>Random Data</td></tr></table></body></html>"
    soup = BeautifulSoup(html, "lxml")
    db_info = extract_db_info(soup)

    # Asserting that it returns 'UNKNOWN' instead of None as per new logic
    assert db_info.version == "UNKNOWN"
    assert db_info.db_name == "UNKNOWN"
