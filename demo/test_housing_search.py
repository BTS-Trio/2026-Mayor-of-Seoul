"""Checks for searchable citations, coverage, and API failure behavior."""
import ast
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import app
from housing_search import DATA_PATH, HousingSearch

ROOT = Path(__file__).resolve().parent


class HousingSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        cls.index = HousingSearch(cls.dataset)
        cls.client = TestClient(app)

    def test_question_covers_every_ready_candidate_and_reports_pending(self):
        result = self.index.search(self.dataset["question"])
        self.assertEqual(set(result["coverage"]["returned_candidates"]),
                         {"정원오", "오세훈", "김정철", "유지혜", "이강산", "권영국"})
        self.assertEqual(result["coverage"]["not_returned_candidates"], [])
        self.assertEqual(result["coverage"]["pending_evidence"], [])
        self.assertTrue(result["candidate_balancing"])
        self.assertTrue(result["coverage"]["all_requested_candidates_returned"])

    def test_monthly_rent_finds_the_actual_support_page(self):
        result = self.index.search("월세 지원", limit=3)
        self.assertEqual(result["results"][0]["document_id"], "SEOUL26-P5-02")
        self.assertEqual(result["results"][0]["pdf_page"], 2)

    def test_single_person_housing_finds_the_relevant_page(self):
        result = self.index.search("김정철 역세권 소형 주택", limit=2)
        self.assertEqual(result["results"][0]["candidate"], "김정철")
        self.assertEqual(result["results"][0]["pdf_page"], 5)

    def test_candidate_filter_preserves_withdrawal_status(self):
        result = self.index.search("주거 지원", candidate="이강산")
        self.assertTrue(result["results"])
        self.assertTrue(all(r["candidate"] == "이강산" for r in result["results"]))
        self.assertTrue(all(r["candidate_withdrawn"] for r in result["results"]))

    def test_verified_candidate_uses_its_own_page_and_pending_is_excluded(self):
        result = self.index.search("정원오 주택 공급")
        self.assertTrue(result["results"])
        self.assertTrue(all(r["candidate"] == "정원오" for r in result["results"]))
        self.assertEqual(result["results"][0]["citation"], "[SEOUL26-PB-01, PDF 7쪽]")
        dataset = copy.deepcopy(self.dataset)
        verified = dataset["chunks"].pop(0)
        dataset["pending_chunks"].append({
            "candidate": verified["candidate"], "document_id": verified["document_id"],
            "rag_eligible": False, "pdf_url": verified["stored_pdf_url"],
            "exclusion_reason": "test: page pending",
        })
        pending_result = HousingSearch(dataset).search("정원오 주택 공급")
        self.assertEqual(pending_result["results"], [])
        self.assertEqual(pending_result["coverage"]["pending_evidence"][0]["document_id"],
                         "SEOUL26-PB-01")

    def test_unrelated_question_does_not_invent_evidence(self):
        self.assertEqual(self.index.search("바이올린 악보")["results"], [])

    def test_results_keep_citations_and_do_not_mutate_the_source(self):
        before = copy.deepcopy(self.index.dataset)
        for result in self.index.search(self.dataset["question"], limit=30)["results"]:
            original = next(c for c in self.dataset["chunks"]
                            if c["chunk_id"] == result["chunk_id"])
            for field in ("document_id", "pdf_page", "citation", "text",
                          "evidence_text", "stored_pdf_url", "official_pdf_download_url"):
                self.assertEqual(result[field], original[field])
            self.assertGreater(result["score"], 0)
        self.assertEqual(self.index.dataset, before)

    def test_limits_and_invalid_candidate_are_rejected(self):
        for query, candidate, limit in [("", "", 10), ("주거", "없는후보", 10),
                                        ("주거", "", 0), ("주거", "", 31)]:
            with self.subTest(query=query, candidate=candidate, limit=limit):
                with self.assertRaises(ValueError):
                    self.index.search(query, candidate, limit)
        self.assertLessEqual(len(self.index.search("주거", limit=1)["results"]), 1)

    def test_bad_citation_blocks_index_loading(self):
        dataset = copy.deepcopy(self.dataset)
        dataset["chunks"][0]["pdf_page"] = 99
        with self.assertRaises(ValueError):
            HousingSearch(dataset)

    def test_duplicate_chunk_and_non_https_source_are_rejected(self):
        for mutation in ("duplicate", "url"):
            dataset = copy.deepcopy(self.dataset)
            if mutation == "duplicate":
                dataset["chunks"].append(copy.deepcopy(dataset["chunks"][0]))
            else:
                dataset["chunks"][0]["stored_pdf_url"] = "javascript:alert(1)"
            with self.assertRaises(ValueError):
                HousingSearch(dataset)

    def test_api_returns_search_evidence(self):
        response = self.client.get("/api/housing/search", params={"q": "월세 지원"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["citation"],
                         "[SEOUL26-P5-02, PDF 2쪽]")
        self.assertEqual(self.client.get("/api/housing/search").status_code, 400)
        self.assertEqual(self.client.get("/api/housing/search",
                                        params={"q": "주거", "limit": 0}).status_code, 400)

    def test_status_and_page_are_served(self):
        response = self.client.get("/api/housing/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ready_chunks"], 17)
        self.assertEqual(response.json()["pending_chunks"], 0)
        self.assertEqual(len(response.json()["candidate_options"]), 6)
        page = self.client.get("/housing-search")
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="question"', page.text)
        self.assertIn("/api/housing/search?", page.text)
        self.assertIn('/housing-search', self.client.get("/").text)

    def test_missing_or_invalid_data_is_an_error_not_empty_success(self):
        with patch("app.get_housing_search", side_effect=ValueError("bad data")):
            response = self.client.get("/api/housing/status")
        self.assertEqual(response.status_code, 503)

    def test_existing_api_is_preserved(self):
        self.assertEqual(self.client.get("/health").json()["role"], "broadcast")
        self.assertEqual(self.client.get("/api/final").status_code, 200)

    def test_new_python_source_has_python_310_syntax(self):
        for name in ("housing_search.py", "app.py", "test_housing_search.py"):
            ast.parse((ROOT / name).read_text(encoding="utf-8"),
                      filename=name, feature_version=(3, 10))


