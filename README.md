# 2026 서울시장 모의 개표·주거 공약 기사 시연

BTS-Trio의 교육용 데이터 저널리즘 프로젝트입니다. 서울 25개 자치구의 공식 개표 데이터를 모의 순서로 재생하고, 후보의 주거 공약 근거를 PDF 출처와 함께 확인합니다.

## 실행하기

먼저 [팀 통합본 ZIP](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/archive/refs/heads/main.zip)을 내려받아 압축을 풉니다.

| 보고 싶은 기능 | 실행 방법 |
| --- | --- |
| 오프라인 개표와 기사 검토 | 압축을 푼 폴더 맨 위의 [Seoul-Election-Desk.html](Seoul-Election-Desk.html)을 Chrome에서 엽니다. **처음부터 재생**을 누르면 개표를 볼 수 있고, 예시 기사로 승인·득표수 오류 차단·반려를 시연할 수 있습니다. |
| 두 서버를 이용한 개표 재생 | [상세 실행 안내](demo/README.md#2-두-서버로-개표-전송-실행하기)에 따라 `demo` 폴더에서 선관위 역할 서버와 방송사 역할 서버를 실행합니다. 그런 다음 Chrome에서 `http://127.0.0.1:8000/`을 엽니다. |
| 주거 공약의 출처 확인 | 방송사 역할 서버를 켜고 Chrome에서 `http://127.0.0.1:8000/housing-search`를 엽니다. **월세 지원**처럼 검색어를 입력하면 관련 근거와 PDF 쪽수, 출처 링크를 볼 수 있습니다. |

공식 개표 원본의 득표수를 바탕으로 하며, 재생 시각과 집계 순서는 시연용입니다. 승인과 반려는 예시 기사로 시연합니다.

## 프로젝트 문서

- [상세 실행 안내와 데이터 파일 목록](demo/README.md)
- [주거 공약 검색 자료와 검수 기준](demo/docs/housing-search.md)
- [데이터 구조와 ERD 초안](demo/docs/data-and-api.md#erd-초안)
- [통합 PR #3과 병합 기록](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/pull/3)
- [Windows 통합 자동 테스트 결과](https://github.com/BTS-Trio/2026-Mayor-of-Seoul/actions/runs/45110068758)
