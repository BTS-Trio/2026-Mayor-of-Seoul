"""Broadcaster demo. Relay the counting feed to each connected dashboard."""
import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from housing_search import get_housing_search

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))
FEED_URL = os.environ.get("ELECTION_FEED_URL", "ws://127.0.0.1:8001/ws/feed")
MESSAGE_TIMEOUT_SECONDS = 10
app = FastAPI(title="서울시장 모의 개표 · 방송 송출 서버")


@app.get("/")
def dashboard():
    return FileResponse(ROOT / "index.html")


@app.get("/housing-search")
def housing_search_page():
    return FileResponse(ROOT / "housing-search.html")


def housing_index():
    try:
        return get_housing_search()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=503, detail="검색 자료의 ID·쪽수·출처 정보를 확인해 주세요."
        ) from error


@app.get("/api/housing/status")
def housing_search_status():
    return housing_index().status()


@app.get("/api/housing/search")
def search_housing_evidence(q: str = "", candidate: str = "", limit: int = 10):
    index = housing_index()
    try:
        return index.search(q, candidate=candidate, limit=limit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/housing/draft")
def housing_draft():
    """Load the team's existing article and link its cited pages."""
    sources = {
        (item["document_id"], item["pdf_page"]): item["stored_pdf_url"]
        for item in housing_index().chunks
    }
    try:
        markdown = (ROOT / "docs" / "housing-article-draft-20261123.md").read_text(encoding="utf-8")
        article, separator, notes = markdown.partition("\n---\n")
        heading, _, body = article.partition("\n")
        if not separator or not heading.startswith("# ") or not body.strip():
            raise ValueError("Invalid article draft format")
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=503, detail="기사 초안 문서를 확인해 주세요.") from error

    withdrawal_source = re.search(r"사퇴 표시 출처: \[[^\]]+\]\((https://[^\s)]+)\)", notes)
    sentences = []
    for line in filter(None, map(str.strip, body.splitlines())):
        text, _, _ = line.partition(" [")
        citations = [
            {"label": f"{document_id} · PDF {page}쪽",
             "url": sources.get((document_id, int(page)))}
            for document_id, page in re.findall(r"\[([A-Z0-9-]+), PDF (\d+)쪽\]", line)
        ]
        withdrawal = re.search(r"\[사퇴 표시 근거: ([A-Z0-9-]+)\]", line)
        if withdrawal:
            citations.append({
                "label": f"사퇴 근거 · {withdrawal[1]}",
                "url": withdrawal_source[1] if withdrawal_source else None,
            })
        sentences.append({"text": text, "citations": citations})

    return {"title": heading[2:], "sentences": sentences}


@app.get("/embic.webp")
def mascot():
    return FileResponse(ROOT / "embic.webp", media_type="image/webp")


@app.get("/embic-election.jpg")
def election_mascot():
    return FileResponse(ROOT / "embic-election.jpg", media_type="image/jpeg")


@app.get("/election-background.jpg")
def election_banner():
    return FileResponse(ROOT / "election-background.jpg", media_type="image/jpeg")


@app.get("/health")
def health():
    return {"role": "broadcast", "mode": "simulation"}


@app.get("/api/final")
def final_result():
    return json.loads((DATA / "seoul_final_totals.json").read_text(encoding="utf-8"))


def decode_snapshot(raw_message, expected_sequence):
    snapshot = json.loads(raw_message)
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("event") != "snapshot"
        or snapshot.get("mode") != "simulation"
        or type(snapshot.get("sequence")) is not int
        or snapshot["sequence"] != expected_sequence
        or type(snapshot.get("complete")) is not bool
        or not isinstance(snapshot.get("source_sent_at"), str)
    ):
        raise ValueError("Invalid or out-of-order election feed snapshot")
    return snapshot


@app.websocket("/ws/replay")
async def replay(socket: WebSocket):
    await socket.accept()
    try:
        try:
            async with connect(FEED_URL, open_timeout=4, close_timeout=1) as upstream:
                sequence = 0
                while True:
                    raw_message = await asyncio.wait_for(upstream.recv(), MESSAGE_TIMEOUT_SECONDS)
                    snapshot = decode_snapshot(raw_message, sequence)
                    delivered = datetime.now(KST).isoformat(timespec="milliseconds")
                    await socket.send_json({**snapshot, "delivered_at": delivered})
                    if snapshot["complete"]:
                        break
                    sequence += 1
        except (OSError, TimeoutError, asyncio.TimeoutError, WebSocketException, ValueError):
            await socket.send_json({
                "event": "error",
                "code": "election_feed_unavailable",
                "message": "선관위 역할 서버의 모의 개표 전송이 끊겼습니다. 8001 서버를 확인하고 다시 재생하세요.",
            })
            await socket.close(code=1011)
            return
        await socket.close(code=1000)
    except (WebSocketDisconnect, OSError):
        return

