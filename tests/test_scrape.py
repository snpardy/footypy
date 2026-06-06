# import pickle
# from __future__ import annotations

from bs4 import BeautifulSoup

# import footypy
from footypy import scrape


def get_full_year_results_test():
    """
    This defines the expected usage, which can then be used in various test cases.
    Pytest will not execute this code directly, since the function does not contain the suffex "test"
    """
    scrape.get_full_year_results()


def test_get_match_details():
    """
    This is a simple test, which can use a mock to override online functionality.
    unit_test_mocks: Fixture located in conftest.py, implictly imported via pytest.
    """

    footy_wire_match_id = 5962
    # soup = BeautifulSoup(page.content, "html.parser")
    df = scrape.get_match_details(footy_wire_match_id)
    # scrape._detail_helper_player_stats(soup)