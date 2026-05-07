from edgepulse.memory.captures import CaptureStore


def test_capture_store_persists_image_blob_without_returning_data_url(tmp_path) -> None:
    store = CaptureStore(tmp_path / "captures.sqlite3")

    record = store.save(
        {
            "source": "test",
            "label": "unit_capture",
            "ts": 123.0,
            "metadata": {"lens": "back"},
            "frame": {
                "mime": "image/jpeg",
                "width": 2,
                "height": 1,
                "data_url": "data:image/jpeg;base64,/9j/",
            },
        }
    )

    [recent] = store.recent()
    payload = record.to_dict()

    assert record.bytes == 3
    assert recent.capture_id == record.capture_id
    assert recent.metadata == {"lens": "back"}
    assert "data_url" not in payload

