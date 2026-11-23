# 데이터 사전·API (가상 후보 통합 전환)

현재 후보·PK/FK·CSV 행 수·근거 추적은 [데이터 통합 안내](dummy-data-integration.md)와 schema.sql이 기준입니다. 전환 전 원본 개표 자료는 Git 이력에 남기고 현재 실행 데이터에서 제외합니다.

| 경로 | 역할 |
| --- | --- |
| GET / | 개표 데스크·지도·예시 기사 |
| GET /health | 방송사 역할 서버 상태, mode=synthetic |
| WS /ws/replay | 송신 역할 서버의 synthetic 스냅샷 중계 |
| WS /ws/feed (8001) | 31단계 가상 스냅샷 전송 |
| GET /api/candidates | 후보 6명·사퇴 상태 |
| GET /api/final | 가상 최종 총계 |
| GET /api/housing/status | BM25 검색 근거와 후보 목록 |
| GET /api/housing/search | q(2~500자), candidate(선택), limit(1~30), include_withdrawn(기본 false) |
| GET /api/housing/draft | 저장 기사 6문장과 문장별 PDF·사퇴 근거 |
| GET /sources/{filename} | 등록된 가상 공약 PDF만 제공 |
| GET /housing-review | 기사 검증·승인·반려 화면 |
| POST /api/housing-review/drafts | normal / missing_source / ai_mismatch 시나리오로 검수 초안 생성 |
| POST /api/housing-review/drafts/{id}/decision | approve / reject, reviewer, reason |
| GET /api/housing-review/history | 검증·처리 이력 최신 100건 |

승인 실패·중복 처리는 409, 반려 사유·검토자 누락은 422입니다. 개표 송신 중단·잘못된 모드는 election_feed_unavailable 오류로 전달합니다. 생성 AI API는 없고 저장 기사 조회입니다.

SNAPSHOT_VOTE.vote_share_pct는 누적 유효표를 분모로 소수 둘째 자리 반올림합니다. 0표 단계는 NULL입니다. synthetic 모드·DEMO 후보 ID를 사용합니다. 사퇴 후보는 개표 행에 포함되지 않습니다. 자치구별 득표 합은 모든 단계에서 전체 후보별 득표와 일치해야 합니다.

## 질문 기반 초안 생성

POST /api/housing/generate와 GET /api/housing-review/drafts, GET /api/housing-review/drafts/{id}를 추가했습니다. 검색·발췌 방식이며 외부 AI는 사용하지 않습니다. [요청·저장·제한](article-generation.md)을 참고하세요.
