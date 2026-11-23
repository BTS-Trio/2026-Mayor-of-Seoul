# 주거 공약 검색 검증 기록

검증일: 2026-11-20

## 실행한 검사

- Python 3.14 환경에서 검색·자료 무결성·인용 유지·오류 처리 등 15개 검사 통과.
- 신규 Python 소스의 Python 3.10 문법 파싱 통과. Python 3.10 런타임
  실행 검증을 했다는 의미는 아니다.
- housing-search.html의 JavaScript를 추출해 Node의 문법 검사 통과.
- 정한 기사 질문으로 실제 검색 실행: 근거 10개, 후보 5명.
  결과는 data/rag/housing_search_example.json에 보존.
- 정원오의 쪽수 미확인 근거는 검색에 포함하지 않고 보류 사유를 반환.
- 월세 지원 질문의 첫 결과는 SEOUL26-P5-02, PDF 2쪽.
- 김정철 역세권 소형 주택 질문의 첫 결과는 PDF 5쪽.
- 다른 후보 자료로 정원오의 결과를 채우지 않으며 사퇴 후보 표시를 유지.

## 아직 검증하지 못한 범위

현재 실행 환경에서 로컬 소켓 접근이 WinError 10013으로 차단되어
TestClient의 이벤트 루프 시작과 실제 두 서버 통신 검증이 완료되지 않았다.
이 제한을 검색 결과가 비어 있는 정상 응답으로 처리하지 않았다.
API 핸들러는 직접 호출해 결과·입력 오류·자료 오류를 검증했다.
HTTP 전달·브라우저 렌더링·기존 두 서버 통합 테스트는 별도 실행 환경에서
다음 명령으로 확인해야 한다.

~~~powershell
python -m pip install -r requirements-dev.txt
python -m unittest test_housing_search -v
python -m unittest test_two_servers -v
~~~

이번 변경은 검색까지다. 임베딩·LLM 호출·기사 생성·기사 승인은 포함하지 않는다.
