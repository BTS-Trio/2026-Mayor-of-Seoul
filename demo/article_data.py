"""Expose a stored, source-linked article; this is not live LLM generation."""
import json
from pathlib import Path
from housing_search import get_housing_search

ROOT=Path(__file__).resolve().parent

def load_article():
    return json.loads((ROOT/'data/rag/housing_article.json').read_text(encoding='utf-8'))

def draft_response():
    index=get_housing_search()
    chunks={c['chunk_id']:c for c in index.chunks}
    sources={s['source_id']:s for s in index.dataset['candidate_status_sources']}
    sentences=[]
    for row in load_article():
        c=chunks[row['chunk_id']]
        citations=[{'label':c['citation'],'url':c['stored_pdf_url']}]
        if row.get('candidate_status_source_id'):
            source=sources[row['candidate_status_source_id']]
            citations.append({'label':'사퇴 상태 설정 · '+source['source_id'],'url':source['source_url']})
        sentences.append({'text':row['sentence'].split(' [')[0],'citations':citations,
            'sentence_id':row['sentence_id'],'candidate_id':row['article_candidate_id']})
    return {'title':'후보별 주거 공약 비교 · 검토 초안','sentences':sentences,
            'label':index.dataset['dataset_name'],'generation_mode':'stored_draft'}
