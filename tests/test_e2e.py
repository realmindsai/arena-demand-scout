"""E2E tests — verify the static site renders correctly."""

import subprocess
import time
import urllib.request
import urllib.error
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE_DIR = Path(__file__).parent.parent / "site"
PORT = 8765


def _wait_for_server(url: str, timeout: float = 5.0) -> None:
    """Poll until the server responds or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    raise RuntimeError(f"Server at {url} did not start within {timeout}s")


@pytest.fixture(scope="module")
def server():
    """Start a local HTTP server for the static site."""
    proc = subprocess.Popen(
        ["python", "-m", "http.server", str(PORT)],
        cwd=SITE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://localhost:{PORT}"
    _wait_for_server(url)
    yield url
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="module")
def page(server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page()
        pg.goto(server)
        pg.wait_for_selector("[x-data]", timeout=5000)
        pg.wait_for_function("() => !document.querySelector('[x-data]')._x_dataStack[0].loading", timeout=10000)
        yield pg
        browser.close()


def test_page_title(page):
    assert "Arena Demand Scout" in page.title()


def test_header_visible(page):
    header = page.locator("header h1")
    assert header.is_visible()
    assert "Arena Demand Scout" in header.text_content()


def test_four_tabs_present(page):
    tabs = page.locator("nav button")
    assert tabs.count() == 4


def test_portfolio_tab_shows_table(page):
    page.locator("nav button", has_text="Portfolio Overview").click()
    page.wait_for_timeout(500)
    table = page.locator("section table")
    assert table.first.is_visible()


def test_portfolio_tab_shows_donut_chart(page):
    page.locator("nav button", has_text="Portfolio Overview").click()
    page.wait_for_timeout(500)
    # Plotly appends js-plotly-plot to the container div; .plot-container has zero height
    chart = page.locator("#chart-donut.js-plotly-plot")
    assert chart.is_visible()


def test_forecast_tab_shows_chart(page):
    page.locator("nav button", has_text="Demand Forecast").click()
    page.wait_for_timeout(500)
    # Plotly appends js-plotly-plot to the container div; .plot-container has zero height
    chart = page.locator("#chart-forecast.js-plotly-plot")
    assert chart.is_visible()


def test_forecast_state_toggles(page):
    page.locator("nav button", has_text="Demand Forecast").click()
    page.wait_for_timeout(500)
    buttons = page.locator("section button")
    assert buttons.count() > 1


def test_opportunity_tab_shows_table_and_chart(page):
    page.locator("nav button", has_text="Opportunity Scoring").click()
    page.wait_for_timeout(500)
    # Use the opportunity section directly to avoid matching the hidden portfolio table
    table = page.locator("section").nth(2).locator("table")
    # Plotly appends js-plotly-plot to the container div; .plot-container has zero height
    chart = page.locator("#chart-scatter.js-plotly-plot")
    assert table.first.is_visible()
    assert chart.is_visible()


def test_map_tab_renders(page):
    page.locator("nav button", has_text="Map").click()
    page.wait_for_timeout(1000)
    # Leaflet adds leaflet-container class directly to #map-container, not a child
    map_el = page.locator("#map-container.leaflet-container")
    assert map_el.is_visible()


def test_series_toggle_updates_charts(page):
    page.locator("nav button", has_text="Demand Forecast").click()
    page.wait_for_timeout(500)
    page.locator("header button", has_text="High").click()
    page.wait_for_timeout(500)
    # Plotly appends js-plotly-plot to the container div; .plot-container has zero height
    chart = page.locator("#chart-forecast.js-plotly-plot")
    assert chart.is_visible()
