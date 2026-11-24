"""Build one consistent educational dataset for the team demo (Python 3.10+)."""
import copy
import csv
import hashlib
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
STEPS = 30
LABEL = '교육용 가상 선거 · 오세훈 공약 일부는 실제 수집 자료 · 모든 개표 수치는 가상'
DISTRICTS = ['종로구','중구','용산구','성동구','광진구','동대문구','중랑구','성북구','강북구','도봉구','노원구','은평구','서대문구','마포구','양천구','강서구','구로구','금천구','영등포구','동작구','관악구','서초구','강남구','송파구','강동구']

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fields or list(rows[0]), extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def seed():
    return json.loads((DATA/'source_build/seed.json').read_text(encoding='utf-8'))

def corpus():
    evidence = copy.deepcopy(seed()['evidence'])
    evidence.update(schema_version='2.0',prepared_date_kst='2026-11-23',dataset_name=LABEL,
        question='각 후보의 주거 공약을 비교해 주세요.',source_spreadsheet=None,mode='mixed_educational',
        candidate_status_sources=[{'source_id':'DEMO-STATUS-WD-06','candidate':'백태오',
        'candidate_id':'DEMO-C06','data_kind':'synthetic','source_url':'/api/candidates',
        'withdrawn_at':'2026-06-01T12:00:00+09:00','text':'백태오: 2026-06-01 12:00 사퇴(교육용 설정).'}])
    for doc in evidence['documents']:
        doc['source_id'] = doc['document_id']
        if doc['data_kind']=='synthetic':
            doc.update(local_document=f"data/pdf/{doc['document_id']}.pdf",pdf_pages_verified=1,
                stored_pdf_url=f"/sources/{doc['document_id']}.pdf",document_type='교육용 가상 공약 PDF')
        else:
            doc.update(pdf_pages_verified=5,verification_note_current='2026-11-23 Drive PDF 총 5쪽 및 인용 1·2·4쪽 본문 대조. 정책 이행 검증 아님.')
    docs = {d['document_id']:d for d in evidence['documents']}
    for chunk in evidence['chunks']:
        chunk['source_id'] = chunk['document_id']
        if chunk['data_kind']=='synthetic':
            chunk.update(pdf_page=1,citation=f"[{chunk['document_id']}, PDF 1쪽]",
                stored_pdf_url=docs[chunk['document_id']]['stored_pdf_url'],official_pdf_download_url=None,
                document_registry_url=None,page_number_basis='생성 PDF 첫 페이지=1쪽',
                verification_status='가상 PDF 원문·수치·기간·예산 내부 대조')
        else:
            chunk['verification_note_current']='2026-11-23 Drive PDF 인용 1·2·4쪽 본문 재대조.'
    return evidence

