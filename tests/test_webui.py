import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_homepage():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Audiobook" in resp.text

def test_invalid_token():
    resp = client.get("/approve/invalidtoken")
    assert resp.status_code in (401, 410, 404)
    assert "expired" in resp.text.lower() or "unauthorized" in resp.text.lower()
