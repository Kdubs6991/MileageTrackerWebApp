import sys
from pathlib import Path

"""
Tests for entry-related routes.

What this file covers:
- The home page loads successfully
- Protected entry routes redirect anonymous users to login
- Export route is also protected

Why these are good starter tests:
- They verify route wiring and login protection
- They do not require modifying the real database yet
- They give us a safe base before we add full create/edit/delete tests
"""

# Add the project root to Python's import path so tests can import `app.py`
# when pytest runs from the `tests/` folder.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app


def test_home_route_redirects_when_not_logged_in():
    """
    The home route currently requires login, so anonymous users should be
    redirected to the login page instead of receiving HTTP 200.
    """
    client = app.test_client()
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]



def test_add_page_redirects_when_not_logged_in():
    """The add-entry page should redirect anonymous users to login."""
    client = app.test_client()
    response = client.get("/add", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]



def test_export_route_redirects_when_not_logged_in():
    """The export route should redirect anonymous users to login."""
    client = app.test_client()
    response = client.get("/export", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]



def test_edit_route_redirects_when_not_logged_in():
    """
    The edit route should redirect anonymous users to login.
    We use a sample entry ID because login protection should happen before
    the app tries to load the entry.
    """
    client = app.test_client()
    response = client.get("/edit/1", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]



def test_delete_route_redirects_when_not_logged_in():
    """
    The delete route should redirect anonymous users to login.
    This verifies that destructive entry actions are protected.
    """
    client = app.test_client()
    response = client.post("/delete/1", follow_redirects=False)

    assert response.status_code in (301, 302)
    assert "/login" in response.headers["Location"]
