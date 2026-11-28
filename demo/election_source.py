"""Election commission role for the educational replay."""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

SNAPSHOT_FILE = Path(__file__).resolve().parent / "data" / "demo_snapshots.jsonl"
KST = timezone(timedelta(hours=9))
REPLAY_INTERVAL = float(os.environ.get("ELECTION_REPLAY_INTERVAL", "2"))
if not 0 < REPLAY_INTERVAL <= 5:
    raise ValueError("ELECTION_REPLAY_INTERVAL must be greater than 0 and at most 5 seconds")

app = FastAPI(title="서울시장 모의 개표 · 선관위 송신 서버")


@app.get("/health")
def health():
    return {"role": "election-source", "mode": "synthetic"}


@app.websocket("/ws/feed")
async def feed(socket: WebSocket):
    await socket.accept()
    try:
        for line in SNAPSHOT_FILE.read_text(encoding="utf-8").splitlines():
            snapshot = json.loads(line)
            sent_at = datetime.now(KST).isoformat(timespec="milliseconds")
            await socket.send_json({**snapshot, "source_sent_at": sent_at})
            if not snapshot["complete"]:
                await asyncio.sleep(REPLAY_INTERVAL)
        await socket.close(code=1000)
    except (WebSocketDisconnect, OSError):
        return
