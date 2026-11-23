"""Retrieve housing pledge evidence without changing its citations.

This is lexical retrieval (BM25 with Korean character bigrams), not an
embedding service or an article generator. It uses only the prepared corpus.
"""
import copy
import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from evidence_contract import valid_evidence

DATA_PATH = Path(__file__).resolve().parent / "data" / "rag" / "housing_evidence.json"
STOPWORDS = {
    "2026", "서울시장", "후보", "후보들은", "공약", "문제", "해결을",
    "위해", "어떤", "제시했나", "알려줘", "내용", "관련", "비교",
}
HOUSING_TERMS = (
    "주택", "주거", "공급", "임대", "전세", "월세", "보증금",
    "재건축", "재개발", "세입자", "주거권", "리모델링",
)


def tokens(text):
    """Keep whole words and Korean bigrams so particles do not hide matches."""
    result = Counter()
    normalized = unicodedata.normalize("NFKC", text).lower()
    for word in re.findall(r"[가-힣]+|[a-z][a-z0-9]*|\d+(?:\.\d+)?", normalized):
        if word in STOPWORDS or (len(word) == 1 and not word.isdigit()):
            continue
        result[word] += 1
        if re.fullmatch(r"[가-힣]{3,}", word):
            for index in range(len(word) - 1):
                result[word[index:index + 2]] += 1
    return result


def _https(value):
    parsed = urlparse(value or "")
    return parsed.scheme == "https" and bool(parsed.netloc)


class HousingSearch:
    def __init__(self, dataset):
        self.dataset = copy.deepcopy(dataset)
        if self.dataset.get("schema_version") != "2.0":
            raise ValueError("지원하지 않는 검색 자료 형식입니다.")
        self.chunks = self.dataset.get("chunks", [])
        documents = {item["document_id"]: item for item in self.dataset["documents"]}
        self.pending = self.dataset.get("pending_chunks", [])
        seen = set()
        for item in self.chunks:
            doc = documents.get(item.get("document_id"))
            if item.get("chunk_id") in seen or not valid_evidence(item,doc):
                raise ValueError("근거의 ID·쪽수·출처 정보가 일치하지 않습니다.")
            seen.add(item["chunk_id"])
        if any(item.get("rag_eligible") is not False for item in self.pending):
            raise ValueError("보류 근거를 검색 대상으로 사용할 수 없습니다.")
        self.documents = documents
        self.names = sorted({item["candidate"] for item in documents.values()})
        self.term_counts = [
            tokens(item.get("topic", "") + " " + item["summary"] + " " + item["evidence_text"] + " " + item["text"])
            for item in self.chunks
        ]
        self.lengths = [sum(counts.values()) for counts in self.term_counts]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1) or 1
        self.document_frequency = Counter()
        for counts in self.term_counts:
            self.document_frequency.update(counts.keys())

    def status(self):
        options = []
        for name in self.names:
            docs = [item for item in self.documents.values() if item["candidate"] == name]
            options.append({
                "name": name,
                "withdrawn": any(item.get("candidate_withdrawn") for item in docs),
                "ready_chunks": sum(item["candidate"] == name for item in self.chunks),
                "pending_chunks": sum(item["candidate"] == name for item in self.pending),
            })
        return {
            "question": self.dataset["question"],
            "prepared_date_kst": self.dataset["prepared_date_kst"],
            "retrieval_method": "lexical_bm25_korean_bigrams",
            "ready_chunks": len(self.chunks),
            "pending_chunks": len(self.pending),
            "candidate_options": options,
            "comparison_coverage_complete": self.dataset["comparison_coverage_complete"],
        }

    def search(self, query, candidate="", limit=10, include_withdrawn=False):
        query = query.strip()
        candidate = candidate.strip()
        if not 2 <= len(query) <= 500:
            raise ValueError("검색 질문을 2~500자로 입력해 주세요.")
        if type(limit) is not int or not 1 <= limit <= 30:
            raise ValueError("검색 개수는 1~30개여야 합니다.")
        if candidate and candidate not in self.names:
            raise ValueError("등록된 후보 이름을 선택해 주세요.")
        named = [name for name in self.names if name in query]
        selected_names = {candidate} if candidate else set(named or self.names)
        withdrawn = {d['candidate'] for d in self.documents.values() if d.get('candidate_withdrawn')}
        if not include_withdrawn:
            selected_names -= withdrawn
        broad = (
            not candidate and not named
            and any(word in query for word in ("후보", "비교", "차이"))
            and any(word in query for word in ("주거", "주택"))
        )
        query_terms = tokens(query)
        if broad:
            # A comparison must also find housing passages that say "주택",
            # "임대" or "재건축" without literally saying "주거".
            for word in HOUSING_TERMS:
                for term in tokens(word):
                    query_terms[term] += 0.3
        scored = []
        count = len(self.chunks)
        for index, item in enumerate(self.chunks):
            if item["candidate"] not in selected_names:
                continue
            score = 0.0
            for term, query_weight in query_terms.items():
                frequency = self.term_counts[index][term]
                if not frequency:
                    continue
                df = self.document_frequency[term]
                idf = math.log(1 + (count - df + 0.5) / (df + 0.5))
                norm = frequency + 1.2 * (
                    0.25 + 0.75 * self.lengths[index] / self.average_length
                )
                score += query_weight * idf * frequency * 2.2 / norm
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["chunk_id"]))
        ranked = scored
        if broad:
            first, remaining, represented = [], [], set()
            for pair in scored:
                name = pair[1]["candidate"]
                if name in represented:
                    remaining.append(pair)
                else:
                    first.append(pair)
                    represented.add(name)
            ranked = first + remaining
        results = []
        for score, item in ranked[:limit]:
            result = copy.deepcopy(item)
            result["score"] = round(score, 6)
            results.append(result)
        returned_names = {item["candidate"] for item in results}
        pending = [
            {"candidate": item["candidate"],
             "document_id": item["document_id"],
             "reason": item.get("exclusion_reason", "근거 확인 대기"),
             "stored_pdf_url": item["pdf_url"]}
            for item in self.pending if item["candidate"] in selected_names
        ]
        return {
            "query": query,
            "retrieval_method": "lexical_bm25_korean_bigrams",
            "candidate_balancing": broad,
            "results": results,
            "coverage": {
                "requested_candidates": sorted(selected_names),
                "returned_candidates": sorted(returned_names),
                "not_returned_candidates": sorted(selected_names - returned_names),
                "pending_evidence": pending,
                "all_requested_candidates_returned": selected_names <= returned_names,
            },
            "scope": "실제 공약 일부와 교육용 가상 공약의 BM25 검색. 공약 이행·실현 가능성 검증이나 기사 생성은 포함하지 않음.",
            "excluded_withdrawn_candidates": sorted(withdrawn) if not include_withdrawn else [],
        }


@lru_cache(maxsize=1)
def get_housing_search():
    with DATA_PATH.open(encoding="utf-8") as source:
        return HousingSearch(json.load(source))
