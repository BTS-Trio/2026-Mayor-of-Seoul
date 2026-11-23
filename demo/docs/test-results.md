# 검증 기록 (2026-11-23)

로컬 Windows에서 데이터·BM25·기사 검증·CSV PK/FK·PDF 본문/쪽수 테스트 11건 통과. Python 3.10 AST 문법 검사 및 JavaScript 구문 검사 통과. 실제 로컬 Python은 3.12이며 3.10.10 런타임 실측은 아닙니다.

오세훈 원문은 Drive 뷰어에서 총 5쪽 및 인용 1·2·4쪽 본문을 대조했습니다. 가상 PDF 5개는 생성 후 1쪽·문서 ID·본문 전체를 추출 비교하고 PNG로 렌더해 확인했습니다.

로컬에는 FastAPI·Uvicorn·WebSockets가 없고 DNS 제한으로 설치할 수 없어 실제 두 서버·API·브라우저 통합 검증은 이 브랜치의 Windows GitHub Actions에서 별도로 수행합니다. 기존 커밋의 테스트 성공을 새 변경의 성공으로 간주하지 않습니다.
