# 프로젝트 1 · 2026 서울시장 개표 시뮬레이션

제9회 전국동시지방선거 서울특별시장 선거를 대상으로 2026년 6월 3일 개표 상황을 모의 재생합니다. 중앙선거관리위원회의 공식 개표 원본에서 서울 25개 자치구의 929개 개표 단위를 골라 재생합니다. 단위별 득표수는 원본 그대로이며, 시간과 집계 순서를 모의 구성했습니다.

## 1. 바로 재생하기

압축을 풀고 `offline-preview.html`을 Chrome에서 엽니다. **처음부터 재생**을 누르면 데이터가 2초마다 바뀝니다. 이 파일의 재생은 브라우저 내부 타이머를 사용합니다.

## 2. WebSocket으로 실행하기

VS Code에서 압축을 푼 `election-2026` 폴더를 열고 **터미널 → 새 터미널**에서 아래 명령을 순서대로 실행합니다. Windows PowerShell 기준입니다.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Chrome에서 [127.0.0.1:8000](http://127.0.0.1:8000)을 열고 **처음부터 재생**을 누릅니다. 0%부터 100%까지 약 60초가 걸립니다. 서버 종료는 터미널에서 Ctrl+C입니다. API 키 없이 실행합니다. 연결이 끊긴 경우 **처음부터 재생**으로 새 연결을 엽니다. 각 브라우저는 별도 재생을 시작합니다.

Python 코드 구문은 3.10에 호환되며 실제 로컬 테스트 런타임은 3.12입니다. 수업 원문에는 Python 3.13.15가 표기돼 있으므로 제출용 환경은 팀과 강사 확인 후 확정합니다.

## 3. 데이터 파일

| 파일 | 내용 |
| --- | --- |
| `data/seoul_final_candidates.csv` | 공식 원본에서 검증한 5인 득표수와 최종 보도 교차 확인 득표율 |
| `data/seoul_final_totals.json` | 실제 선거일·선거인수·투표수·무효표 |
| `data/raw/nec_governors_20260603.csv` | 전국 시·도지사선거 공식 원본 59,903행 |
| `data/seoul_final_by_district.csv` | 서울 25개 자치구별 공식 득표 집계 |
| `data/demo_reporting_schedule.csv` | 공식 개표 단위 929개의 가상 순서 및 시각 |
| `data/demo_snapshots.jsonl` | WebSocket에서 보내는 31개 누적 상태, 한 줄에 JSON 한 개 |
| `data/demo_candidates.csv` | Excel에서 확인할 수 있는 후보별 누적 데이터 155행 |
| `data/sources.csv` | 출처 및 원본 파일 확보 상태 |
| `docs/project-plan.md` | 프로젝트 1 요구사항·팀 분담·일정·GitHub 작업 방식 |
| `docs/data-and-api.md` | 데이터 사전·통신 명세·ERD 초안·정제 기록 |

데이터 검증은 `python -m unittest -v`를 사용합니다. 동일한 데이터를 다시 생성하려면 `python generate_demo.py`를 실행합니다.

## 4. GitHub 올리기

GitHub 오가니제이션에서 팀이 정한 저장소를 열고, VS Code로 복제한 폴더에 압축 안의 `election-2026` **안쪽 내용**을 복사합니다. 처음 작업은 `setup/project-1` 브랜치로 커밋하고 PR로 검토합니다. `.env`와 대용량 영상은 제외합니다. GitHub Desktop은 필요하지 않습니다. 조직 주소·저장소·쓰기 권한을 확인하면 팀이 계속 협업할 수 있습니다.

## 5. 진행 상태

개표 데이터·모의 대시보드·WebSocket 코드·출처 목록·검증 테스트·프로젝트 계획을 준비했습니다. 선관위 후보별 공약 원문 확보, RAG·기사 생성·규칙 검증·승인 화면, FHD 영상, PPT와 최종 보고서는 팀의 후속 작업입니다.


