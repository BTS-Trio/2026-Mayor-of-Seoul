# 후보·공약·개표·검수 통합 데모

오세훈의 기존 수집 공약과 창작 후보 5명을 사용합니다. 모든 개표 수치·순위·역전·당선은 가상입니다. 현재 주거 공약 분야만 준비되어 있습니다.

## 실행

저장소의 demo 폴더에서 Windows PowerShell로 실행합니다. Python 3.10 문법 호환을 검사했고 실제 로컬 검증은 3.12 환경입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

터미널 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn election_source:app --host 127.0.0.1 --port 8001
```

터미널 2:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

http://127.0.0.1:8000/ 에서 새 대시보드 디자인과 내장 개표 예시를 확인합니다. **개표 재생·상세 데이터·공약 검색** 링크를 열면 기존 개표 재생과 지도·예시 기사 기능을 사용할 수 있습니다. /housing-search는 BM25 공약 검색, /housing-review는 기사 검증·승인·반려 이력입니다. 각 서버 역할은 로컬 두 프로세스로 시연합니다.

서버 없이 보려면 offline-preview.html 또는 최상위 Seoul-Election-Desk.html을 엽니다. 개표·예시 기사·저장 공약 기사를 확인할 수 있습니다. PDF를 열려면 함께 제공한 data/pdf 폴더도 유지해야 합니다. 서버 검증·영구 이력은 오프라인 파일에서 사용할 수 없습니다.

## 후보와 데이터

| ID | 이름 | 상태 |
| --- | --- | --- |
| DEMO-C01 | 강도윤 | 출마 |
| DEMO-C02 | 오세훈 | 실제 수집 공약 유지 |
| DEMO-C03 | 서지안 | 출마 |
| DEMO-C04 | 한서준 | 출마 |
| DEMO-C05 | 윤채린 | 출마 |
| DEMO-C06 | 백태오 | 사퇴·득표 제외 |

개표는 31단계·5명·25개 자치구입니다. 중반 강도윤 선두 → 최종 오세훈 역전은 창작 시나리오입니다. 최종 유효표 100만 + 무효표 1만 = 총투표 101만. 과거 선거 비교 자료는 기존 참고 정보이며 이번 작업에서 재검증하지 않았습니다.

공약은 실제 PDF 1개에서 3청크, 가상 PDF 5개에서 5청크입니다. 기본 검색 5명, include_withdrawn=true일 때 6명을 반환할 수 있습니다. 가상 공약도 실제 PDF를 생성했으므로 PDF 1쪽을 근거로 연결합니다. 가상 공약에 공식 출처를 붙이지 않습니다.

## 테이블 CSV·검증

`data/tables`에 ERD 9개 테이블 및 지도용 2개 테이블 CSV가 있습니다. `schema.sql`은 SQLite에서 실행할 수 있는 PK·FK·제약을 포함합니다. `python table_data.py`로 CSV를 메모리 DB에 적재하고 참조를 확인합니다. Supabase에 적용한 것은 아닙니다.

`data/source_build/seed.json`이 생성 기준이며 `python generate_demo.py`로 실행 데이터와 CSV·PDF·오프라인 화면을 함께 갱신합니다. 생성·테스트 의존성은 아래와 같습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest -v
```

실제 승인·반려는 새 기본 SQLite 파일 housing-review-demo-v2.sqlite3에 기록합니다. 기본 CSV의 FACT_CHECK·REVIEW는 헤더만 있으며 승인 결과를 미리 만들지 않았습니다. 기존 실데이터 검수 DB를 재사용하지 마세요.

[후보·공약·PDF·CSV 연결 상세 안내](docs/dummy-data-integration.md)

## 기능 한계

질문 기반 검색·발췌 초안 생성·DB 저장·재조회와 기존 공약 기사 조회·검증·승인 이력을 제공합니다. LLM 새 기사 자동 생성이나 실제 외부 AI 판정은 아닙니다. AI 판정은 시연용 fixture입니다. 공약 이행·실현 가능성을 판정하지 않습니다. 화면·기사·영상에서 실제 공약 일부와 가상 시나리오의 범위를 구분하고 사람이 최종 검수해야 합니다.

[질문 기반 초안 생성 사용법·저장 위치](docs/article-generation.md)
