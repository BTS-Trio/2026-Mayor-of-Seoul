# 프로젝트 1 · 2026 서울시장 개표 시뮬레이션

**11월 20일 최신 시연** · [오프라인 HTML 다운로드](https://raw.githubusercontent.com/BTS-Trio/2026-Mayor-of-Seoul/301773b868548970f93a3766a26fc07631160b0b/demo/offline-preview.html) · [두 서버 통합 테스트](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/actions/runs/44690562165)

HTML 파일을 저장해 Chrome에서 열고 **처음부터 재생**을 누릅니다. 이번 화면에서는 엠빅을 약 두 배로 키우고 흰 띠에 굵은 ‘선거’를 넣었습니다. 개표 제목과 자치구 이름도 굵게 표시합니다. Windows 통합 테스트에서 집계 31단계 순차 전송, 최종 개표율 100%·5,289,383표, 송신 서버 중단 시 오류 응답을 확인했습니다.

제9회 전국동시지방선거 서울특별시장 선거를 대상으로 2026년 6월 3일 개표 상황을 모의 재생합니다. 중앙선거관리위원회의 공식 개표 원본에서 서울 25개 자치구의 929개 개표 단위를 골라 재생합니다. 단위별 득표수는 원본 그대로이며, 시간과 집계 순서를 모의 구성했습니다.

## 1. 바로 재생하기

압축을 풀고 `offline-preview.html`을 Chrome에서 엽니다. **처음부터 재생**을 누르면 데이터가 2초마다 바뀝니다. 이 파일의 재생은 브라우저 내부 타이머를 사용합니다.

## 2. 두 서버로 개표 전송 실행하기

**선관위 역할 서버(8001) → 방송사 역할 서버(8000) → Chrome 화면** 순서입니다. 화면에서 재생을 누르면 방송사 서버가 선관위 역할 서버에 연결합니다. 선관위 역할 서버가 공식 개표 데이터 기반의 가상 집계 결과를 차례로 보내면 방송사 서버가 받아 화면에 전달합니다. 두 서버는 한 PC에서 별도 터미널로 실행할 수 있습니다.

VS Code에서 저장소의 `demo` 폴더를 열고 Windows PowerShell에서 한 번만 설치합니다.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**터미널 1에서 선관위 역할 서버를 시작합니다.**

```powershell
.\.venv\Scripts\python.exe -m uvicorn election_source:app --host 127.0.0.1 --port 8001
```

**터미널 2에서 방송사 역할 서버를 시작합니다.**

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Chrome에서 [방송사 화면](http://127.0.0.1:8000)을 열고 **처음부터 재생**을 누릅니다. 약 60초 동안 31단계로 0%에서 100%까지 갱신됩니다. 서버를 끄려면 각 터미널에서 Ctrl+C를 누릅니다.

- [선관위 역할 서버 확인](http://127.0.0.1:8001/health)은 `election-source`, [방송사 서버 확인](http://127.0.0.1:8000/health)은 `broadcast`를 표시합니다.
- 선관위 역할 서버를 끄면 방송사 화면에서 연결 오류를 확인할 수 있습니다. 서버를 다시 시작한 뒤 **처음부터 재생**합니다.
- 서버 사이의 데이터 주소는 기본 `ws://127.0.0.1:8001/ws/feed`입니다. 브라우저는 방송사 서버의 `/ws/replay`에 연결합니다.
- 시연용 승인·반려는 현재 탭 안에서 처리합니다. 기사·출처 및 검증·승인 서버 기능은 별도 팀 작업입니다.

### 지도와 역대 비교

- 개표 화면에서 서울 자치구 타일을 누르면 그 구의 누적 집계 수와 후보별 득표가 나온다. 모의 중간 개표에서는 **선두**, 완료 후에는 **구별 1위**를 표시한다.
- 역대 비교 패널은 당선자와 주요 경쟁 후보의 서울 전체 득표율, 자치구별 선두 수를 요약한다. 타일 지도는 위치를 단순화했다.
- 엠빅 이미지는 프로젝트에 제공된 참고 이미지다. 화면에 MBC 캐릭터 표기와 교육용 시뮬레이션 표기를 넣었다.
- 두 서버 통합 검증은 `python -m unittest test_two_servers -v`로 실행한다. 검사 중 두 개의 테스트 서버가 자동으로 시작·종료된다.

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


