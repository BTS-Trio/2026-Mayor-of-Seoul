# 2026 서울시장 모의 개표·주거 공약 기사 시연

BTS-Trio의 교육용 데이터 저널리즘 프로젝트입니다. 후보 6명 기준 가상 개표 데이터를 재생하고, 후보별 주거 공약을 원문 근거와 함께 검색하여 기사 검토·승인으로 연결하는 과정을 실습합니다.

> 현재 전환: [후보·공약·PDF·CSV 통합 안내](demo/docs/dummy-data-integration.md). 오세훈 공약 일부는 실제 수집 자료이고 나머지 공약과 모든 현재 개표 수치는 가상입니다. 이 변경 브랜치에는 PR #6의 검증·승인 코드를 포함했습니다. main 반영 여부는 PR 병합 상태와 구분하세요.

> 이전 문서 기준: 2026-11-23 전환 전 main의 코드·데이터 및 PR #6 상태 확인 시점. 현재 개표 수치·시각·순서는 모두 가상입니다. 실제 중앙선거관리위원회나 방송사의 운영 서버에 연결하는 서비스가 아닙니다.

## 목차

- [빠른 실행](#빠른-실행)
- [1. 기획서](#1-기획서)
- [2. 요구사항 정의서](#2-요구사항-정의서)
- [3. WBS](#3-wbs)
- [4. 화면 설계서](#4-화면-설계서)
- [5. ERD](#5-erd)
- [6. API 명세서](#6-api-명세서)
- [7. 시스템 아키텍처](#7-시스템-아키텍처)
- [8. 검수 및 관련 자료](#8-검수-및-관련-자료)

## 빠른 실행

[팀 통합본 ZIP](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/archive/refs/heads/main.zip)을 내려받아 압축을 풉니다.

| 보고 싶은 기능 | 실행 방법 |
| --- | --- |
| 오프라인 개표·예시 기사 검토 | 최상위 [Seoul-Election-Desk.html](Seoul-Election-Desk.html)을 Chrome에서 엽니다. 예시 기사 승인·득표수 오류 차단·반려 시연입니다. |
| 두 서버를 이용한 개표 재생 | 아래 명령으로 서버 두 개를 실행하고 http://127.0.0.1:8000/ 에 접속합니다. |
| 공약 근거 검색 | 방송사 역할 서버 실행 후 http://127.0.0.1:8000/housing-search 에 접속합니다. |
| 저장된 주거 공약 기사 조회 | 방송사 역할 서버의 GET /api/housing/draft를 사용합니다. 새 기사를 자동 생성하는 API가 아닙니다. |

Windows PowerShell에서 저장소의 `demo` 폴더를 작업 위치로 사용합니다.

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

터미널 1 — 선관위 역할 송신 서버:

```powershell
.\.venv\Scripts\python.exe -m uvicorn election_source:app --host 127.0.0.1 --port 8001
```

터미널 2 — 방송사 역할 수신 서버:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

브라우저에서 **처음부터 재생**을 누르면 기본 2초 간격으로 31개 상태가 전달됩니다. 약 60초 후 모의 집계가 완료됩니다. 각 터미널의 Ctrl+C로 종료합니다. Python 3.10 문법 호환을 목표로 작성했으며, 기존 검색 검증 기록의 실제 실행 환경은 Python 3.12.10입니다. 이 README 수정에서는 프로그램 테스트를 새로 실행하지 않았습니다.

## 1. 기획서

### 목적과 배경

과제 주제는 **RAG 모델 기반의 선거 보도 구성하기**입니다. 개표 숫자와 후보 공약의 원문을 함께 다루면서, 기사의 사실 문장이 어느 자료에서 나왔는지 추적하고 사람이 검수하는 과정을 구현합니다.

개표 수치는 기준 시각·지역·후보가 바뀌면 의미가 달라집니다. 공약은 공급·착공, 임기 내 목표·장기 목표 등을 혼동하기 쉽습니다. 따라서 데이터 재생과 출처 검색, 기사 검토를 연결하고 오류 및 근거 누락을 확인하는 것을 핵심 과제로 삼습니다.

### 목표와 범위

| 구분 | 내용 |
| --- | --- |
| 개표 질문 | 모의 개표 단계에 따라 후보 간 득표와 격차가 어떻게 달라지는가? |
| 공약 질문 | 2026년 서울시장 후보들은 주거 문제 해결을 위해 어떤 공약을 제시했나? |
| 데이터 범위 | 서울 25개 자치구·750개 가상 재생 단위, 전체·구별 후보 득표 일치 |
| 공약 자료 | 실제 PDF 1개+가상 PDF 5개, 검색 근거 8개, 보류 0개, 후보 6명(1명 사퇴) |
| 기사 결과물 | 자료 ID와 PDF 쪽수가 연결된 저장 기사 초안 및 원문 대조 기록 |
| 영상 결과물 | 최근 제작 방향에 따른 10분 개표방송 영상. 제작·완료 여부는 별도 관리 |
| 제외 범위 | 실제 실시간 개표 수신, 당선 예측, 공약 실현 가능성 판정, 자동 게재 |

개표 데이터의 후보는 5명이며 공약 자료의 후보는 사퇴 후보를 포함한 6명입니다. 두 목록을 개수나 배열 순서로 대응시키지 않습니다. 공약자료ID, 검색 조각 ID, 후보 ID는 각각의 용도가 다릅니다. 현재 후보 연결은 DEMO-C01~06으로 통일했습니다.

### 기능 구현 상태

| 기능 | 현재 상태 |
| --- | --- |
| 모의 개표 전송·수신·대시보드 | 이 브랜치에 코드 있음 |
| 공약 근거 검색·PDF 출처 연결 | 이 브랜치에 코드·검색 자료 있음 |
| 저장 기사 초안과 문장별 출처 조회 | main의 /api/housing/draft에 구현 |
| 오프라인 예시 기사 승인·오류 차단·반려 | 독립 HTML 시연 기능 |
| 주거 공약 기사 서버 검증·SQLite 승인·반려 이력 | 이 변경 브랜치에 PR #6 구현 포함; main 병합 전 |
| AI 기사 자동 생성 API·실제 외부 AI 판정 | main에 구현되지 않음. PR #6의 AI 판정도 시연용 값 |

검색은 BM25와 한글 2글자 검색을 사용합니다. 임베딩이나 외부 AI API를 호출하는 구현으로 설명하지 않습니다.

## 2. 요구사항 정의서

### 기능을 4가지로 구분

| 기능 그룹 | 주요 기능 | 요구사항 num | 화면 num | DB num |
| --- | --- | --- | --- | --- |
| G-01 개표 현황 | 모의 재생·득표·자치구 집계·연결 오류 | FR-01~FR-03 | UI-01, UI-04(예시) | DB-01~DB-03 |
| G-02 공약·근거 검색 | 질문·후보 검색·PDF 원문 확인 | FR-04, FR-05 | UI-02, UI-03(원문 대조) | DB-04, DB-05 |
| G-03 기사 작성·출처 확인 | 저장 기사 조회·문장별 인용·새 기사 생성(예정) | FR-06, FR-09 | UI-03, UI-02(02-4·예정), UI-04(예시) | DB-04~DB-07 |
| G-04 검증·승인·이력 | 오류 차단·승인·반려·이력 | FR-07, FR-08 | UI-05(PR #6), UI-04(예시) | DB-04~DB-09 |

NFR-01~NFR-04는 네 그룹에 걸친 공통 품질·검수 요구사항입니다. DB 번호는 아래 ERD의 논리 설계 항목 번호이며 실제 DB 구현 완료를 뜻하지 않습니다. UI-04는 예시 시연이며 서버 검증·영구 이력 요구사항을 충족한 것으로 간주하지 않습니다.

현재 상태는 코드 존재 여부를 뜻하며 최종 사용자 검수 완료를 뜻하지 않습니다.

| ID | 사용자 요구사항·기능 | 완료 기준 | 현재 상태 | 관련 화면 num | 관련 DB num |
| --- | --- | --- | --- | --- | --- |
| FR-01 | 모의 개표 재생 | 0~30 순번 전달, 최종 complete=true | 이 브랜치 구현 | UI-01(01-1), UI-04(04-1·예시) | DB-02, DB-03 |
| FR-02 | 후보·자치구 집계 확인 | 후보별 누적표·득표율과 자치구 집계를 표시 | 이 브랜치 구현 | UI-01(01-2), UI-04(04-1·예시) | DB-01, DB-02, DB-03 |
| FR-03 | 연결 실패 확인 | 송신 서버 장애 시 오류 코드·안내 전달 | 이 브랜치 구현 | UI-01(01-1) | 해당 없음(통신 오류) |
| FR-04 | 질문·후보로 공약 검색 | 관련 근거와 후보별 반환 여부 제공 | 이 브랜치 구현 | UI-02(02-1, 02-2) | DB-04, DB-05 |
| FR-05 | 원문 근거 확인 | 공약자료ID·PDF 쪽수·발췌·출처 링크 보존 | 이 브랜치 구현 | UI-02(02-3), UI-03(03-3) | DB-04, DB-05 |
| FR-06 | 기사 문장별 출처 확인 | 저장 초안 문장과 인용 링크 조회 | 이 브랜치 구현 | UI-03(03-1~03-3), UI-04(04-1·예시) | DB-04, DB-05, DB-06, DB-07 |
| FR-07 | 잘못된 기사 승인 차단 | 검증 실패 시 서버에서 승인 거부 | PR #6 기반 코드 포함(이 브랜치) | UI-05(05-1, 05-2); UI-04(04-2·예시) | DB-04, DB-05, DB-06, DB-07, DB-08 |
| FR-08 | 승인·반려 기록 보존 | 사유·처리 이력 저장 및 재조회 | PR #6 기반 코드 포함(이 브랜치) | UI-05(05-2, 05-3); UI-04(04-2, 04-3·예시) | DB-06, DB-09 |
| FR-09 | 근거 기반 새 기사 생성 | 검색 근거와 문장별 인용을 갖춘 새 초안 반환 | 검색·발췌 초안 API 구현, 외부 LLM 재작성 미구현 | UI-02(02-4·예정), UI-03(03-1, 03-2·확장 예정) | DB-04, DB-05, DB-06, DB-07(생성 저장은 예정) |
| NFR-01 | 실제·모의 데이터 구분 | synthetic 및 가상 시각 표시 유지 | 코드·제출물 교차 검수 | UI-01, UI-04 | DB-02, DB-03 |
| NFR-02 | 출처·사퇴 상태 보존 | 자료 ID·쪽수·사퇴 근거를 원문과 대조 | 데이터·기사 검수 | UI-02(02-3), UI-03(03-2, 03-3) | DB-04, DB-05, DB-07 |
| NFR-03 | 실행 재현성 | 설치·실행·환경 변수 안내로 동일 데이터 재생 | 실행 안내 제공 | 해당 없음(실행·설치 문서) | 해당 없음 |
| NFR-04 | 보도 책임·보안 | 사람 검수, AI 사용 표시, 비밀키·개인정보 제외 | 최종 제출 검수 | UI-01~UI-05(공통 검수) | DB-04, DB-05, DB-06, DB-07, DB-08, DB-09(검수 관련 설계) |

## 3. WBS

기존 [작업 계획](demo/docs/project-plan.md)의 역할·일정을 바탕으로 정리했습니다. 날짜는 팀 확인용 계획이며, 실제 완료일로 간주하지 않습니다. 기존 계획의 약 20분 영상 대신 이번 정리에서는 최근 요청인 10분을 적용합니다.

| WBS | 작업 | 담당 | 선행 작업 | 계획 일정 | 산출물·확인 기준 |
| --- | --- | --- | --- | --- | --- |
| 1 | 주제·보도 질문·범위 확정 | 공동 | — | 11/20 | 기획·요구사항 |
| 2 | 공식 개표·후보·공약 자료 확보 | 윤 | 1 | 11/20~23 | 원본·자료목록·근거 ID |
| 3 | 데이터 정제·모의 집계 검수 | 윤 | 2 | 11/23 | CSV·JSONL·검수 기록 |
| 4 | 화면·메뉴 설계 | 흠 | 1 | 11/20~23 | 화면 기능·이동 흐름 |
| 5 | ERD·통신·시스템 설계 | 태 | 3, 4 | 11/20~23 | ERD·API·아키텍처 |
| 6 | 송신·수신 서버와 개표 화면 연결 | 태·흠 | 5 | 11/23~24 | 두 서버 개표 시연 |
| 7 | 공약 검색·기사 근거 연결 | 윤 | 2 | 11/23~25 | 검색 결과·기사·문장별 출처 |
| 8 | 서버 검증·승인·반려 이력 연결 | 태·흠 | 6, 7 | 11/24~25 | 검증·저장·재조회 |
| 9 | 교차 검수·사람 승인 | 공동 | 7, 8 | 11/25~26 | 정상·오류 사례 및 수정 기록 |
| 10 | 10분 방송 대본·CG·자막·편집 | 흠 중심·공동 검수 | 7, 9 | 11/24~26 | 영상·대본·출처표 |
| 11 | 통합 검사·발표·보고 | 공동 | 6~10 | 11/26~27 | README·시연·PPT·보고서 |

현재 진행 상태의 근거는 main 코드와 연결된 PR을 사용합니다. 과거 계획표의 일정만 보고 완료 표시하지 않습니다.

## 4. 화면 설계서

화면 **UI-01~UI-05**, 영역 **01-1~05-3**, 요구사항 **FR/NFR**, DB **DB-01~DB-09**를 함께 표시합니다. UI-01은 사용자가 제공한 상·중·하단 캡처를 연결해 실제 배치를 재구성한 설계 이미지입니다. 나머지 이미지는 기능 기반 구성도로, 해당 화면의 실제 배치를 확인한 자료가 아닙니다. **예정·논리 대응은 구현 완료를 뜻하지 않습니다.** PR 상태는 문서 기준 시점입니다. NFR-04는 모든 화면의 공통 검수 항목입니다.

### 01. 개표 데스크

![01. 스크린샷 기반 개표 데스크 전체 화면 설계](docs/images/ui-01-wireframe.svg)

사용자가 제공한 3개 캡처의 상·중·하단을 연결해 재구성했습니다. **상단 배너 → 왼쪽 개표·지도·득표표 / 오른쪽 기사 검토 → 하단 전체 폭 역대 비교**의 실제 배치를 반영했습니다. 배너·캐릭터는 위치만 표시하고 일부 문구는 축약했습니다. 득표표 수치는 캡처 표기 재현이며 이번 문서 수정에서 공식 원문을 재검증한 것은 아닙니다.

| 영역 num | 구성 | 역할 | 관련 요구사항 num | 관련 DB num |
| --- | --- | --- | --- | --- |
| 01-0 | 상단 제목·배너 | 모의 개표 안내·제목·이미지 | NFR-01, NFR-04 | 직접 조회 없음 |
| 01-1 | 개표 현황 | 재생·연결 상태·진행률·시각·근거 행 ID | FR-01, FR-03, NFR-01 | DB-02, DB-03. 연결 오류 자체는 DB 없음 |
| 01-2a | 자치구 타일 지도 | 후보별 색상·구별 선두·선택 구 상세 | FR-02 | DB-01~DB-03(논리 대응). 구별 집계 세부 스키마는 추가 설계 필요 |
| 01-2b | 후보별 누적 득표표 | 후보·정당·누적 득표수·득표율 | FR-02 | DB-01, DB-02, DB-03 |
| 01-3 | 오른쪽 기사 검토·기능 이동 | 공약 검색 링크·주거 공약 기사 펼침 | FR-04, FR-06(이동·조회) | DB-04~DB-07(대상 기능의 논리 대응) |
| 04-1 | 오른쪽 득표 예시 기사 영역 | 예시 기사 생성·오류 입력·기사 표시 | FR-06(예시) | DB-02, DB-03, DB-06, DB-07(논리 대응) |
| 04-2 | 오른쪽 검증·반려 입력 | 검증 결과·반려 사유·승인/반려 | FR-07, FR-08(예시만) | DB-06, DB-08, DB-09(논리 대응·영구 저장 의미 아님) |
| 01-4 | 하단 역대 선거 비교 | 연도별 득표율·자치구 선두 분포 | FR-02와 관련. 역대 비교 세부 요구사항 번호 미정 | 전용 DB 번호 미정. 기존 SNAPSHOT 설계가 역대 비교를 지원한다고 단정하지 않음 |

경로·대상: `UI-01 · /` · 상태: **제공 캡처 기반 재구성**

UI-03의 기사·출처 기능과 UI-04에서 설명한 예시 검토 기능은 이 데스크의 오른쪽 패널에서도 나타납니다. 화면 번호는 기능 설명을 참조하는 번호이며 각각이 반드시 별도 페이지라는 뜻은 아닙니다. 접힌 주거 공약 기사 본문과 별도 검색 결과 화면은 아직 캡처가 없어 내부 배치를 재구성하지 않았습니다.

### 02. 주거 공약 근거 검색

![02. 주거 공약 근거 검색 — 요구사항·DB 번호 연결](docs/images/ui-02-wireframe.svg)

| 영역 num | 구성 | 역할 | 관련 요구사항 num | 관련 DB num |
| --- | --- | --- | --- | --- |
| 02-1 | 검색 조건 입력 | 질문 / 후보 / 검색 개수 / 검색 실행 | FR-04 | DB-04, DB-05 |
| 02-2 | 검색 결과·포함 여부 | 근거 본문 / 후보별 반환·누락·보류 | FR-04 | DB-04, DB-05 |
| 02-3 | 자료 출처 확인 | 공약자료ID / PDF 쪽수 / 원문 링크 | FR-05, NFR-02 | DB-04, DB-05 |
| 02-4 | 기사 생성 요청 [추가 설계·미구현] | 근거 선택 / 기사 생성 / 진행·실패 안내 → UI-03 | FR-09(예정) | DB-04, DB-05, DB-06, DB-07 |

경로·대상: `UI-02 · /housing-search` · 상태: **검색 구현 / 생성은 설계 예정**

### 03. 기사 초안·문장별 출처

![03. 기사 초안·문장별 출처 — 요구사항·DB 번호 연결](docs/images/ui-03-wireframe.svg)

| 영역 num | 구성 | 역할 | 관련 요구사항 num | 관련 DB num |
| --- | --- | --- | --- | --- |
| 03-1 | 기사 불러오기·결과 표시 | 현재: 저장 기사 조회 / 예정: 생성된 새 기사 표시 | FR-06, FR-09(확장 예정) | DB-06 |
| 03-2 | 문장과 인용 연결 | 문장 본문 / 공약자료ID·PDF 쪽수 / 사퇴 근거 | FR-06, NFR-02, FR-09(확장 예정) | DB-04, DB-05, DB-06, DB-07 |
| 03-3 | 원문 대조 | 출처 열기 / 수치·대상·기간 확인 / 사람 검수 | FR-05, FR-06, NFR-02, NFR-04 | DB-04, DB-05, DB-06, DB-07 |

경로·대상: `UI-03 · 개표 데스크의 기사 검토 영역` · 상태: **저장 기사 조회 구현 / 생성 결과는 확장 예정**

### 04. 오프라인 예시 기사 검토

![04. 오프라인 예시 기사 검토 — 요구사항·DB 번호 연결](docs/images/ui-04-wireframe.svg)

| 영역 num | 구성 | 역할 | 관련 요구사항 num | 관련 DB num |
| --- | --- | --- | --- | --- |
| 04-1 | 예시 기사 확인 | 모의 개표 / 예시 기사·근거 | FR-01, FR-02, FR-06(예시), NFR-01 | DB-01, DB-02, DB-03, DB-06, DB-07(논리 대응) |
| 04-2 | 검증·처리 예시 | 정상 예시 승인 / 득표 오류 차단 / 반려 | FR-07, FR-08(예시만) | DB-06, DB-08, DB-09(논리 대응) |
| 04-3 | 시연 결과 | 현재 시연 결과 표시 / 서버 영구 이력 저장 아님 | FR-08(예시만) | DB-09(논리 대응) |

경로·대상: `UI-04 · Seoul-Election-Desk.html` · 상태: **독립 HTML 예시 / 서버 저장과 구분**

### 05. 서버 검증·승인·반려 이력

![05. 서버 검증·승인·반려 이력 — 요구사항·DB 번호 연결](docs/images/ui-05-wireframe.svg)

| 영역 num | 구성 | 역할 | 관련 요구사항 num | 관련 DB num |
| --- | --- | --- | --- | --- |
| 05-1 | 검증 대상·결과 | 기사·근거 확인 / 서버 검증 / 실패 사유 | FR-07 | DB-04, DB-05, DB-06, DB-07, DB-08 |
| 05-2 | 승인·반려 처리 | 검증 결과 확인 / 승인 / 사유 입력 후 반려 | FR-07, FR-08 | DB-06, DB-08, DB-09 |
| 05-3 | 이력 저장·재조회 | SQLite 처리 이력 / 새로고침 후 보존 확인 | FR-08 | DB-06, DB-09 |

경로·대상: `UI-05 · PR #6 연결 대상` · 상태: **PR #6 / main 미병합·문서 기준 시점**

FR-09의 설계 흐름은 **02-4 근거 선택·생성 요청 → 03-1 새 초안 표시 → 03-2 문장별 근거 연결 → 03-3 사람 검수**입니다. 생성 버튼·생성 API·DB 저장은 미구현이며, 현재 GET /api/housing/draft는 저장 기사 6문장 조회입니다.

## 5. ERD

**DB num는 테이블별 문서 식별 번호입니다.** DB-01 CANDIDATE · DB-02 SNAPSHOT · DB-03 SNAPSHOT_VOTE · DB-04 SOURCE · DB-05 EVIDENCE · DB-06 ARTICLE · DB-07 ARTICLE_EVIDENCE · DB-08 FACT_CHECK · DB-09 REVIEW.

아래는 관계형 데이터베이스로 정리할 때의 **논리 설계**입니다. 현재 main의 개표·검색·기사는 CSV·JSONL·JSON·Markdown 파일로 저장합니다. 현재 전환에서는 schema.sql과 data/tables의 11개 CSV를 제공하고 SQLite 적재·PK/FK 검사를 구현했습니다. 운영 DB에 적용한 것은 아닙니다. 최신 대응표는 통합 안내를 우선합니다.

```mermaid
erDiagram
    CANDIDATE ||--o{ SNAPSHOT_VOTE : 득표
    SNAPSHOT ||--o{ SNAPSHOT_VOTE : 누적집계
    SNAPSHOT ||--o{ ARTICLE : 개표기사
    SOURCE ||--o{ EVIDENCE : 검색근거
    ARTICLE ||--o{ ARTICLE_EVIDENCE : 문장인용
    EVIDENCE ||--o{ ARTICLE_EVIDENCE : 문서연결
    SNAPSHOT_VOTE ||--o{ ARTICLE_EVIDENCE : 수치연결
    ARTICLE ||--o{ FACT_CHECK : 검증
    ARTICLE ||--o{ REVIEW : 승인반려
```

| DB num | 논리 테이블 | 키·주요 필드 설계 | 현재 대응 파일·상태 |
| --- | --- | --- | --- |
| DB-01 | CANDIDATE | candidate_id PK, name, party | demo/data/tables/CANDIDATE.csv(6명) 및 스냅샷 candidates(출마 5명) |
| DB-02 | SNAPSHOT | event_id PK, sequence, simulated_at, counted_ballots | demo/data/tables/SNAPSHOT.csv 및 demo_snapshots.jsonl |
| DB-03 | SNAPSHOT_VOTE | row_id PK, event_id FK, candidate_id FK, votes, vote_share_pct | demo/data/tables/SNAPSHOT_VOTE.csv 및 스냅샷 candidates 배열 |
| DB-04 | SOURCE | source_id PK, 기관·URL·자료 유형·날짜 | demo/data/sources.csv, housing_evidence.json의 documents·상태 출처 |
| DB-05 | EVIDENCE | chunk_id PK, source_id FK, document_id, pdf_page, text | demo/data/rag/housing_evidence.json의 chunks |
| DB-06 | ARTICLE | article_id PK, snapshot_id 선택 FK, 제목·본문·상태 | demo/docs/housing-article-draft-20261123.md. 공약 기사에는 개표 스냅샷 연결이 필수 아님 |
| DB-07 | ARTICLE_EVIDENCE | 연결 ID PK, article_id FK, 문장 번호, chunk_id 또는 row_id FK | demo/data/tables/ARTICLE_EVIDENCE.csv 및 실제 SQLite 테이블 |
| DB-08 | FACT_CHECK | 검사 ID PK, article_id FK, 결과·사유·시각 | demo/data/tables/FACT_CHECK.csv(기본 0행); 실행 시 SQLite 기록 |
| DB-09 | REVIEW | 검토 ID PK, article_id FK, 승인·반려·사유·처리자·시각 | SQLite 이력 연결은 PR #6 기반 코드 포함(이 브랜치). 실제 스키마는 병합 후 확인 |

설계 제약: SNAPSHOT_VOTE의 (event_id, candidate_id)는 유일하고 누적 득표는 0 이상입니다. 유효표가 0이면 득표율은 NULL입니다. ARTICLE_EVIDENCE는 문서 근거 또는 개표 수치 근거를 구분해 연결합니다. 파일상의 document_id와 후보 이름을 관계형 키로 옮기는 변환 규칙은 DB 구현 시 확정해야 합니다.

## 6. API 명세서

main의 [방송사 서버](demo/app.py), [송신 서버](demo/election_source.py), [검색 구현](demo/housing_search.py)을 기준으로 작성했습니다.

| 서버·포트 | 방식·경로 | 요청 | 응답·역할 |
| --- | --- | --- | --- |
| 송신 8001 | GET /health | 없음 | role=election-source, mode=synthetic |
| 송신 8001 | WS /ws/feed | 연결 | 스냅샷에 source_sent_at을 추가해 순차 송신 |
| 방송사 8000 | GET /health | 없음 | role=broadcast, mode=synthetic |
| 방송사 8000 | GET / | 없음 | 개표 데스크 HTML |
| 방송사 8000 | GET /api/final | 없음 | seoul_final_totals.json의 확정 집계 |
| 방송사 8000 | WS /ws/replay | 연결 | 순서를 검사한 스냅샷에 delivered_at을 추가해 전달 |
| 방송사 8000 | GET /housing-search | 없음 | 공약 검색 HTML |
| 방송사 8000 | GET /api/housing/status | 없음 | question, ready_chunks, pending_chunks, candidate_options 등 |
| 방송사 8000 | GET /api/housing/search | q, candidate 선택, limit=10 | query, results, coverage, retrieval_method, scope |
| 방송사 8000 | GET /api/housing/draft | 없음 | title, sentences 배열. 각 문장은 text와 citations(label, url) |

### 검색 요청·응답

- q: 앞뒤 공백 제거 후 2~500자.
- candidate: 등록된 후보명, 생략 가능.
- limit: 정수 1~30, 기본값 10.
- results: 공약자료ID(document_id), 검색 조각 ID(chunk_id), 후보, PDF 쪽수(pdf_page), 본문·발췌, 인용 표기, 출처 링크, 검색 점수.
- coverage: 요청 후보·반환 후보·누락 후보·보류 근거 및 전체 포함 여부. 결과가 없다고 해당 후보에게 공약이 없다고 판단하지 않습니다.

예: `GET /api/housing/search?q=월세%20지원&limit=10`

### 개표 메시지·오류

스냅샷의 주요 필드는 event=snapshot, event_id, sequence, mode=synthetic, simulated_at, counted_ballots, count_progress_pct, candidates, complete입니다. candidates에는 candidate_id, row_id, name, votes, vote_share_pct가 있습니다.

| 조건 | 처리 |
| --- | --- |
| 마지막 스냅샷 | complete=true 전송 후 WebSocket 정상 종료(1000) |
| 송신 서버 장애·시간 초과·잘못된 순번 | event=error, code=election_feed_unavailable 전송 후 종료(1011) |
| 검색 질문·후보·개수 범위 오류 | HTTP 400, detail 안내 |
| limit 정수 변환 실패 | HTTP 422, FastAPI 요청 검증 오류 |
| 검색 자료 누락·형식 오류 또는 초안 형식 오류 | HTTP 503, detail 안내 |

기사 자동 생성·승인·반려 API는 이 브랜치 구현 목록에 포함하지 않습니다. 이 브랜치에 포함된 검증·승인 API와 최신 스키마는 demo/docs/data-and-api.md 및 schema.sql을 참고하세요.

## 7. 시스템 아키텍처

![전체 시스템 아키텍처 — 줄바꿈과 여백을 확보한 구성도](docs/images/system-architecture.svg)

[아키텍처 원본 크게 보기](docs/images/system-architecture.svg)

긴 파일명과 설명을 줄바꿈한 SVG 구성도입니다. BM25 검색은 방송사 프로세스 내부 기능이며 별도 서버가 아닙니다. 실선은 main의 흐름, 점선은 문서 기준 시점 별도 PR의 연결 대상입니다.

- 두 역할 서버는 한 PC의 별도 프로세스로 실행할 수 있습니다. 방송사 서버가 브라우저와 송신 서버 사이를 중계합니다.
- 브라우저 연결마다 모의 재생을 새로 시작합니다. 실제 다수 사용자에게 동일 실시간 집계를 배포하는 운영 구조와 다릅니다.
- 송신 주소는 ELECTION_FEED_URL로 바꿀 수 있으며 기본값은 ws://127.0.0.1:8001/ws/feed입니다.
- 공약 검색은 방송사 프로세스 내부에서 수행하므로 송신 서버가 꺼져 있어도 사용할 수 있습니다.
- 검색 JSON은 프로세스 안에 캐시됩니다. 자료 변경 후 방송사 서버 재시작이 필요하며 Google Sheets와 자동 동기화되지 않습니다.
- 독립 HTML은 오프라인 실행 경로입니다. 두 서버 통신 및 서버 이력 저장과 구분합니다.
- main의 이 실행 구조에는 Supabase·Render 배포 연결이 포함되어 있지 않습니다.

## 8. 검수 및 관련 자료

### 제출 전 확인

- [ ] 공식 원문과 후보명·수치·단위·대상·기간·PDF 쪽수를 대조한다.
- [ ] 개표 후보 5명과 공약 자료 후보 6명의 차이 및 사퇴 표시를 유지한다.
- [ ] 모든 사실 문장에 근거를 연결하고 AI 작성 사실과 사람 검수 여부를 표시한다.
- [ ] 실제 수치와 가상 시각·순서·진행률을 화면·기사·영상에서 구분한다.
- [ ] 정상 흐름과 오류 차단·반려 흐름을 확인하고 미병합 기능을 완료로 표시하지 않는다.
- [ ] YouTube 영상·방송 이미지·캐릭터·음악의 사용 허락과 이용 조건을 확인한다. 온라인 공개가 자유 이용을 의미하지 않는다.
- [ ] AI 합성 영상·음성 표시, 정치적 편향·당선 예측 표현, 개인정보·비밀키 노출을 점검한다.

`demo` 폴더에서 기존 자동 검사를 실행할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest test_housing_search -v
.\.venv\Scripts\python.exe -m unittest test_two_servers -v
```

기존 [Windows 통합 자동 테스트 기록](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/actions/runs/45110068758)은 해당 커밋의 검사 결과입니다. 모든 후속 변경이나 실제 화면의 최종 검수를 보장하지 않습니다.

### 원본 문서·근거

- [상세 실행 안내와 데이터 목록](demo/README.md)
- [기존 작업 계획·역할·일정](demo/docs/project-plan.md)
- [데이터 사전·통신 명세·ERD 초안](demo/docs/data-and-api.md)
- [주거 공약 검색·출처·검수 기준](demo/docs/housing-search.md)
- [인용 기사 초안](demo/docs/housing-article-draft-20261123.md)
- [문장별 원문 대조·사퇴 출처·수정 기록](demo/docs/housing-article-review-20261123.md)
- [검색 자료 JSON](demo/data/rag/housing_evidence.json)
- [통합 PR #3](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/pull/3)
- [서버 검증·승인 이력 연결 PR #6](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/pull/6)

최신 후보·근거·PDF·CSV 연결과 검증 결과는 [통합 안내](demo/docs/dummy-data-integration.md) 및 [새 Windows 테스트](demo/docs/test-results.md)를 기준으로 합니다.

## 질문 기반 공약 초안 생성 추가

이 브랜치에서는 질문에 맞는 근거를 검색·발췌하여 새 공약 기사 초안을 생성하고 DB에 저장·재조회·검토·승인하는 기능을 추가했습니다. 외부 AI/LLM 재작성은 사용하지 않고 API 키가 필요 없습니다. 현재 범위는 주거 공약입니다. [사용법·저장·API](demo/docs/article-generation.md)를 참고하세요. 기존의 저장 기사 예시 및 AI 자동 생성 미구현 설명과 이 검색·발췌 방식의 신규 초안 기능을 구분합니다.