class HousingAPIUnitTest(unittest.TestCase):
    """Call endpoint handlers directly, without a network transport."""

    def test_handler_returns_unchanged_citation(self):
        from app import search_housing_evidence
        result = search_housing_evidence(q="월세 지원", limit=3)
        self.assertEqual(result["results"][0]["citation"],
                         "[SEOUL26-P5-02, PDF 2쪽]")
        self.assertTrue(result["results"][0]["stored_pdf_url"].startswith("https://"))

    def test_handler_rejects_bad_input(self):
        from app import search_housing_evidence
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as raised:
            search_housing_evidence(q="")
        self.assertEqual(raised.exception.status_code, 400)

    def test_handler_reports_dataset_failure(self):
        from app import housing_search_status
        from fastapi import HTTPException
        with patch("app.get_housing_search", side_effect=ValueError("bad data")):
            with self.assertRaises(HTTPException) as raised:
                housing_search_status()
        self.assertEqual(raised.exception.status_code, 503)

    def test_routes_page_and_existing_handlers(self):
        from app import housing_search_page, housing_search_status, health, final_result
        paths = {getattr(route, "path", None) for route in app.routes}
        self.assertTrue({"/housing-search", "/api/housing/status",
                         "/api/housing/search", "/ws/replay"} <= paths)
        self.assertTrue(Path(housing_search_page().path).is_file())
        self.assertEqual(housing_search_status()["pending_chunks"], 0)
        self.assertEqual(health()["role"], "broadcast")
        self.assertIsInstance(final_result(), dict)


if __name__ == "__main__":
    unittest.main()
