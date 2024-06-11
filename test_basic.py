from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
headers = {
    'accept': 'application/json',
    # 'Content-Type': 'multipart/form-data'
}


def test_main_smoke():
    response = client.get("/")
    assert response.status_code == 200
