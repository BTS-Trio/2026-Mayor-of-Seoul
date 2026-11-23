import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import app

class ReviewApiTest(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.db=str(Path(self.work.name)/'test.sqlite3')
        self.env=patch.dict(os.environ,{'HOUSING_REVIEW_DB':self.db}); self.env.start()
        self.client=TestClient(app)
    def tearDown(self):
        self.client.close(); self.env.stop(); self.work.cleanup()

    def create(self,scenario='normal'):
        response=self.client.post('/api/housing-review/drafts',json={'scenario':scenario})
        self.assertEqual(response.status_code,201)
        return response.json()

    def test_api_sources_search_and_article(self):
        self.assertEqual(len(self.client.get('/api/candidates').json()['candidates']),6)
        data=self.client.get('/api/housing/search',params={'q':'후보 주거 비교'}).json()
        self.assertEqual(len(data['coverage']['returned_candidates']),5)
        data=self.client.get('/api/housing/search',params={'q':'후보 주거 비교','include_withdrawn':'true'}).json()
        self.assertEqual(len(data['coverage']['returned_candidates']),6)
        draft=self.client.get('/api/housing/draft').json()
        self.assertEqual(len(draft['sentences']),6)
        self.assertTrue(all(s['citations'] for s in draft['sentences']))
        pdf=self.client.get('/sources/DEMO-DOC-01.pdf')
        self.assertEqual(pdf.status_code,200); self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(self.client.get('/sources/unknown.pdf').status_code,404)
        self.assertEqual(self.client.get('/api/housing/search',params={'q':'x'}).status_code,400)

    def test_normal_approval_persists_in_erd_tables(self):
        draft=self.create(); self.assertTrue(draft['validation']['can_approve'])
        response=self.client.post(f"/api/housing-review/drafts/{draft['id']}/decision",json={'action':'approve','reviewer':'테스트 검토자'})
        self.assertEqual(response.status_code,200)
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('SELECT action FROM REVIEW').fetchone()[0],'approve')
            self.assertEqual(db.execute('SELECT status FROM ARTICLE WHERE article_id=?',(draft['id'],)).fetchone()[0],'approve')
        with TestClient(app) as reloaded:
            self.assertEqual(len(reloaded.get('/api/housing-review/history').json()),2)
        self.assertEqual(self.client.post(f"/api/housing-review/drafts/{draft['id']}/decision",json={'action':'approve','reviewer':'다른 검토자'}).status_code,409)

    def test_missing_source_blocks_approval_and_rejection_requires_reason(self):
        draft=self.create('missing_source'); self.assertFalse(draft['validation']['can_approve'])
        url=f"/api/housing-review/drafts/{draft['id']}/decision"
        self.assertEqual(self.client.post(url,json={'action':'approve','reviewer':'검토자'}).status_code,409)
        self.assertEqual(self.client.post(url,json={'action':'reject','reviewer':'검토자'}).status_code,422)
        self.assertEqual(self.client.post(url,json={'action':'reject','reviewer':'검토자','reason':'근거 누락'}).status_code,200)

if __name__=='__main__': unittest.main()
