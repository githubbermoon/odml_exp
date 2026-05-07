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
    caption: str = ""
    visible_text: str = ""
    summary: str = ""
    objects: list[str] | None = None
    tags: list[str] | None = None
    extraction_status: str = "pending"

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
            "caption": self.caption,
            "visible_text": self.visible_text,
            "summary": self.summary,
            "objects": self.objects or [],
            "tags": self.tags or [],
            "extraction_status": self.extraction_status,
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
                    capture_id, ts, source, label, mime, width, height, bytes, metadata_json, image,
                    caption, visible_text, summary, objects_json, tags_json, extraction_status, extraction_raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    "",
                    "",
                    "",
                    "[]",
                    "[]",
                    "pending",
                    "",
                ),
            )
        return record

    def update_extraction(self, capture_id: str, extraction: dict[str, Any]) -> CaptureRecord:
        caption = str(extraction.get("caption", ""))
        visible_text = str(extraction.get("visible_text", ""))
        summary = str(extraction.get("summary", caption or visible_text))
        objects = listify(extraction.get("objects"))
        tags = listify(extraction.get("tags"))
        status = str(extraction.get("status", "ready"))
        raw = str(extraction.get("raw", ""))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE captures
                SET caption = ?, visible_text = ?, summary = ?, objects_json = ?, tags_json = ?,
                    extraction_status = ?, extraction_raw = ?
                WHERE capture_id = ?
                """,
                (
                    caption,
                    visible_text,
                    summary,
                    json.dumps(objects, sort_keys=True),
                    json.dumps(tags, sort_keys=True),
                    status,
                    raw,
                    capture_id,
                ),
            )
        record = self.get(capture_id)
        if record is None:
            raise ValueError(f"capture not found: {capture_id}")
        return record

    def get(self, capture_id: str) -> CaptureRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT capture_id, ts, source, label, mime, width, height, bytes, metadata_json,
                       caption, visible_text, summary, objects_json, tags_json, extraction_status
                FROM captures
                WHERE capture_id = ?
                """,
                (capture_id,),
            ).fetchone()
        return self._record_from_row(row) if row else None

    def recent(self, limit: int = 24) -> list[CaptureRecord]:
        limit = max(1, min(limit, 100))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT capture_id, ts, source, label, mime, width, height, bytes, metadata_json,
                       caption, visible_text, summary, objects_json, tags_json, extraction_status
                FROM captures
                ORDER BY ts DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def search(self, question: str, limit: int = 6) -> list[CaptureRecord]:
        terms = [term.lower() for term in question.split() if len(term) > 2]
        records = self.recent(limit=100)
        scored: list[tuple[int, CaptureRecord]] = []
        for record in records:
            haystack = " ".join(
                [
                    record.caption,
                    record.visible_text,
                    record.summary,
                    " ".join(record.objects or []),
                    " ".join(record.tags or []),
                ]
            ).lower()
            score = sum(1 for term in terms if term in haystack)
            if score or not terms:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].ts), reverse=True)
        bounded_limit = max(1, min(limit, 24))
        if not scored:
            return records[:bounded_limit]
        return [record for _, record in scored[:bounded_limit]]

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
            for column, ddl in {
                "caption": "ALTER TABLE captures ADD COLUMN caption TEXT NOT NULL DEFAULT ''",
                "visible_text": "ALTER TABLE captures ADD COLUMN visible_text TEXT NOT NULL DEFAULT ''",
                "summary": "ALTER TABLE captures ADD COLUMN summary TEXT NOT NULL DEFAULT ''",
                "objects_json": "ALTER TABLE captures ADD COLUMN objects_json TEXT NOT NULL DEFAULT '[]'",
                "tags_json": "ALTER TABLE captures ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'",
                "extraction_status": "ALTER TABLE captures ADD COLUMN extraction_status TEXT NOT NULL DEFAULT 'pending'",
                "extraction_raw": "ALTER TABLE captures ADD COLUMN extraction_raw TEXT NOT NULL DEFAULT ''",
            }.items():
                if column not in table_columns(conn, "captures"):
                    conn.execute(ddl)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _record_from_row(self, row: sqlite3.Row) -> CaptureRecord:
        return CaptureRecord(
            capture_id=str(row["capture_id"]),
            ts=float(row["ts"]),
            source=str(row["source"]),
            label=str(row["label"]),
            mime=str(row["mime"]),
            width=int(row["width"]),
            height=int(row["height"]),
            bytes=int(row["bytes"]),
            metadata=json.loads(str(row["metadata_json"] or "{}")),
            caption=str(row["caption"] or ""),
            visible_text=str(row["visible_text"] or ""),
            summary=str(row["summary"] or ""),
            objects=json.loads(str(row["objects_json"] or "[]")),
            tags=json.loads(str(row["tags_json"] or "[]")),
            extraction_status=str(row["extraction_status"] or "pending"),
        )


def decode_data_url(data_url: str) -> tuple[str, bytes]:
    if not data_url.startswith("data:") or "," not in data_url:
        raise ValueError("capture frame must include a data URL")
    header, encoded = data_url.split(",", 1)
    mime = header[5:].split(";", 1)[0] or "image/jpeg"
    return mime, base64.b64decode(encoded, validate=True)


def listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row["name"]) for row in rows}
