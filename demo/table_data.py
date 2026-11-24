"""CSV exports matching the team's 9-table ERD, plus district relations."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TABLES={
 'CANDIDATE':['candidate_id','name','party','status','data_kind','withdrawn_at','profile'],
 'SOURCE':['source_id','provider','title','data_kind','url','local_path','sha256','pdf_pages'],
 'SNAPSHOT':['event_id','sequence','simulated_at','counted_ballots','valid_ballots','invalid_ballots','count_progress_pct','source_id','mode'],
 'SNAPSHOT_VOTE':['row_id','event_id','candidate_id','votes','vote_share_pct'],
 'EVIDENCE':['chunk_id','source_id','candidate_id','document_id','pdf_page','text','citation','data_kind'],
 'ARTICLE':['article_id','snapshot_id','title','body','status','data_kind'],
 'ARTICLE_EVIDENCE':['id','article_id','sentence_no','sentence_id','sentence','chunk_id','row_id'],
 'FACT_CHECK':['check_id','article_id','verdict','reason','checked_at'],
 'REVIEW':['review_id','article_id','action','reviewer','reason','created_at'],
 'DISTRICT':['district_id','name'],
 'DISTRICT_VOTE':['event_id','district_id','candidate_id','votes']}

def export_tables(candidates,evidence,frames,article):
    from dataset_builder import DATA,write_csv,write_json
    rows={key:[] for key in TABLES}
    rows['CANDIDATE']=candidates
    rows['SOURCE']=[{'source_id':'DEMO-VOTES-01','provider':'BTS-Trio 교육용 창작','title':'가상 개표 시나리오','data_kind':'synthetic'}]
    for doc in evidence['documents']:
        path=ROOT/doc['local_document'] if doc.get('local_document') else None
        rows['SOURCE'].append({'source_id':doc['document_id'],
            'provider':'BTS-Trio 교육용 창작' if doc['data_kind']=='synthetic' else '기존 선관위 공약 PDF 수집본',
            'title':doc['title'],'data_kind':doc['data_kind'],'url':doc.get('stored_pdf_url'),
            'local_path':doc.get('local_document'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None,
            'pdf_pages':doc['pdf_pages_verified']})
    for src in evidence['candidate_status_sources']:
        rows['SOURCE'].append({'source_id':src['source_id'],'provider':'BTS-Trio 교육용 창작',
            'title':'백태오 사퇴 설정','data_kind':'synthetic','url':src['source_url']})
        rows['EVIDENCE'].append({'chunk_id':src['source_id']+':status','source_id':src['source_id'],
            'candidate_id':src['candidate_id'],'document_id':src['source_id'],'pdf_page':None,
            'text':src['text'],'citation':'[DEMO-STATUS-WD-06, 후보 상태 설정]','data_kind':'synthetic'})
    rows['EVIDENCE']+=evidence['chunks']
    for f in frames:
        rows['SNAPSHOT'].append({**f,'valid_ballots':f['valid_ballots_counted'],
            'invalid_ballots':f['invalid_ballots_counted'],'source_id':f['fact_source_id']})
        rows['SNAPSHOT_VOTE'] += [{**c,'event_id':f['event_id']} for c in f['candidates']]
        for name,district in f['districts'].items():
            if f['sequence']==0:
                rows['DISTRICT'].append({'district_id':district['district_id'],'name':name})
            rows['DISTRICT_VOTE'] += [{'event_id':f['event_id'],'district_id':district['district_id'],
                'candidate_id':c['candidate_id'],'votes':n} for c,n in zip(f['candidates'],district['votes'])]
    rows['ARTICLE']=[{'article_id':'DEMO-ARTICLE-01','snapshot_id':None,'title':'후보별 주거 공약 비교',
        'body':'\n'.join(a['sentence'] for a in article),'status':'pending','data_kind':'mixed_educational'}]
    for i,a in enumerate(article,1):
        rows['ARTICLE_EVIDENCE'].append({'id':f'DEMO-AE-{i:02}','article_id':'DEMO-ARTICLE-01',
            'sentence_no':i,'sentence_id':a['sentence_id'],'sentence':a['sentence'],'chunk_id':a['chunk_id'],'row_id':None})
        if a['candidate_status_source_id']:
            rows['ARTICLE_EVIDENCE'].append({'id':f'DEMO-AE-{i:02}-STATUS','article_id':'DEMO-ARTICLE-01',
                'sentence_no':i,'sentence_id':a['sentence_id'],'sentence':a['sentence'],
                'chunk_id':a['candidate_status_source_id']+':status','row_id':None})
    for table,fields in TABLES.items():
        write_csv(DATA/f'tables/{table}.csv',rows[table],fields)
    write_csv(DATA/'sources.csv',rows['SOURCE'],TABLES['SOURCE'])
    write_json(DATA/'tables/manifest.json',{'encoding':'utf-8-sig','null':'빈 필드=NULL',
        'row_counts':{k:len(v) for k,v in rows.items()},'import_order':list(TABLES),
        'note':'FACT_CHECK·REVIEW는 실제 실행 전 0행. 승인·검수 결과를 만들어 채우지 않음.'})

def initialize(connection):
    connection.executescript((ROOT/'schema.sql').read_text(encoding='utf-8'))
    if connection.execute('SELECT count(*) FROM CANDIDATE').fetchone()[0]:
        return
    for table,fields in TABLES.items():
        with (ROOT/f'data/tables/{table}.csv').open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream)
            if reader.fieldnames!=fields:
                raise ValueError(f'CSV header mismatch: {table}')
            values=[[None if row[f]=='' else row[f] for f in fields] for row in reader]
        if values:
            connection.executemany(f'INSERT INTO {table} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})',values)
    failures=connection.execute('PRAGMA foreign_key_check').fetchall()
    if failures:
        raise ValueError(f'CSV foreign key mismatch: {failures}')

if __name__=='__main__':
    with sqlite3.connect(':memory:') as db:
        initialize(db)
        print(json.dumps({t:db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in TABLES}))
