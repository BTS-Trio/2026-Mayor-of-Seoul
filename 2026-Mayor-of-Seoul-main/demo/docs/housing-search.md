# 주거 공약 근거 검색

기사 질문: **2026년 서울시장 후보들은 주거 문제 해결을 위해 어떤 공약을 제시했나?**

방송사 서버를 실행한 뒤 /housing-search를 연다. 기존 개표 데스크의
주거 공약 근거 검색 링크에서도 이동할 수 있다. 개표 송신 서버가 꺼져
있어도 공약 검색은 독립적으로 동작한다.

## 등록 자료

- data/rag/housing_evidence.json: PDF 8개의 자료 정보, 검색 근거 17개,
  보류 근거 0개. 2026-11-23 정원오 선거공보 총 12쪽 및 PDF 7쪽 주거 본문 대조 완료.
- document_id는 드라이브 공약자료목록의 **공약자료ID**를 유지한다.
- pdf_page는 표지 포함 PDF 첫 페이지를 1쪽으로 센다.
- chunk_id는 프로그램 내부 검색 조각 식별자이며 공약자료ID와 다르다.
- text는 업로드 PDF의 추출된 공약 항목 또는 짧은 선거공보 발췌다.
  모든 PDF의 전체 본문을 등록한 데이터가 아니다.
- candidate_withdrawn으로 이강산의 사퇴 여부를 유지한다.
- pending_chunks는 검색과 인용에서 제외한다. 정원오 근거는
  [SEOUL26-PB-01, PDF 7쪽]으로 등록했다. 36만 호 이상은 2031년까지의 착공 목표다.
  검색 결과가 없다는 이유로 해당 후보에게 주거 공약이 없다고 쓰지 않는다.

원본 자료·발췌·쪽수를 먼저 검수한 뒤 JSON을 갱신한다. 이 버전의 검색
인덱스는 프로세스 안에서 캐시되므로, JSON 갱신 후 방송사 서버를 재시작한다.
표의 상태만 변경해도 JSON이 자동 갱신되는 기능은 없다.

## 검색 방식과 범위

housing_search.py는 BM25와 한글 2글자 단위 검색을 사용한다.
임베딩·외부 AI API 호출은 사용하지 않으며, 기사 초안 생성은 후속 단계다.

후보 전체의 주거 공약 비교 질문에는 관련 주거 용어를 함께 검색하고,
검색 가능한 후보의 상위 근거를 먼저 선택한다. limit가 후보 수보다
작으면 모든 후보를 포함할 수 없으므로 API의 coverage를 확인한다.
특정 후보를 선택하거나 질문에 후보 이름을 쓰면 그 후보만 검색한다.
쪽수 미확인 자료는 다른 후보의 자료로 대신 채우지 않는다.

## API

| 주소 | 용도 |
| --- | --- |
| GET /api/housing/status | 등록 자료 수·후보별 준비·보류 상태 |
| GET /api/housing/search?q=질문&candidate=후보명&limit=10 | 근거 검색 |
| GET /housing-search | 질문·근거·출처를 확인하는 페이지 |

candidate는 생략할 수 있고 limit는 1~30이다. 질문은 2~500자다.
결과에는 공약자료ID·후보명·쪽수·발췌·본문·인용 표기·저장 PDF·공식
제공처·직접 다운로드 주소·자료목록 링크가 유지된다.
입력 오류는 400, 자료 파일 누락·손상은 503으로 반환한다.
숫자 형식이 잘못된 limit는 FastAPI 요청 검증에서 422를 반환한다.

인용 예: [SEOUL26-P5-02, PDF 2쪽].
링크는 파일을 열며 특정 PDF 쪽으로 자동 이동하는 기능은 보장하지 않는다.
이 검색은 제출한 공약의 내용을 찾는 기능이고, 공약 이행·실적·실현
가능성을 사실검증한 결과가 아니다.

data/rag/housing_search_example.json은 2026-11-23 재검색 결과다.
결과 10개에 후보 6명 모두 포함, 누락·보류 0개를 확인했다.

docs/housing-article-draft-20261123.md에 인용이 붙은 기사 초안,
docs/housing-article-review-20261123.md에 문장별 원문 대조 기록을 보존했다.
기사 작성은 ChatGPT가 검색 결과를 바탕으로 수행했으며 자동 기사 생성 API는 구현하지 않았다.
이강산 사퇴는 candidate_status_sources의 NEC-SEOUL26-WD-001 공식 원문과 연결했다.

## 확인 방법

~~~powershell
python -m pip install -r requirements-dev.txt
python -m unittest test_housing_search -v
python -m unittest test_two_servers -v
~~~

신규 소스는 Python 3.10 문법으로 작성했다. 실제 API 테스트를 실행한
Python 버전과 결과는 작업 결과 보고에서 구분해 기록한다.
