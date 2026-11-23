import copy
import csv
import json
import sqlite3
import unittest
from pathlib import Path
from dataset_builder import DATA, ROOT, generate, seed
from table_data import initialize, TABLES
from article_validation import validate

class DatasetTest(unittest.TestCase):
    def test_generated_frames_and_csv(self):
        frames=list(generate())
        packaged=[json.loads(line) for line in (DATA/'demo_snapshots.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(frames,packaged)
        with (DATA/'demo_candidates.csv').open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),155)
        for row in rows:
            actual=next(c for c in frames[int(row['sequence'])]['candidates'] if c['candidate_id']==row['candidate_id'])
            self.assertEqual(int(row['votes']),actual['votes'])

    def test_district_and_city_totals_every_frame(self):
        frames=list(generate())
        for f in frames:
            self.assertEqual(len(f['districts']),25)
            self.assertEqual(len(f['candidates']),5)
            self.assertEqual(sum(c['votes'] for c in f['candidates']),f['valid_ballots_counted'])
            self.assertEqual(f['valid_ballots_counted']+f['invalid_ballots_counted'],f['counted_ballots'])
            for i,c in enumerate(f['candidates']):
                self.assertEqual(sum(d['votes'][i] for d in f['districts'].values()),c['votes'])
                self.assertEqual(c['vote_share_pct'],round(c['votes']/f['valid_ballots_counted']*100,2) if f['valid_ballots_counted'] else None)
            self.assertEqual(sum(d['invalid_ballots'] for d in f['districts'].values()),f['invalid_ballots_counted'])
            self.assertNotIn('DEMO-C06',[c['candidate_id'] for c in f['candidates']])
        for a,b in zip(frames,frames[1:]):
            self.assertLess(a['counted_ballots'],b['counted_ballots'])
            for name in a['districts']:
                self.assertTrue(all(x<=y for x,y in zip(a['districts'][name]['votes'],b['districts'][name]['votes'])))
        self.assertEqual(frames[15]['leader_candidate_id'],'DEMO-C01')
        self.assertEqual(frames[-1]['winner_candidate_id'],'DEMO-C02')
        self.assertEqual(frames[-1]['counted_ballots'],1010000)

    def test_all_table_csvs_import_and_fk_constraints(self):
        with sqlite3.connect(':memory:') as db:
            initialize(db)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('SELECT count(*) FROM DISTRICT_VOTE').fetchone()[0],3875)
            self.assertEqual(db.execute('SELECT count(*) FROM REVIEW').fetchone()[0],0)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO SNAPSHOT_VOTE VALUES ('bad','unknown','DEMO-C01',1,0)")
            columns=[x[1] for x in db.execute('PRAGMA table_info(SNAPSHOT_VOTE)')]
            self.assertEqual(columns,TABLES['SNAPSHOT_VOTE'])

    def test_retained_real_content_and_synthetic_budget(self):
        current=json.loads((DATA/'rag/housing_evidence.json').read_text(encoding='utf-8'))
        old={c['chunk_id']:c for c in seed()['evidence']['chunks']}
        for c in current['chunks']:
            if c['data_kind']=='collected_real':
                for k in ['text','evidence_text','citation','pdf_page','stored_pdf_url','official_pdf_download_url']:
                    self.assertEqual(c[k],old[c['chunk_id']][k])
            else:
                self.assertEqual(c['total_support_budget_krw'],c['target_households']*c['monthly_support_krw']*c['duration_months'])
                self.assertIsNone(c['official_pdf_download_url'])
                self.assertIsNone(c['source_site_url'])

    def test_article_validation_blocks_tampering(self):
        original=json.loads((DATA/'rag/housing_article.json').read_text(encoding='utf-8'))
        self.assertTrue(validate({'sentences':original,'scenario':'normal'})['can_approve'])
        for key,value in [('sentence','지원금을 999억 원으로 바꾼 기사'),('article_candidate_id','DEMO-C02'),('pdf_page',99),('chunk_id',None)]:
            rows=copy.deepcopy(original); rows[0][key]=value
            self.assertFalse(validate({'sentences':rows,'scenario':'normal'})['can_approve'])
        self.assertFalse(validate({'sentences':original[:-1],'scenario':'normal'})['can_approve'])
        rows=copy.deepcopy(original); rows[-1]['candidate_status_source_id']=None
        self.assertFalse(validate({'sentences':rows,'scenario':'normal'})['can_approve'])
        self.assertFalse(validate({'sentences':original,'scenario':'ai_mismatch'})['can_approve'])

    def test_synthetic_pdf_actual_pages_and_text(self):
        try:
            from pypdf import PdfReader
        except ImportError:
            self.skipTest('pypdf is a build/test dependency')
        corpus=json.loads((DATA/'rag/housing_evidence.json').read_text(encoding='utf-8'))
        normalize=lambda s:''.join(s.split())
        for chunk in corpus['chunks']:
            if chunk['data_kind']!='synthetic': continue
            pdf=PdfReader(DATA/f"pdf/{chunk['document_id']}.pdf")
            self.assertEqual(len(pdf.pages),1)
            text=normalize(pdf.pages[0].extract_text())
            self.assertIn(normalize(chunk['text']),text)
            self.assertIn(chunk['candidate_id'],text)
            self.assertIn(chunk['document_id'],text)

if __name__=='__main__': unittest.main()
