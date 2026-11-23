import json
import sqlite3
import unittest
from contextlib import closing
import test_review_api


class GenerationApiTest(unittest.TestCase):
    setUp=test_review_api.ReviewApiTest.setUp
    tearDown=test_review_api.ReviewApiTest.tearDown
    def test_generate_save_reload_and_approve(self):
        request={'question':'강도윤 청년 지원 예산은 얼마야?','candidate':'','include_withdrawn':False}
        response=self.client.post('/api/housing/generate',json=request)
        self.assertEqual(response.status_code,201)
        draft=response.json()
        self.assertIn('864억',draft['sentences'][0]['sentence'])
        self.assertEqual(draft['generation_mode'],'retrieval_extract')
        self.assertEqual(draft['validation']['ai_mode'],'not_used')
        loaded=self.client.get('/api/housing-review/drafts/'+draft['id']).json()
        self.assertEqual(loaded['question'],request['question'])
        self.assertEqual(loaded['sentences'],draft['sentences'])
        self.assertIn(draft['id'],[d['id'] for d in self.client.get('/api/housing-review/drafts').json()])
        decision=self.client.post('/api/housing-review/drafts/'+draft['id']+'/decision',json={'action':'approve','reviewer':'생성 기사 검토자'})
        self.assertEqual(decision.status_code,200)
        self.assertEqual(self.client.get('/api/housing-review/drafts/'+draft['id']).json()['status'],'approve')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertIn('864억',db.execute('SELECT body FROM ARTICLE WHERE article_id=?',(draft['id'],)).fetchone()[0])
            self.assertEqual(db.execute('SELECT count(*) FROM ARTICLE_EVIDENCE WHERE article_id=?',(draft['id'],)).fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM REVIEW WHERE article_id=?',(draft['id'],)).fetchone()[0],1)

    def test_no_evidence_does_not_save_a_fake_article(self):
        for question in ['교통 공약','강도윤 화성기지 공약']:
            response=self.client.post('/api/housing/generate',json={'question':question})
            self.assertEqual(response.status_code,422)
            self.assertIn('message',response.json()['detail'])
        self.assertEqual(self.client.get('/api/housing-review/drafts').json(),[])
        self.assertEqual(self.client.get('/api/housing-review/drafts/unknown').status_code,404)

    def test_database_tampering_blocks_generated_approval(self):
        draft=self.client.post('/api/housing/generate',json={'question':'강도윤 주거 예산'}).json()
        with closing(sqlite3.connect(self.db)) as db:
            payload=json.loads(db.execute('SELECT payload FROM drafts WHERE id=?',(draft['id'],)).fetchone()[0])
            payload['sentences'][0]['sentence']='예산 999억 원'
            db.execute('UPDATE drafts SET payload=? WHERE id=?',(json.dumps(payload),draft['id'])); db.commit()
        response=self.client.post('/api/housing-review/drafts/'+draft['id']+'/decision',json={'action':'approve','reviewer':'검토자'})
        self.assertEqual(response.status_code,409)

    def test_generated_rejection_preserves_reason(self):
        draft=self.client.post('/api/housing/generate',json={'question':'강도윤 주거 예산'}).json()
        url='/api/housing-review/drafts/'+draft['id']+'/decision'
        self.assertEqual(self.client.post(url,json={'action':'reject','reviewer':'검토자','reason':'문맥 보완 필요'}).status_code,200)
        self.assertEqual(self.client.get('/api/housing-review/drafts/'+draft['id']).json()['status'],'reject')
        rows=self.client.get('/api/housing-review/history').json()
        self.assertTrue(any(r['draft_id']==draft['id'] and r['reason']=='문맥 보완 필요' for r in rows))
