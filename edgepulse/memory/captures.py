from __future__ import annotations

import base64
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(os.getenv("EDGEPULSE_MEMORY_DB", "data/secondsight.sqlite3"))


@dataclass(slots=True)
class CaptureRecord:
    capture_id: str
    mime: str
    width: int
    height: int
    bytes: int
    source: str
    label: str
    ts: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "mime": self.mime,
            "width": self.width,
            "height": self.height,
            "bytes": self.bytes,
            "source": self.source,
            "label": self.label,
            "ts": self.ts,
            "metadata": self.metadata,
        }


class CaptureStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def save(self, payload: dict[str, Any]) -> CaptureRecord:
        frame = payload.get("frame") if isinstance(payload.get("frame"), dict) else {}
        data_url = str(frame.get("data_url", ""))
        mime, image_bytes = decode_data_url(data_url)
        capture_id = str(payload.get("capture_id") or uuid.uuid4())
        record = CaptureRecord(
            capture_id=capture_id,
            mime=mime or str(frame.get("mime", "image/jpeg")),
            width=int(frame.get("width", 0) or 0),
            height=int(frame.get("height", 0) or 0),
            bytes=len(image_bytes),
            source=str(payload.get("source", "secondsight")),
            label=str(payload.get("label", "capture")),
            ts=float(payload.get("ts", time.time())),
            metadata=dict(payload.get("metadata", {})) if isinstance(payload.get("metadata"), dict) else {},
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO captures (
                    capture_id, ts, source, label, mime, width, height, bytes, metadata_json, image
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.capture_id,
                    record.ts,
                    record.source,
                    record.label,
                    record.mime,
                    record.width,
                    record.height,
                    record.bytes,
                    json.dumps(record.metadata, sort_keys=True),
                    image_bytes,
                ),
            )
        return record

    def recent(self, limit: int = 24) -> list[CaptureRecord]:
        limit = max(1, min(limit, 100))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT capture_id, ts, source, label, mime, width, height, bytes, metadata_json
                FROM captures
                ORDER BY ts DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            CaptureRecord(
                capture_id=str(row["capture_id"]),
                ts=float(row["ts"]),
                source=str(row["source"]),
                label=str(row["label"]),
                mime=str(row["mime"]),
                width=int(row["width"]),
                height=int(row["height"]),
                bytes=int(row["bytes"]),
                metadata=json.loads(str(row["metadata_json"] or "{}")),
            )
            for row in rows
        ]

    def _ensure_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS captures (
                    capture_id TEXT PRIMARY KEY,
                    ts REAL NOT NULL,
                    source TEXT NOT NULL,
                    label TEXT NOT NULL,
                    mime TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    bytes INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    image BLOB NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_captures_ts ON captures(ts)")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def decode_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("capture frame must include a data URL")
    header, encoded = data_url.split(",", 1)
    mime = header[5:].split(";", 1)[0] or "image/jpeg"
    return mime, base64.b64decode(encoded, validate=True)

