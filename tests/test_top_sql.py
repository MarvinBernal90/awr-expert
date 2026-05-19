"""
Unit tests for the Top SQL extraction logic.
"""

from bs4 import BeautifulSoup

from src.parser.top_sql import extract_top_sql


def test_extract_top_sql_survives_malformed_html() -> None:
    """
    GIVEN an AWR Top SQL table where one row is valid and another is malformed
    WHEN extract_top_sql is called
    THEN it should parse the valid row and gracefully skip the malformed one.
    """
    html = (
        "<html><body>"
        "<h3>SQL ordered by Elapsed Time</h3>"
        "<table>"
        "<tr><th>Elapsed</th><th>Executions</th><th>SQL ID</th><th>SQL Text</th></tr>"
        "<tr><td>1,234.56</td><td>100</td><td>a1b2c3d4e5f6g</td>"
        "<td>SELECT * FROM USERS</td></tr>"
        "<tr><td><div class='broken-plan'>This breaks everything</td></tr>"
        "</table></body></html>"
    )
    soup = BeautifulSoup(html, "lxml")
    sql_data = extract_top_sql(soup)

    # El parser sobrevivió y logró extraer la fila buena
    assert len(sql_data) == 1

    assert sql_data[0].sql_id == "a1b2c3d4e5f6g"
    assert sql_data[0].elapsed_time_s == 1234.56
    assert sql_data[0].executions == 100
    assert sql_data[0].sql_text == "SELECT * FROM USERS"
