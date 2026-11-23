"""Pure validation of article/source links; no network or AI calls."""
import json
from pathlib import Path
from evidence_contract import valid_evidence

DATA=Path(__file__).resolve().parent/'data'

def validate(payload):
    expected=json.loads((DATA/'rag/housing_article.json').read_text(encoding='utf-8'))
    evidence=json.loads((DATA/'rag/housing_evidence.json').read_text(encoding='utf-8'))
    chunks={c['chunk_id']:c for c in evidence['chunks']}
    docs={d['document_id']:d for d in evidence['documents']}
    states={s['source_id']:s for s in evidence['candidate_status_sources']}
    problems=[]
    rows=payload.get('sentences')
    if not isinstance(rows,list) or len(rows)!=len(expected):
        problems.append({'sentence_id':None,'message':'기사 문장 수 또는 형식 불일치'})
        rows=[]
    for row,original in zip(rows,expected):
        sid=original['sentence_id']
        c=chunks.get(row.get('chunk_id'))
        if not c or not valid_evidence(c,docs.get(c['document_id'])):
            problems.append({'sentence_id':sid,'message':'필수 출처 또는 근거 행 ID 누락·불일치'})
            continue
        if (any(row.get(k)!=c.get(k) for k in ('document_id','pdf_page','stored_pdf_url','citation','data_kind'))
            or row.get('candidate_name')!=c['candidate']
            or row.get('article_candidate_id')!=c['candidate_id']
            or any(row.get(k)!=original.get(k) for k in ('sentence_id','sentence','chunk_id','count_candidate_id'))):
            problems.append({'sentence_id':sid,'message':'기사 수치·후보 ID·본문 또는 출처가 기준 자료와 불일치'})
        if c['candidate_withdrawn']:
            state=states.get(row.get('candidate_status_source_id'),{})
            if (state.get('candidate_id')!=c['candidate_id'] or not state.get('source_url')
                or row.get('count_candidate_id') is not None or '(사퇴)' not in row.get('sentence','')):
                problems.append({'sentence_id':sid,'message':'사퇴 상태 근거·기사 표시·집계 제외 불일치'})
    rules_pass=not problems
    ai_pass=payload.get('scenario')=='normal'
    if ai_pass!=rules_pass:
        problems.append({'sentence_id':None,'message':'규칙 검증과 AI 시연 판정 불일치'})
    return {'can_approve':not problems,'rules_pass':rules_pass,'ai_pass':ai_pass,'ai_mode':'fixture','issues':problems}
