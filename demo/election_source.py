"""Election commission role for the educational replay."""
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from replay_timing import PLAYBACK_SPEEDS, seconds_between_snapshots

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
async def feed(socket: WebSocket, speed: str = ""):
    await socket.accept()
    if speed and speed not in PLAYBACK_SPEEDS:
        await socket.close(code=1008)
        return
    interval = seconds_between_snapshots(speed) if speed else REPLAY_INTERVAL
    clock = asyncio.get_running_loop()
    started_at = clock.time()
    try:
        for index, line in enumerate(SNAPSHOT_FILE.read_text(encoding="utf-8").splitlines()):
            if index:
                await asyncio.sleep(max(0, started_at + index * interval - clock.time()))
            snapshot = json.loads(line)
            sent_at = datetime.now(KST).isoformat(timespec="milliseconds")
            await socket.send_json({**snapshot, "source_sent_at": sent_at})
        await socket.close(code=1000)
    except (WebSocketDisconnect, OSError):
        return
