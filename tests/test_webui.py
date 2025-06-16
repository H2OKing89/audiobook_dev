import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db import save_request
from src.token_gen import generate_token

client = TestClient(app)

def test_homepage():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Audiobook" in resp.text

def test_invalid_token():
    resp = client.get("/approve/invalidtoken")
    assert resp.status_code in (401, 410, 404)
    assert "expired" in resp.text.lower() or "unauthorized" in resp.text.lower()

def test_rejection_endpoint():
    """Test the rejection endpoint with valid and invalid tokens"""
    # Test with invalid token
    resp = client.get("/reject/invalidtoken")
    assert resp.status_code in (401, 410, 404)
    
    # Test with valid token
    token = generate_token()
    metadata = {'title': 'Test Book', 'author': 'Test Author'}
    payload = {'name': 'Test torrent', 'url': 'http://test.com'}
    save_request(token, metadata, payload)
    
    resp = client.get(f"/reject/{token}")
    assert resp.status_code == 200
    assert "rejected" in resp.text.lower()
    assert "Request Rejected" in resp.text
