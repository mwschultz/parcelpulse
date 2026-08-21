"""CORS headers must survive unhandled exceptions.

Regression test for the failure mode where a 500 reached Starlette's
ServerErrorMiddleware (outside CORSMiddleware) and came back without an
Access-Control-Allow-Origin header, so browsers reported a server error as a
CORS policy violation.
"""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

ORIGIN = settings.FRONTEND_URL


@pytest.fixture
def client():
    # raise_server_exceptions=False lets the middleware produce the 500 response
    # instead of the exception propagating into the test itself.
    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_exception_returns_500_with_cors_header(client):
    @app.get("/_boom")
    def boom():
        raise RuntimeError("kaboom")

    resp = client.get("/_boom", headers={"Origin": ORIGIN})

    assert resp.status_code == 500
    assert resp.headers.get("access-control-allow-origin") == ORIGIN
    assert resp.json() == {"detail": "Internal server error"}


def test_successful_response_still_has_cors_header(client):
    resp = client.get("/health", headers={"Origin": ORIGIN})

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == ORIGIN
