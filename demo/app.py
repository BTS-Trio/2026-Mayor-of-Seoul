"""Broadcaster demo. Relay the counting feed to each connected dashboard."""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))
FEED_URL = os.environ.get("ELECTION_FEED_URL", "ws://127.0.0.1:8001/ws/feed")
MESSAGE_TIMEOUT_SECONDS = 10
app = FastAPI(title="서울시장 모의 개표 · 방송 송출 서버")


@app.get("/")
def dashboard():
    return FileResponse(ROOT / "index.html")


@app.get("/embic.webp")
def mascot():
    return FileResponse(ROOT / "embic.webp", media_type="image/webp")


@app.get("/election-background.jpg")
def election_background():
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
