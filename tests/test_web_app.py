from fastapi.testclient import TestClient

from edgepulse.network.server import app


def test_pwa_root_serves_html() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "ODML Checkpoint" in response.text


def test_network_info_exposes_demo_urls() -> None:
    client = TestClient(app)
    response = client.get("/network-info")

    assert response.status_code == 200
    assert "http_url" in response.json()


def test_capture_endpoint_stores_frame_metadata_without_echoing_image() -> None:
    client = TestClient(app)
    response = client.post(
        "/captures",
        json={
            "source": "test",
            "label": "api_capture",
            "metadata": {"route": "secondsight"},
            "frame": {
                "mime": "image/jpeg",
                "width": 2,
                "height": 1,
                "data_url": "data:image/jpeg;base64,/9j/",
            },
        },
    )

    assert response.status_code == 200
    capture = response.json()["capture"]
    assert capture["bytes"] == 3
    assert capture["width"] == 2
    assert "data_url" not in capture


def test_capture_endpoint_rejects_missing_data_url() -> None:
    client = TestClient(app)
    response = client.post("/captures", json={"frame": {"mime": "image/jpeg"}})

    assert response.status_code == 400


def test_browser_websocket_streams_hint_token_and_reasoning() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/events") as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["type"] == "snapshot"

        websocket.send_json(
            {
                "source": "test-browser",
                "input_mode": "mediapipe_gemma",
                "gesture": "raised_hand",
                "attention": "focused",
                "head_pose": "tilted_left",
                "duration": 4.2,
                "confidence": 0.9,
            }
        )

        seen = {websocket.receive_json()["type"] for _ in range(3)}
        assert "hint" in seen
        assert "token" in seen


def test_browser_can_switch_to_mediapipe_only_mode() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/events") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "set_mode", "mode": "mediapipe"})
        mode_message = websocket.receive_json()

        assert mode_message["type"] == "mode"
        assert mode_message["mode"] == "mediapipe"
        assert mode_message["model_status"] == "bypassed"


def test_direct_gemma_vision_reports_missing_runner_without_raw_frame_storage() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/events") as websocket:
        websocket.receive_json()
        websocket.send_json(
            {
                "source": "test-browser",
                "input_mode": "gemma_multimodal",
                "gesture": "pointing",
                "attention": "focused",
                "head_pose": "center",
                "duration": 1.0,
                "confidence": 0.8,
                "frame": {
                    "mime": "image/jpeg",
                    "width": 2,
                    "height": 2,
                    "data_url": "data:image/jpeg;base64,abcd",
                },
            }
        )

        messages = [websocket.receive_json() for _ in range(5)]
        reasoning = next(message["result"] for message in messages if message["type"] == "reasoning")
        hint = next(message["event"] for message in messages if message["type"] == "hint")

        assert reasoning["intent"] == "multimodal_runner_unconfigured"
        assert hint["frame_meta"]["bytes"] == len("data:image/jpeg;base64,abcd")
        assert "data_url" not in hint["frame_meta"]
