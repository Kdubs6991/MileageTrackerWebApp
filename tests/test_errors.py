"""Tests for custom error pages and error handlers.

These tests use Flask's built-in test client to make requests against the app
without starting a real web server.

What this file covers:
- 404 page renders for missing routes
- 400 page renders for a forced bad request
- 500 page renders for a forced internal server error

Why temporary test routes are used:
The app may not naturally expose easy ways to trigger 400 and 500 errors on
command, so we register tiny test-only routes in this file. These routes must
be registered at import time, before the first request happens, because Flask
locks route setup after request handling starts.
"""

import sys
from pathlib import Path
from flask import abort

# Add the project root to Python's import path so tests can import `app.py`
# when pytest runs from the `tests/` folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app


# ---------------------------------------------------------
# Test-only routes
# ---------------------------------------------------------
# Define these once, at import time, before any requests happen.
if "forced_400_route_handler" not in app.view_functions:
    @app.route("/test-400-route")
    def forced_400_route_handler():
        abort(400)


if "forced_500_route_handler" not in app.view_functions:
    @app.route("/test-500-route")
    def forced_500_route_handler():
        raise Exception("Intentional test 500 error")


def test_404_page_renders():
    """A missing route should return the custom 404 page."""
    client = app.test_client()
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    assert b"404" in response.data
    assert b"Page Not Found" in response.data or b"doesn\xe2\x80\x99t exist" in response.data


def test_400_page_renders():
    """A forced bad request should return the custom 400 page."""
    client = app.test_client()
    response = client.get("/test-400-route")

    assert response.status_code == 400
    assert b"400" in response.data
    assert b"Bad Request" in response.data


def test_500_page_renders():
    """A forced server crash should return the custom 500 page."""
    client = app.test_client()

    # Keep TESTING off so Flask uses your 500 error handler
    # instead of re-raising the exception into pytest.
    app.config["TESTING"] = False
    response = client.get("/test-500-route")

    assert response.status_code == 500
    assert b"Something went wrong" in response.data or b"Server Error" in response.data