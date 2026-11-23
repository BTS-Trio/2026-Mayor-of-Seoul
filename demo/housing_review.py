"""Server-side review of the supplied housing article and its evidence."""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Literal

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "rag"
ARTICLE = json.loads((DATA / "housing_article.json").read_text(encoding="utf-8"))
EVIDENCE = json.loads((DATA / "housing_evidence.json").read_text(encoding="utf-8"))
CHUNKS = {row["chunk_id"]: row for row in EVIDENCE["chunks"]}
STATUS_SOURCES = {row["source_id"]: row for row in EVIDENCE["candidate_status_sources"]}
router = APIRouter()


class Scenario(BaseModel):
    scenario: Literal["normal", "missing_source", "ai_mismatch"]


class Decision(BaseModel):
    action: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=80)
    reason: str = Field(default="", max_length=1000)


@contextmanager
def storage():
    path = os.environ.get("HOUSING_REVIEW_DB", str(ROOT / "housing-review.sqlite3"))
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                seq INTEGER PRIMARY KEY, draft_id TEXT NOT NULL, event TEXT NOT NULL,
                reviewer TEXT NOT NULL, reason TEXT NOT NULL, validation TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        with connection:
            yield connection
    finally:
        connection.close()


def validate(payload):
    problems = []
    for row, expected in zip(payload["sentences"], ARTICLE, strict=True):
        sid = expected["sentence_id"]
        chunk = CHUNKS.get(row.get("chunk_id"))
        if not chunk or not all(row.get(k) for k in ("document_id", "pdf_page", "stored_pdf_url")):
            problems.append({"sentence_id": sid, "message": "필수 출처 또는 근거 행 ID 누락"})
            continue
        if (
            any(row[k] != chunk[k] for k in ("document_id", "pdf_page", "stored_pdf_url", "citation"))
            or row["candidate_name"] != chunk["candidate"]
            or not chunk["rag_eligible"]
            or any(row.get(k) != expected[k] for k in ("sentence_id", "sentence", "chunk_id"))
        ):
            problems.append({"sentence_id": sid, "message": "초안 또는 출처가 제공된 검수 자료와 불일치"})
        if chunk["candidate_withdrawn"]:
            source = STATUS_SOURCES.get(row.get("candidate_status_source_id"), {})
            if source.get("candidate") != row["candidate_name"] or not source.get("source_url"):
                problems.append({"sentence_id": sid, "message": "후보 사퇴 표시 근거 누락 또는 불일치"})
    rules_pass = not problems
    # These are deterministic verdict fixtures, never presented as live AI calls.
    ai_pass = payload["scenario"] == "normal"
    if ai_pass != rules_pass:
        problems.append({"sentence_id": None, "message": "규칙 검증과 AI 시연 판정 불일치"})
    return {"can_approve": not problems, "rules_pass": rules_pass, "ai_pass": ai_pass,
            "ai_mode": "fixture", "issues": problems}


def audit(connection, draft_id, event, reviewer, reason, payload, result):
    details = {**result, "scenario": payload["scenario"], "evidence": [
        {"sentence_id": row["sentence_id"], "chunk_id": row["chunk_id"]} for row in payload["sentences"]
    ]}
    connection.execute(
        "INSERT INTO audit (draft_id,event,reviewer,reason,validation,created_at) VALUES (?,?,?,?,?,?)",
        (draft_id, event, reviewer, reason, json.dumps(details, ensure_ascii=False),
         datetime.now(timezone.utc).isoformat()),
    )


@router.get("/housing-review")
def review_page():
    return FileResponse(ROOT / "housing-review.html")


@router.post("/api/housing-review/drafts", status_code=201)
def create_draft(request: Scenario):
    sentences = [row.copy() for row in ARTICLE]
    if request.scenario == "missing_source":
        sentences[0].update(chunk_id=None, document_id=None, stored_pdf_url=None, citation=None)
    payload = {"scenario": request.scenario, "sentences": sentences}
    draft_id = str(uuid4())
    result = validate(payload)
    with storage() as db:
        db.execute("INSERT INTO drafts VALUES (?, ?, 'pending')", (draft_id, json.dumps(payload)))
        audit(db, draft_id, "validated", "", "", payload, result)
    return {"id": draft_id, **payload, "validation": result}


@router.post("/api/housing-review/drafts/{draft_id}/decision")
def decide(draft_id: str, request: Decision):
    reviewer, reason = request.reviewer.strip(), request.reason.strip()
    if not reviewer or (request.action == "reject" and not reason):
        raise HTTPException(422, "검토자와 반려 사유를 확인해 주세요.")
    with storage() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "초안을 찾을 수 없습니다.")
        if row["status"] != "pending":
            raise HTTPException(409, "이미 처리된 초안입니다.")
        payload = json.loads(row["payload"])
        result = validate(payload)
        blocked = request.action == "approve" and not result["can_approve"]
        if blocked:
            audit(db, draft_id, "blocked", reviewer, reason, payload, result)
        else:
            db.execute("UPDATE drafts SET status = ? WHERE id = ?", (request.action, draft_id))
            audit(db, draft_id, request.action, reviewer, reason, payload, result)
    if blocked:
        raise HTTPException(409, detail=result)
    return {"id": draft_id, "status": request.action}


@router.get("/api/housing-review/history")
def history():
    with storage() as db:
        rows = db.execute("SELECT * FROM audit ORDER BY seq DESC LIMIT 100").fetchall()
    return [{**dict(row), "validation": json.loads(row["validation"])} for row in rows]
