"""Local FastAPI demo. Each browser connection replays a private session."""
import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

def load_snapshots():
    return [
        json.loads(line)
        for line in (DATA / "demo_snapshots.jsonl").read_text(encoding="utf-8").splitlines()
    ]

app = FastAPI(title="2026 지방선거 교육용 개표 시뮬레이션")

@app.get("/")
def dashboard():
    return FileResponse(ROOT / "index.html")

@app.get("/api/final")
def final_result():
    return json.loads((DATA / "seoul_final_totals.json").read_text(encoding="utf-8"))

@app.websocket("/ws/replay")
async def replay(socket: WebSocket):
    await socket.accept()
    try:
        for snapshot in load_snapshots():
            delivered = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
            await socket.send_json({**snapshot, "delivered_at": delivered})
            if not snapshot["complete"]:
                await asyncio.sleep(2)
        await socket.close(code=1000)
    except (WebSocketDisconnect, OSError):
        return
