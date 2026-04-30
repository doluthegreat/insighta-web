import pytest
from unittest.mock import patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

@pytest.fixture
def client():
    os.environ["API_URL"]      = "http://fakeapi"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    os.environ["SECRET_KEY"]   = "test-secret"
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"GitHub" in resp.data


def test_root_redirects_to_login_or_dashboard(client):
    resp = client.get("/")
    assert resp.status_code in (200, 302)


def test_dashboard_redirects_without_auth(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profiles_redirects_without_auth(client):
    resp = client.get("/profiles")
    assert resp.status_code == 302


def test_search_redirects_without_auth(client):
    resp = client.get("/search")
    assert resp.status_code == 302


def test_account_redirects_without_auth(client):
    resp = client.get("/account")
    assert resp.status_code == 302


def test_unknown_route_redirects(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code in (302, 404)
