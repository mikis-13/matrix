from fastapi.testclient import TestClient

from api.main import app
from api.database import Base, engine


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_register_and_login():
    client = TestClient(app)
    response = client.post("/register", json={"username": "alice", "password": "secret123"})
    assert response.status_code == 200
    payload = response.json()
    assert "access_token" in payload
    assert "refresh_token" in payload

    login_response = client.post("/login", json={"username": "alice", "password": "secret123"})
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert "access_token" in login_payload
    assert "refresh_token" in login_payload


def test_refresh_rotation_and_reuse_detection():
    client = TestClient(app)
    register = client.post("/register", json={"username": "bob", "password": "secret123"})
    old_token = register.json()["refresh_token"]

    rotated = client.post("/refresh", json={"refresh_token": old_token})
    assert rotated.status_code == 200
    new_token = rotated.json()["refresh_token"]
    assert new_token != old_token

    reused = client.post("/refresh", json={"refresh_token": old_token})
    assert reused.status_code == 401

    second_reuse = client.post("/refresh", json={"refresh_token": new_token})
    assert second_reuse.status_code == 200


def test_logout_revokes_token():
    client = TestClient(app)
    register = client.post("/register", json={"username": "charlie", "password": "secret123"})
    token = register.json()["refresh_token"]

    logout = client.post("/logout", json={"refresh_token": token})
    assert logout.status_code == 200

    refreshed = client.post("/refresh", json={"refresh_token": token})
    assert refreshed.status_code == 401
