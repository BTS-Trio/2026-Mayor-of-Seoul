"""Check the team review key before accepting server-side decisions."""
import os
from hmac import compare_digest

from fastapi import Header, HTTPException


def require_reviewer(x_reviewer_key: str = Header(default="")):
    expected = os.environ.get("ELECTION_REVIEW_KEY")
    if not expected:
        raise HTTPException(503, "서버에 검토 키를 설정해 주세요.")
    if not compare_digest(x_reviewer_key.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(403, "검토 키를 확인해 주세요.")
