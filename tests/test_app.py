"""Unit tests for ACEest Fitness & Gym Flask application (v1.0)."""

import pytest
from ACEest_Fitness import app, init_db


@pytest.fixture
def client(tmp_path):
    """Provide a Flask test client backed by an isolated temp SQLite DB."""
    test_db = tmp_path / "test_aceest.db"
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(test_db)
    init_db(str(test_db))

    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    """Verify /health returns 200 OK and healthy payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_version_endpoint(client):
    """Verify /version returns application version and hostname."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.get_json()
    assert data["app"] == "ACEest Fitness & Gym"
    assert data["version"] == "v1.0"
    assert "hostname" in data


def test_home_page_renders(client):
    """Verify main HTML dashboard renders cleanly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ACEest Fitness" in response.data
    assert b"v1.0" in response.data


def test_login_valid_credentials(client):
    """Verify valid admin credentials succeed."""
    response = client.post(
        "/login", json={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    assert response.get_json()["message"] == "Login successful"


def test_login_invalid_credentials(client):
    """Verify invalid credentials return 401 Unauthorized."""
    response = client.post(
        "/login", json={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 401


def test_add_and_list_clients(client):
    """Verify adding a client persists it and returns it in GET /clients."""
    create_resp = client.post(
        "/clients",
        json={"name": "Aarav Sharma", "program": "Strength Training"},
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["name"] == "Aarav Sharma"

    list_resp = client.get("/clients")
    assert list_resp.status_code == 200
    clients = list_resp.get_json()
    assert len(clients) == 1
    assert clients[0]["program"] == "Strength Training"


def test_add_client_missing_fields(client):
    """Verify missing required client fields return 400 Bad Request."""
    response = client.post("/clients", json={"name": "Incomplete User"})
    assert response.status_code == 400
