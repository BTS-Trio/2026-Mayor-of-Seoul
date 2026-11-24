import copy
import unittest
from article_generation import generate_article, GenerationError
from article_validation import validate


class GenerationTest(unittest.TestCase):
    def test_question_changes_source_excerpt(self):
        budget=generate_article('강도윤의 청년 지원 예산은 얼마인가?')
        finance=generate_article('강도윤 주거 공약의 재원 조달 방법은?')
        self.assertIn('864억',budget['sentences'][0]['evidence_quote'])
        self.assertIn('70%',finance['sentences'][0]['evidence_quote'])
        self.assertNotEqual(budget['sentences'][0]['sentence'],finance['sentences'][0]['sentence'])
        self.assertEqual(budget['generation_mode'],'retrieval_extract')
        self.assertEqual(len(budget['sentences']),1)
        self.assertTrue(validate(budget)['can_approve'])
        self.assertEqual(validate(budget)['ai_mode'],'not_used')

    def test_comparison_withdrawn_and_real_sources(self):
        normal=generate_article('후보별 주거 공약을 비교해줘')
        self.assertEqual(len(normal['sentences']),5)
        all_rows=generate_article('후보별 주거 공약을 비교해줘',include_withdrawn=True)
        self.assertEqual(len(all_rows['sentences']),6)
        self.assertTrue(validate(all_rows)['can_approve'])
        withdrawn=next(r for r in all_rows['sentences'] if r['candidate_name']=='백태오')
        self.assertIn('(사퇴)',withdrawn['sentence'])
        self.assertIsNone(withdrawn['count_candidate_id'])
        real=generate_article('오세훈의 월세 지원 공약은?')
        self.assertEqual(real['sentences'][0]['document_id'],'SEOUL26-P5-02')
        self.assertEqual(real['sentences'][0]['pdf_page'],2)

    def test_missing_or_out_of_scope_evidence(self):
        for question in ['교통 공약 알려줘','주거와 교통 공약 비교','모든 분야의 공약','득표 기사 작성','강도윤 화성기지 공약','화성기지 우주왕복선']:
            with self.subTest(question=question),self.assertRaises(GenerationError): generate_article(question)
        with self.assertRaises(GenerationError): generate_article('백태오 주거 공약')
        with self.assertRaises(GenerationError): generate_article('강도윤 주거 공약',candidate='오세훈')

    def test_partial_coverage_blocks_approval_and_named_comparison_is_limited(self):
        partial=generate_article('전세')
        self.assertFalse(validate(partial)['can_approve'])
        self.assertTrue(any('누락' in x['message'] for x in validate(partial)['issues']))
        selected=generate_article('강도윤과 서지안 주거 공약 비교')
        self.assertEqual({r['candidate_name'] for r in selected['sentences']},{'강도윤','서지안'})
        self.assertTrue(validate(selected)['can_approve'])

    def test_approval_blocks_tampered_text_and_source(self):
        original=generate_article('강도윤 주거 예산')
        for field,value in [('sentence','예산 999억 원'),('evidence_quote','예산 999억 원'),('chunk_id','missing'),
                            ('article_candidate_id','DEMO-C02'),('pdf_page',99),('stored_pdf_url','https://example.com')]:
            changed=copy.deepcopy(original); changed['sentences'][0][field]=value
            self.assertFalse(validate(changed)['can_approve'],field)
        changed=copy.deepcopy(original); changed['source_fingerprint']='changed'
        self.assertFalse(validate(changed)['can_approve'])
        changed=copy.deepcopy(original); changed['sentences']=[]
        self.assertFalse(validate(changed)['can_approve'])


if __name__=='__main__': unittest.main()
