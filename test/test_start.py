import pytest


@pytest.mark.anyio
async def test_start_short_interview(client):
    data = {"email": "test@example.com", "type": "short"}
    response = await client.post("/api/interview/start", data=data)
    assert response.status_code == 200
    json_data = response.json()
    assert "session_id" in json_data
    assert json_data["q_num"] == 1
    assert "text" in json_data
    assert "audio" in json_data
