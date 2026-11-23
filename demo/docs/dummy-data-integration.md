# 후보·공약·PDF·CSV 통합 기준 (2026-11-23)

## 적용 범위

main 3634b81의 문서·설계를 유지하고 PR #6 05a4b778의 검증·승인 코드를 기반으로 새 후보 6명에 맞췄습니다. 기존 main이나 팀원 브랜치를 직접 수정하지 않고 별도 PR로 제안하는 변경입니다.

| 후보 ID | 이름 | 정당 | 상태 |
| --- | --- | --- | --- |
| DEMO-C01 | 강도윤 | 가상 생활당 | 출마 |
| DEMO-C02 | 오세훈 | 국민의힘 | 기존 수집 공약 유지 |
| DEMO-C03 | 서지안 | 가상 미래당 | 출마 |
| DEMO-C04 | 한서준 | 가상 돌봄당 | 출마 |
| DEMO-C05 | 윤채린 | 가상 녹색당 | 출마 |
| DEMO-C06 | 백태오 | 가상 참여당 | 사퇴 |

후보 이름 옆에는 ‘가상 인물’ 표식을 붙이지 않습니다. 데이터의 data_kind와 전체 시뮬레이션 안내는 보존합니다. 가상 인물·정당은 실존 동명이인과 무관합니다. 오세훈의 공약 본문과 인용은 유지했지만 모든 득표·순위·역전·당선은 교육용 설정입니다. 과거 선거 비교는 기존 참고 데이터이며 이번 전환에서 재검증하지 않았습니다. 현재 가상 선거와 혼동할 수 있는 기존 2026 비교 행은 제거했습니다.

## 무엇을 기준으로 수정하나

`data/source_build/seed.json`이 후보와 공약의 생성 기준입니다. 실행용 JSON/CSV/PDF를 따로 고치면 연결이 어긋납니다. 수정 후 `python generate_demo.py`를 실행하세요. 생성에만 reportlab이 필요하며 서버 실행에는 필요 없습니다. 검증은 `python -m unittest -v`입니다.

기존 모의 개표 후보 순서 01~05를 새 후보 ID로 옮겼고, 사퇴 후보는 `SEOUL-WD-06 → DEMO-C06`입니다. 이전 인물의 약력·사진·공약을 새 인물에게 귀속시킨 것이 아닙니다. 연결표는 `data/candidate_id_mapping.csv`입니다.

## ERD 테이블과 CSV

| 문서 번호 | 테이블 | 파일 | 기준 행 수 |
| --- | --- | --- | ---: |
| DB-01 | CANDIDATE | data/tables/CANDIDATE.csv | 6 |
| DB-02 | SNAPSHOT | data/tables/SNAPSHOT.csv | 31 |
| DB-03 | SNAPSHOT_VOTE | data/tables/SNAPSHOT_VOTE.csv | 155 |
| DB-04 | SOURCE | data/tables/SOURCE.csv | 8 |
| DB-05 | EVIDENCE | data/tables/EVIDENCE.csv | 9 |
| DB-06 | ARTICLE | data/tables/ARTICLE.csv | 1 |
| DB-07 | ARTICLE_EVIDENCE | data/tables/ARTICLE_EVIDENCE.csv | 7 |
| DB-08 | FACT_CHECK | data/tables/FACT_CHECK.csv | 0 |
| DB-09 | REVIEW | data/tables/REVIEW.csv | 0 |
| 지도 확장 | DISTRICT | data/tables/DISTRICT.csv | 25 |
| 지도 확장 | DISTRICT_VOTE | data/tables/DISTRICT_VOTE.csv | 3,875 |

CSV는 UTF-8 BOM이며 쉼표·줄바꿈은 CSV 규칙으로 인용합니다. 비어 있는 필드는 NULL입니다. EVIDENCE는 공약 검색 청크 8개 + 사퇴 상태 근거 1개이며, 사퇴 상태 근거를 공약 검색 결과에 넣지 않습니다. ARTICLE_EVIDENCE는 문장별 공약 6개 + 사퇴 상태 연결 1개입니다. 실제 검수·승인을 만들어 채우지 않으므로 FACT_CHECK와 REVIEW의 기본 CSV는 헤더만 있습니다.

