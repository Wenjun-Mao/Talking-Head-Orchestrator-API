from fastapi.testclient import TestClient

from ingest_nocodb.app import app


client = TestClient(app)


def _noop_enqueue(*_args, **_kwargs):
    return None


def test_webhook_ok(monkeypatch):
    monkeypatch.setenv("S1_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("S1_NOCODB_API_KEY", "test")
    monkeypatch.setenv("S1_NOCODB_BASE_URL", "https://example.com")
    monkeypatch.setattr("ingest_nocodb.app.enqueue_downstream", _noop_enqueue)
    payload = {
        "type": "records.after.trigger",
        "id": "074d261a-66c4-4c05-99af-3ffb6b964f7a",
        "version": "v3",
        "data": {
            "table_id": "murmwwnt5ukvp7i",
            "table_name": "创意素材",
            "rows": [
                {
                    "Id": 1,
                    "CreatedAt": "2026-01-27T03:21:31.929Z",
                    "UpdatedAt": "2026-01-27T03:21:31.929Z",
                    "Title": "Sample Text",
                    "url": "Sample Text",
                    "content": "Sample Text",
                    "originaltext": "Sample Text",
                    "image1": "Sample Text",
                    "image2": "Sample Text",
                    "image3": "Sample Text",
                    "image4": "Sample Text",
                    "image5": "Sample Text",
                    "fengmianimage": "Sample Text",
                    "chengpinurl": "Sample Text",
                }
            ],
        },
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "received_rows": 1}


def test_webhook_empty_rows(monkeypatch):
    monkeypatch.setenv("S1_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("S1_NOCODB_API_KEY", "test")
    monkeypatch.setenv("S1_NOCODB_BASE_URL", "https://example.com")
    monkeypatch.setattr("ingest_nocodb.app.enqueue_downstream", _noop_enqueue)
    payload = {
        "type": "records.after.trigger",
        "id": "074d261a-66c4-4c05-99af-3ffb6b964f7a",
        "version": "v3",
        "data": {
            "table_id": "murmwwnt5ukvp7i",
            "table_name": "创意素材",
            "rows": [],
        },
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid webhook payload."


def test_webhook_missing_fields(monkeypatch):
    monkeypatch.setenv("S1_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("S1_NOCODB_API_KEY", "test")
    monkeypatch.setenv("S1_NOCODB_BASE_URL", "https://example.com")
    monkeypatch.setattr("ingest_nocodb.app.enqueue_downstream", _noop_enqueue)

    payload = {
        "type": "records.after.trigger",
        "id": "074d261a-66c4-4c05-99af-3ffb6b964f7a",
        "version": "v3",
        "data": {
            "table_id": "murmwwnt5ukvp7i",
            "table_name": "创意素材",
            "rows": [
                {
                    "Id": 1,
                    "CreatedAt": "2026-01-27T03:21:31.929Z",
                    "UpdatedAt": "2026-01-27T03:21:31.929Z",
                    "url": "Sample Text",
                    "content": "Sample Text",
                    "originaltext": "",
                }
            ],
        },
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "received_rows": 1}


def test_webhook_empty_table_id(monkeypatch):
    monkeypatch.setenv("S1_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("S1_NOCODB_API_KEY", "test")
    monkeypatch.setenv("S1_NOCODB_BASE_URL", "https://example.com")
    monkeypatch.setattr("ingest_nocodb.app.enqueue_downstream", _noop_enqueue)
    payload = {
        "type": "records.after.trigger",
        "id": "074d261a-66c4-4c05-99af-3ffb6b964f7a",
        "version": "v3",
        "data": {
            "table_id": "   ",
            "table_name": "创意素材",
            "rows": [
                {
                    "Id": 1,
                    "CreatedAt": "2026-01-27T03:21:31.929Z",
                    "UpdatedAt": "2026-01-27T03:21:31.929Z",
                    "Title": "Sample Text",
                    "url": "Sample Text",
                    "content": "Sample Text",
                    "originaltext": "Sample Text",
                }
            ],
        },
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid webhook payload."


def test_webhook_missing_content(monkeypatch):
    monkeypatch.setenv("S1_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("S1_NOCODB_API_KEY", "test")
    monkeypatch.setenv("S1_NOCODB_BASE_URL", "https://example.com")
    monkeypatch.setattr("ingest_nocodb.app.enqueue_downstream", _noop_enqueue)
    payload = {
        "type": "records.after.trigger",
        "id": "074d261a-66c4-4c05-99af-3ffb6b964f7a",
        "version": "v3",
        "data": {
            "table_id": "murmwwnt5ukvp7i",
            "table_name": "创意素材",
            "rows": [
                {
                    "Id": 1,
                    "CreatedAt": "2026-01-27T03:21:31.929Z",
                    "UpdatedAt": "2026-01-27T03:21:31.929Z",
                    "url": "Sample Text",
                    "originaltext": "Sample Text",
                }
            ],
        },
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid webhook payload."


def test_webhook_downstream_contract(monkeypatch):
    monkeypatch.setenv("S1_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    monkeypatch.setenv("S1_NOCODB_API_KEY", "test")
    monkeypatch.setenv("S1_NOCODB_BASE_URL", "https://example.com")

    captured_calls: list[dict] = []

    def _capture_enqueue(*_args, **kwargs):
        captured_calls.append(kwargs)

    monkeypatch.setattr("ingest_nocodb.app.enqueue_downstream", _capture_enqueue)

    payload = {
        "type": "records.after.trigger",
        "id": "074d261a-66c4-4c05-99af-3ffb6b964f7a",
        "version": "v3",
        "data": {
            "table_id": "murmwwnt5ukvp7i",
            "table_name": "创意素材",
            "rows": [
                {
                    "Id": 7,
                    "CreatedAt": "2026-01-27T03:21:31.929Z",
                    "UpdatedAt": "2026-01-27T03:21:31.929Z",
                    "url": "https://example.com/video",
                    "content": "Sample Text",
                    "originaltext": "ignored",
                }
            ],
        },
    }

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "received_rows": 1}
    assert len(captured_calls) == 1

    enqueue_kwargs = captured_calls[0]
    assert enqueue_kwargs["record_id"] == 7
    assert enqueue_kwargs["table_id"] == "murmwwnt5ukvp7i"
    assert enqueue_kwargs["url"] == "https://example.com/video"
    assert enqueue_kwargs["content"] == "Sample Text"
    assert "title" not in enqueue_kwargs
    assert "original_text" not in enqueue_kwargs
