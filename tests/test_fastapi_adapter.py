from fastapi.testclient import TestClient

from src.api import app


def test_chat_endpoint_uses_request_context(monkeypatch):
    captured = {}

    def fake_run_request(message, *, request_context=None):
        captured["message"] = message
        captured["request_context"] = request_context
        return {"messages": [{"role": "assistant", "content": "stubbed response"}]}

    monkeypatch.setattr("src.api.run_request", fake_run_request)

    client = TestClient(app)
    response = client.post(
        "/api/chat",
        json={
            "message": "hello",
            "user_id": "11111111-1111-1111-1111-111111111111",
            "workspace_id": "22222222-2222-2222-2222-222222222222",
            "conversation_id": "33333333-3333-3333-3333-333333333333",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"]["messages"][0]["content"] == "stubbed response"
    assert captured["message"] == "hello"
    assert captured["request_context"].user_id == "11111111-1111-1111-1111-111111111111"
    assert captured["request_context"].workspace_id == "22222222-2222-2222-2222-222222222222"
    assert captured["request_context"].conversation_id == "33333333-3333-3333-3333-333333333333"
