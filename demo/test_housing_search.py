import copy
import json
import unittest
from housing_search import HousingSearch, DATA_PATH

class HousingSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA_PATH.read_text(encoding='utf-8'))
        cls.index=HousingSearch(cls.data)

    def test_bm25_all_running_candidates(self):
        result=self.index.search('후보 주거 공약 비교')
        self.assertEqual(set(result['coverage']['returned_candidates']),{'강도윤','오세훈','서지안','한서준','윤채린'})
        self.assertEqual(result['retrieval_method'],'lexical_bm25_korean_bigrams')

    def test_withdrawn_opt_in(self):
        self.assertEqual(self.index.search('백태오 주거')['results'],[])
        result=self.index.search('후보 주거 비교',include_withdrawn=True)
        self.assertEqual(len(result['coverage']['returned_candidates']),6)
        self.assertTrue(self.index.search('주거',candidate='백태오',include_withdrawn=True)['results'][0]['candidate_withdrawn'])

    def test_specific_real_source(self):
        result=self.index.search('월세 지원',candidate='오세훈')
        self.assertEqual(result['results'][0]['document_id'],'SEOUL26-P5-02')
        self.assertEqual(result['results'][0]['pdf_page'],2)

    def test_unknown_topic_no_invention(self):
        self.assertEqual(self.index.search('화성기지 우주왕복선')['results'],[])

    def test_validation_and_bad_inputs(self):
        for q in ['','x','x'*501]:
            with self.assertRaises(ValueError): self.index.search(q)
        for limit in [0,31,'10']:
            with self.assertRaises(ValueError): self.index.search('주거',limit=limit)
        with self.assertRaises(ValueError): self.index.search('주거',candidate='정원오')
        for key,value in [('pdf_page',2),('stored_pdf_url','javascript:alert(1)'),('official_pdf_download_url','https://policy.nec.go.kr/')]:
            data=copy.deepcopy(self.data); data['chunks'][0][key]=value
            with self.assertRaises(ValueError): HousingSearch(data)

if __name__=='__main__': unittest.main()