`schema.sql`은 SQLite용 실행 스키마이고 `python table_data.py`는 CSV를 메모리 DB에 적재하여 PK·FK·제약을 검사합니다. 현재 운영 Supabase DB에 적용한 것이 아닙니다. 실제 검증·승인 API는 별도 데모 DB `housing-review-demo-v2.sqlite3`에 이 테이블과 기존 drafts/audit를 함께 만들고 ARTICLE·ARTICLE_EVIDENCE·FACT_CHECK·REVIEW를 기록합니다. 기존 실데이터 검수 DB와 섞지 않도록 새 기본 파일명을 사용합니다. HOUSING_REVIEW_DB를 지정할 때도 기존 DB를 재사용하지 마세요.

근거 추적 경로:

1. 공약 기사: ARTICLE → ARTICLE_EVIDENCE.chunk_id → EVIDENCE.source_id → SOURCE의 PDF.
2. 후보 연결: EVIDENCE.candidate_id → CANDIDATE.
3. 개표 기사 수치: SNAPSHOT_VOTE.row_id → event_id·candidate_id → SNAPSHOT·CANDIDATE.
4. 지도: DISTRICT_VOTE(event_id, district_id, candidate_id)의 합계가 같은 단계의 SNAPSHOT_VOTE와 일치.

## PDF 확인 결과

오세훈의 저장된 `20260603_서울특별시_오세훈_5대공약.pdf`는 Drive 뷰어에서 총 5쪽을 확인했습니다. 검색에 사용하는 PDF 1쪽(31만 호 착공·3년 8.5만 호), 2쪽(공공주택 약 13만 호·월세 지원), 4쪽(고령친화 리모델링 포함) 본문을 확인했습니다. 기존 문서 ID와 인용 쪽수·본문을 유지했습니다. ‘착공’과 ‘공급’, ‘약’, 2031년이라는 목표 기간을 임의로 바꾸지 않았습니다. 공약 이행이나 정책 실현 가능성을 검증한 것은 아닙니다.

가상 공약서는 `data/pdf/DEMO-DOC-01.pdf`, 03, 04, 05, 06의 5개 파일입니다. 실제 생성된 각 PDF의 1쪽을 인용합니다. 문서 본문은 검색 JSON과 같은 텍스트이고 PDF마다 후보·문서 ID를 적었습니다. 가상 문서에 선관위 링크를 붙이지 않습니다. 오세훈 실제 PDF는 기존 Drive·공식 출처 링크를 유지합니다. 원본 PDF 바이너리를 수정하거나 재배포하지 않았습니다.

새 가상 PDF가 나오기 전의 ‘주거-1절’ 인용은 현재 적용하지 않습니다. 실제 PDF를 만들었으므로 `[DEMO-DOC-01, PDF 1쪽]`처럼 인용합니다.

주거 지원 예산은 가구 수 × 월 150,000원 × 48개월입니다. 행정비는 정하지 않았고, 시비 70%·기금 30%는 창작 설정입니다. 실현 가능성·재원 확보 사실이 아닙니다. 오세훈 자료는 정책 범위가 다르므로 동일 조건의 우열 비교로 사용하면 안 됩니다.

## 연동 수정

- 기존 BM25+한글 bigram 검색을 유지하고 실제·가상 PDF를 구분해 검증합니다.
- 사퇴 후보는 기본 검색·개표에서 제외하고 검색에서 명시적으로 포함할 수 있습니다.
- 두 역할 서버는 synthetic 스냅샷을 전달합니다. API 경로와 지도·예시 기사 기능을 유지합니다.
- 저장 기사는 6문장이며 공약·후보 ID·사퇴 표시를 함께 검증합니다. 문장 수, 수치, 근거, 후보 ID가 바뀌면 승인 차단합니다.
- AI 판정은 기존과 같은 시연용 fixture이며 외부 AI의 실시간 판정이 아닙니다. LLM 자동 기사 생성은 추가하지 않았습니다.
- 오프라인 두 HTML도 같은 생성 기준으로 갱신합니다. 서버 검증·영구 이력은 서버 실행 시에만 사용합니다.

실행 순서와 두 서버 명령은 demo/README.md를 따르세요. 자동 재생은 31단계, 60초입니다. 마지막은 유효표 1,000,000·무효표 10,000·총투표 1,010,000이며 백태오는 득표 행에 포함되지 않습니다.
