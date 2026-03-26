import sys
from pathlib import Path

"""
Tests for authentication-related routes.

What this file covers:
- Login page loads successfully
- Register page loads successfully
- Protected routes redirect when the user is not logged in

Why these are good starter tests:
- They are simple and safe
- They do not require modifying the real database yet
- They help confirm that the auth pages and login protection work
"""

# Add the project root to Python's import path so tests can import `app.py`
# when pytest runs from the `tests/` folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app


def test_login_page_loads():
    """The login page should return HTTP 200 and contain Login text."""
    client = app.test_client()
    response = client.get("/login")

    assert response.status_code == 200
    assert b"Login" in response.data



def test_register_page_loads():
    """The register page should return HTTP 200 and contain Register text."""
    client = app.test_client()
    response = client.get("/register")

    assert response.status_code == 200
    assert b"Register" in response.data



def test_add_route_redirects_when_not_logged_in():
    """
    Protected routes should redirect anonymous users to login.
    We use /add because it should require authentication.
    """
    client = app.test_client()
    response = client.get("/add", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]



def test_account_route_redirects_when_not_logged_in():
    """
    Another protected route should also redirect anonymous users to login.
    This helps verify that login protection is applied consistently.
    """
    client = app.test_client()
    response = client.get("/account", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]