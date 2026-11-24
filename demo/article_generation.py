"""Question-driven retrieval/extractive drafting. No model call or fixed article reuse."""
import hashlib
import json
import re
from datetime import datetime, timezone
from housing_search import get_housing_search, tokens, HOUSING_TERMS
from evidence_contract import valid_evidence


class GenerationError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code=code


def source_fingerprint(chunks):
    values=[{k:c.get(k) for k in ('chunk_id','candidate_id','candidate','text','citation','pdf_page',
            'stored_pdf_url','candidate_withdrawn','data_kind')} for c in chunks]
    return hashlib.sha256(json.dumps(values,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()


def retrieve(question, candidate='', include_withdrawn=False):
    question=question.strip()
    if not 2<=len(question)<=500:
        raise GenerationError('invalid_question','기사 질문을 2~500자로 입력해 주세요.')
    other_scope=question.replace('주거복지','').replace('주거환경','')
    if re.search(r'교통|지하철|버스|일자리|고용|병원|의료|교육|탄소|치안|외교|복지|돌봄|보육|환경|산업',other_scope):
        raise GenerationError('unsupported_scope','현재 기사 생성용 근거는 주거 공약입니다. 다른 분야는 근거를 준비한 뒤 생성할 수 있습니다.')
    if any(w in question for w in ('득표','지지율','개표','당선')):
        raise GenerationError('unsupported_scope','이 기능은 공약 기사 초안용입니다. 개표 수치는 개표 데스크에서 확인해 주세요.')
    housing=any(w in question for w in HOUSING_TERMS+('청년','임차료','예산','재원','지원금','기간','대상'))
    if not housing and re.search(r'(모든|전체|전부).{0,8}공약',question):
        raise GenerationError('incomplete_corpus','모든 분야의 공약은 아직 준비되지 않았습니다. 주거 공약으로 질문 범위를 좁혀 주세요.')
    index=get_housing_search()
    named={name for name in index.names if name in question}
    if candidate and named and candidate not in named:
        raise GenerationError('conflicting_candidate','질문에 적은 후보와 선택한 후보가 다릅니다.')
    withdrawn={d['candidate'] for d in index.documents.values() if d.get('candidate_withdrawn')}
    if named and named<=withdrawn and not include_withdrawn:
        raise GenerationError('withdrawn_excluded','사퇴 후보를 질문하려면 사퇴 후보 포함을 선택해 주세요.')
    query=question
    for name in index.names: query=query.replace(name,'')
    query=re.sub(r'공약[은는이가을를의에]*|후보[별은는이가을를의에]*|알려줘|알려주세요|뭐야|무엇인가요',' ',query).strip()
    if len(query)<2: query='주거'
    if not named and not candidate and any(w in question for w in ('후보','비교','차이')) and housing:
        query+=' 주거 후보 비교'
    result=index.search(query,candidate=candidate,limit=30,include_withdrawn=include_withdrawn)
    if named and not candidate:
        requested=named if include_withdrawn else named-withdrawn
        result['results']=[c for c in result['results'] if c['candidate'] in requested]
        returned={c['candidate'] for c in result['results']}
        result['coverage'].update(requested_candidates=sorted(requested),returned_candidates=sorted(returned),
            not_returned_candidates=sorted(requested-returned),all_requested_candidates_returned=requested<=returned)
    if not result['results']:
        raise GenerationError('no_evidence','질문에 맞는 근거를 찾지 못했습니다. 기사나 수치를 임의로 만들지 않습니다.')
    # One ranked passage per candidate; preserve the requested candidates in coverage.
    selected=[]; seen=set()
    for c in result['results']:
        if c['candidate_id'] not in seen:
            selected.append(c); seen.add(c['candidate_id'])
    return selected,result['coverage']


def choose_quote(chunk, question):
    source=chunk['text']
    counts=tokens(question)
    focus=[]
    if re.search(r'예산|총액|총.*지원금|총.*금액',question): focus.append(r'예산|총\s*\d+억')
    if re.search(r'재원|조달|재정',question): focus.append(r'시비|기금|조달|재정')
    if re.search(r'대상|나이|소득|몇\s*세',question): focus.append(r'대상|소득|만\s*\d+')
    if re.search(r'기간|언제|몇\s*년|몇\s*개월',question): focus.append(r'개월|2027|2030|이행기간|년까지')
    if re.search(r'월.*얼마|월.*금액|지원액',question): focus.append(r'월\s*\d+만')
    options=[]
    for match in re.finditer(r'[^\r\n]+',source):
        line=match.group().strip()
        if not line: continue
        # Retain complete source sentences; never truncate a number or qualifying clause.
        parts=re.split(r'(?<=다\.)\s+',line)
        for part in parts:
            if not part or part not in source or len(part)>1000: continue
            term_counts=tokens(part)
            score=sum(min(counts[t],term_counts[t]) for t in counts)
            score+=30*sum(bool(re.search(pattern,part)) for pattern in focus)
            options.append((score,len(part),part))
    if not options:
        raise GenerationError('source_too_long','근거를 안전하게 발췌할 수 없습니다. 원문 검색 조각을 먼저 나눠 주세요.')
    options.sort(key=lambda item:(-item[0],-min(item[1],200),item[2]))
    return options[0][2]


def sentence_text(chunk, quote):
    name=chunk['candidate']+('(사퇴)' if chunk['candidate_withdrawn'] else '')
    return f'{name}의 공약 자료에는 “{quote}”라는 내용이 담겼다. {chunk["citation"]}'


def generate_article(question, candidate='', include_withdrawn=False):
    chunks,coverage=retrieve(question,candidate,include_withdrawn)
    states=get_housing_search().dataset['candidate_status_sources']
    rows=[]
    for i,c in enumerate(chunks,1):
        quote=choose_quote(c,question)
        state=next((s['source_id'] for s in states if s['candidate_id']==c['candidate_id']),None)
        rows.append({'sentence_id':f'GEN-S{i:02}','article_candidate_id':c['candidate_id'],
            'count_candidate_id':None if c['candidate_withdrawn'] else c['candidate_id'],
            'candidate_name':c['candidate'],'sentence':sentence_text(c,quote),'evidence_quote':quote,
            'chunk_id':c['chunk_id'],'document_id':c['document_id'],'pdf_page':c['pdf_page'],
            'citation':c['citation'],'stored_pdf_url':c['stored_pdf_url'],'data_kind':c['data_kind'],
            'candidate_status_source_id':state if c['candidate_withdrawn'] else None})
    return {'scenario':'generated','generation_mode':'retrieval_extract',
        'title':(candidate+' ' if candidate else '')+'주거 공약 근거 정리',
        'question':question.strip(),'candidate':candidate,'include_withdrawn':include_withdrawn,
        'created_at':datetime.now(timezone.utc).isoformat(),'sentences':rows,'coverage':coverage,
        'source_fingerprint':source_fingerprint(chunks),'label':get_housing_search().dataset['dataset_name'],
        'generation_notice':'질문에 따라 근거를 검색·발췌해 작성한 새 초안입니다. 외부 AI 문장 재작성은 사용하지 않았습니다.',
        'review_notice':'공약 이행·실현 가능성 판단은 포함하지 않습니다. 문맥·누락·질문에 대한 충분성은 사람이 원문과 대조해야 합니다.'}


def validate_generated(payload):
    issues=[]
    def issue(sid,message): issues.append({'sentence_id':sid,'message':message})
    try:
        selected,coverage=retrieve(payload.get('question',''),payload.get('candidate',''),payload.get('include_withdrawn',False))
        if payload.get('source_fingerprint')!=source_fingerprint(selected):
            issue(None,'생성 당시와 현재의 검색 근거가 다릅니다. 다시 생성해 주세요.')
        if not coverage['all_requested_candidates_returned']:
            issue(None,'요청한 후보 중 근거가 누락됐습니다. 후보나 질문 범위를 좁혀 다시 생성해 주세요.')
    except ValueError as error:
        selected=[]; issue(None,str(error))
    rows=payload.get('sentences')
    if not isinstance(rows,list) or len(rows)!=len(selected) or not rows:
        issue(None,'생성 기사 문장 수 또는 근거 범위 불일치'); rows=[]
    docs=get_housing_search().documents
    states={s['source_id']:s for s in get_housing_search().dataset['candidate_status_sources']}
    for i,(row,c) in enumerate(zip(rows,selected),1):
        sid=f'GEN-S{i:02}'
        if not valid_evidence(c,docs.get(c['document_id'])):
            issue(sid,'PDF 출처·쪽수 또는 후보 연결 불일치'); continue
        if (row.get('sentence_id')!=sid or row.get('chunk_id')!=c['chunk_id']
            or row.get('article_candidate_id')!=c['candidate_id'] or row.get('candidate_name')!=c['candidate']
            or any(row.get(k)!=c.get(k) for k in ('document_id','pdf_page','stored_pdf_url','citation','data_kind'))):
            issue(sid,'생성 기사의 후보 ID·근거·인용 불일치')
        quote=row.get('evidence_quote')
        if not isinstance(quote,str) or not quote.strip() or quote not in c['text']:
            issue(sid,'인용 문구가 원문에 없거나 변경됐습니다.')
        elif row.get('sentence')!=sentence_text(c,quote):
            issue(sid,'생성 기사 본문·수치가 원문 발췌와 다릅니다.')
        expected_count=None if c['candidate_withdrawn'] else c['candidate_id']
        if row.get('count_candidate_id')!=expected_count:
            issue(sid,'출마·사퇴 후보의 개표 연결 불일치')
        if c['candidate_withdrawn']:
            state=states.get(row.get('candidate_status_source_id'),{})
            if state.get('candidate_id')!=c['candidate_id'] or '(사퇴)' not in row.get('sentence',''):
                issue(sid,'사퇴 상태 근거 또는 기사 표시 누락')
    return {'can_approve':not issues,'rules_pass':not issues,'ai_pass':None,'ai_mode':'not_used',
            'issues':issues,'scope':'원문 발췌·후보·인용·검색 범위의 일치 검사. 기사 충분성·문맥·실제 사실성은 사람 검토 필요.'}