def allocate(total, weights):
    denominator = sum(weights)
    counts = [total*w//denominator for w in weights]
    order = sorted(range(len(weights)),key=lambda i:(-(total*weights[i]%denominator),i))
    for i in order[:total-sum(counts)]:
        counts[i] += 1
    return counts

def generate():
    candidates = [c for c in seed()['candidates'] if not c['candidate_withdrawn']]
    weights = [[9+((d*(j+3)+j*7)%19) for d in range(25)] for j in range(5)]
    start = datetime(2026,6,3,20,tzinfo=timezone(timedelta(hours=9)))
    # Each candidate's fixed final district allocation is scaled monotonically.
    finals = [allocate(c['final_votes'],w) for c,w in zip(candidates,weights)]
    for step in range(31):
        p = step/30
        district_votes = [[int(n*(p+.22*p*(1-p) if j==0 else p)) for n in values]
                          for j,values in enumerate(finals)]
        votes = [sum(values) for values in district_votes]
        invalid = 10000*step//30
        invalid_district = allocate(invalid,[1]*25)
        valid = sum(votes)
        eid = f'DEMO-SNAPSHOT-{step:03}'
        rows = [{'candidate_id':c['candidate_id'],'name':c['name'],'party':c['party'],
            'row_id':eid+'-'+c['candidate_id'],'votes':n,
            'vote_share_pct':round(n/valid*100,2) if valid else None,'votes_are_synthetic':True}
            for c,n in zip(candidates,votes)]
        districts = {name:{'district_id':f'SEOUL-D{d+1:02}','counted_units':step,'total_units':30,
            'votes':[district_votes[j][d] for j in range(5)],'invalid_ballots':invalid_district[d]}
            for d,name in enumerate(DISTRICTS)}
        yield {'event':'snapshot','event_id':eid,'sequence':step,'mode':'synthetic','label':LABEL,
            'timestamp_is_simulated':True,'simulated_at':(start+timedelta(minutes=step*15)).isoformat(),
            'scope':'서울시 전체(가상)','region':'서울특별시','race':'교육용 가상 시장선거',
            'count_unit':'가상 자치구별 재생 단계','counted_units':step*25,'total_units':750,
            'registered_voters':2000000,'total_ballots':1010000,'counted_ballots':valid+invalid,
            'valid_ballots_counted':valid,'invalid_ballots_counted':invalid,
            'count_progress_pct':round((valid+invalid)/1010000*100,2),'final_turnout_pct':50.5,
            'fact_source_id':'DEMO-VOTES-01','schema_source_id':None,'schema_version':'2.0','verified_source_ids':[],
            'complete':step==30,'candidates':rows,'districts':districts,
            'withdrawn_candidates':[c for c in seed()['candidates'] if c['candidate_withdrawn']],
            'leader_candidate_id':max(rows,key=lambda r:r['votes'])['candidate_id'] if valid else None,
            'winner_candidate_id':'DEMO-C02' if step==30 else None}

def article(evidence):
    rows=[]
    for candidate in seed()['candidates']:
        choices=[c for c in evidence['chunks'] if c['candidate_id']==candidate['candidate_id']]
        chunk=next((c for c in choices if c['pdf_page']==2),choices[0])
        if candidate['data_kind']=='collected_real':
            sentence='오세훈은 2031년까지 공공주택 약 13만 호를 공급하고, 주거비 금융지원과 월세 지원을 확대하겠다고 밝혔다.'
        else:
            sentence=(candidate['name']+('(사퇴)' if candidate['candidate_withdrawn'] else '')+
                f"은 2027~2030년 무주택 청년 {chunk['target_households']:,}가구에 월 15만 원을 48개월 지원하고, 지원금 총 {chunk['total_support_budget_krw']//100000000}억 원을 투입하겠다는 공약을 제시했다.")
        rows.append({'sentence_id':f'DEMO-HOUSING-S{len(rows)+1:02}','article_id':'DEMO-ARTICLE-01',
            'article_candidate_id':candidate['candidate_id'],
            'count_candidate_id':None if candidate['candidate_withdrawn'] else candidate['candidate_id'],
            'candidate_name':candidate['name'],'sentence':sentence+' '+chunk['citation'],
            'chunk_id':chunk['chunk_id'],'document_id':chunk['document_id'],'pdf_page':chunk['pdf_page'],
            'citation':chunk['citation'],'evidence_excerpt':chunk['evidence_text'],'source_chunk_text':chunk['text'],
            'stored_pdf_url':chunk['stored_pdf_url'],'data_kind':chunk['data_kind'],
            'candidate_status_source_id':'DEMO-STATUS-WD-06' if candidate['candidate_withdrawn'] else None,
            'editor_approval':'미승인'})
    return rows

def make_pdfs(evidence):
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    font=Path('C:/Windows/Fonts/malgun.ttf')
    if font.exists():
        pdfmetrics.registerFont(TTFont('Korean',str(font))); fontname='Korean'
    else:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium')); fontname='HYSMyeongJo-Medium'
    body=ParagraphStyle('body',fontName=fontname,fontSize=11,leading=19,wordWrap='CJK')
    title=ParagraphStyle('title',parent=body,fontSize=20,leading=28,spaceAfter=20)
    for chunk in evidence['chunks']:
        if chunk['data_kind']!='synthetic': continue
        path=DATA/f"pdf/{chunk['document_id']}.pdf"; path.parent.mkdir(parents=True,exist_ok=True)
        story=[Paragraph(html.escape(chunk['candidate']+' 주거 공약서'),title),
            Paragraph('자료 ID: '+chunk['document_id']+' / 후보 ID: '+chunk['candidate_id'],body),Spacer(1,18),
            Paragraph(html.escape(chunk['text']),body),Spacer(1,25),
            Paragraph('교육용 가상 공약 원문입니다. 실제 인물의 공약·공식 선거 문서가 아니며 동명이인과 무관합니다.',body)]
        def footer(canvas,doc):
            canvas.setFont(fontname,9); canvas.drawString(45,30,chunk['document_id']+' / PDF 1쪽 / 교육용 가상자료')
        SimpleDocTemplate(str(path),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=50,bottomMargin=55,
            title=chunk['candidate']+' 주거 공약서',author='BTS-Trio 교육용',invariant=1).build(story,onFirstPage=footer)

def main():
    source = seed()
    candidates=source['candidates']; evidence=corpus(); frames=list(generate()); article_rows=article(evidence)
    write_json(DATA/'candidates.json',{'label':LABEL,'candidates':candidates,
        'portraits':source['portraits'],'portrait_note':source['portrait_note']})
    write_json(DATA/'rag/housing_evidence.json',evidence); write_json(DATA/'rag/housing_article.json',article_rows)
    write_json(DATA/'seoul_final_totals.json',{'mode':'synthetic','label':LABEL,'election_date':'2026-06-03',
        'region':'서울특별시','race':'가상 시장선거','registered_voters':2000000,'total_ballots':1010000,
        'valid_ballots':1000000,'invalid_ballots':10000,'district_count':25,'count_reporting_units':750,
        'winner_candidate_id':'DEMO-C02','verified_source_ids':[],'official_dataset_id':None})
    (DATA/'demo_snapshots.jsonl').write_text(''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in frames),encoding='utf-8')
    write_csv(DATA/'demo_candidates.csv',[{'event_id':f['event_id'],'sequence':f['sequence'],'mode':f['mode'],
        'fact_source_id':f['fact_source_id'],**c} for f in frames for c in f['candidates']])
    write_csv(DATA/'seoul_final_candidates.csv',[{'candidate_id':c['candidate_id'],'candidate':c['name'],
        'party':c['party'],'votes':c['final_votes'],'reported_share_pct':c['final_votes']/10000,'mode':'synthetic'}
        for c in candidates if not c['candidate_withdrawn']])
    write_csv(DATA/'seoul_final_by_district.csv',[{'district':name,'district_id':d['district_id'],
        'valid_ballots':sum(d['votes']),'invalid_ballots':d['invalid_ballots'],
        **{c['candidate_id']:n for c,n in zip(candidates[:5],d['votes'])},'mode':'synthetic'} for name,d in frames[-1]['districts'].items()])
    write_csv(DATA/'demo_reporting_schedule.csv',[{'event_id':f['event_id'],'sequence':f['sequence'],
        'simulated_at':f['simulated_at'],'mode':'synthetic'} for f in frames])
    write_csv(DATA/'candidate_id_mapping.csv',[{'old_count_id':f'SEOUL-{i+1:02}' if i<5 else '',
        'old_article_id':f'SEOUL-{i+1:02}' if i<5 else 'SEOUL-WD-06','candidate_id':c['candidate_id'],
        'name':c['name'],'withdrawn':int(c['candidate_withdrawn'])} for i,c in enumerate(candidates)])
    write_json(DATA/'rag/housing_search_example.json',{'question':evidence['question'],'notice':'검색 결과는 BM25 검색 테스트로 재생성합니다.'})
    (ROOT/'docs/housing-article-draft-20261123.md').write_text('# 후보별 주거 공약 비교 · 검토 초안\n\n'+
        '\n\n'.join(r['sentence'] for r in article_rows)+'\n\n---\n'+LABEL+'\nAI 작성 초안 · 사람 최종 승인 전\n',encoding='utf-8')
    make_pdfs(evidence)
    from housing_search import get_housing_search
    get_housing_search.cache_clear()
    write_json(DATA/'rag/housing_search_example.json',
        get_housing_search().search(evidence['question'], include_withdrawn=True))
    from table_data import export_tables
    export_tables(candidates,evidence,frames,article_rows)
    write_json(DATA/'dummy_manifest.json',{'label':LABEL,'candidates':6,'running':5,'withdrawn':1,'districts':25,
        'snapshots':31,'evidence':len(evidence['chunks']),'generated_from':'data/source_build/seed.json',
        'sha256':{str(p.relative_to(DATA)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in DATA.rglob('*') if p.is_file() and p.name!='dummy_manifest.json'}})
    print('Generated 6 candidates, 25 districts, 31 snapshots, PDFs and table CSVs.')

if __name__=='__main__': main()
