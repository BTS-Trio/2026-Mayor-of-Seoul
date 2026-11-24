"""Reader-facing archive for approved educational articles."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from housing_review import storage

ROOT = Path(__file__).resolve().parent
router = APIRouter()
MILESTONES = {f"{percent}% 도달": percent for percent in range(10, 100, 10)}


class VotePublication(BaseModel):
    event_id: str = Field(max_length=80)
    reason: str = Field(max_length=30)
    votes: int = Field(ge=0)


def vote_article(request):
    reason = request.reason
    if reason == "중간 집계":
        reason = "50% 도달"
    previous_progress = 0
    previous_leader = None
    with (ROOT / "data" / "demo_snapshots.jsonl").open(encoding="utf-8") as source:
        for line in source:
            frame = json.loads(line)
            ranked = sorted(frame["candidates"], key=lambda candidate: -candidate["votes"])
            leader, runner_up = ranked[:2]
            unique_leader = leader["candidate_id"] if leader["votes"] > runner_up["votes"] else None
            progress = frame["count_progress_pct"]
            if frame["event_id"] == request.event_id:
                milestone = MILESTONES.get(reason)
                stage_matches = (
                    (milestone is not None and previous_progress < milestone <= progress)
                    or (reason == "최종 집계" and frame["complete"])
                    or (reason == "선두 변경" and unique_leader and previous_leader
                        and unique_leader != previous_leader)
                )
                if not stage_matches or not frame["counted_ballots"] or leader["votes"] != request.votes:
                    break
                gap = leader["votes"] - runner_up["votes"]
                if gap:
                    body = f'{leader["name"]} 후보가 {leader["votes"]:,}표를 얻어 {runner_up["name"]} 후보에 {gap:,}표 앞섰다.'
                else:
                    names = "·".join(item["name"] for item in ranked if item["votes"] == leader["votes"])
                    body = f'{names} 후보가 {leader["votes"]:,}표로 공동 선두다.'
                return {
                    "id": f'feed:{frame["event_id"]}:{reason}',
                    "kind": "followup" if reason == "선두 변경" else "count",
                    "title": f"서울시장 모의 개표 {reason} · {progress:.1f}%",
                    "body": body,
                    "simulated_at": frame["simulated_at"],
                    "source": f'집계 근거 {frame["event_id"]} · 후보 근거 {leader["row_id"]}',
                }
            previous_progress = progress
            if unique_leader:
                previous_leader = unique_leader
    raise HTTPException(422, "공개할 개표 기사와 원본 집계가 일치하지 않습니다.")


def archive_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS published_vote_articles (
        id TEXT PRIMARY KEY, payload TEXT NOT NULL, published_at TEXT NOT NULL
    )""")


@router.get("/articles", include_in_schema=False)
@router.get("/articles.html", include_in_schema=False)
def articles_page():
    return FileResponse(ROOT / "articles.html")


@router.post("/api/articles/vote")
def publish_vote_article(request: VotePublication):
    article = vote_article(request)
    with storage() as db:
        archive_table(db)
        db.execute("INSERT OR IGNORE INTO published_vote_articles VALUES (?, ?, ?)", (
            article["id"], json.dumps(article, ensure_ascii=False), datetime.now(timezone.utc).isoformat(),
        ))
    return {"id": article["id"]}


@router.get("/api/articles")
def published_articles():
    with storage() as db:
        archive_table(db)
        votes = db.execute("SELECT payload, published_at FROM published_vote_articles ORDER BY rowid DESC").fetchall()
        housing = db.execute("SELECT article_id, title, body FROM ARTICLE WHERE status = 'approve' ORDER BY rowid DESC").fetchall()
    return {
        "vote": [{**json.loads(row["payload"]), "published_at": row["published_at"]} for row in votes],
        "housing": [{"id": row["article_id"], "kind": "housing", "title": row["title"], "body": row["body"]} for row in housing],
    }
