PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS CANDIDATE (
 candidate_id TEXT PRIMARY KEY, name TEXT NOT NULL, party TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('running','withdrawn')),
 data_kind TEXT NOT NULL, withdrawn_at TEXT, profile TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS SOURCE (
 source_id TEXT PRIMARY KEY, provider TEXT NOT NULL, title TEXT NOT NULL,
 data_kind TEXT NOT NULL, url TEXT, local_path TEXT, sha256 TEXT, pdf_pages INTEGER
);
CREATE TABLE IF NOT EXISTS SNAPSHOT (
 event_id TEXT PRIMARY KEY, sequence INTEGER NOT NULL UNIQUE, simulated_at TEXT NOT NULL,
 counted_ballots INTEGER NOT NULL CHECK(counted_ballots>=0), valid_ballots INTEGER NOT NULL,
 invalid_ballots INTEGER NOT NULL, count_progress_pct REAL NOT NULL,
 source_id TEXT NOT NULL REFERENCES SOURCE(source_id), mode TEXT NOT NULL,
 CHECK(counted_ballots=valid_ballots+invalid_ballots)
);
CREATE TABLE IF NOT EXISTS SNAPSHOT_VOTE (
 row_id TEXT PRIMARY KEY, event_id TEXT NOT NULL REFERENCES SNAPSHOT(event_id),
 candidate_id TEXT NOT NULL REFERENCES CANDIDATE(candidate_id), votes INTEGER NOT NULL CHECK(votes>=0),
 vote_share_pct REAL, UNIQUE(event_id,candidate_id)
);
CREATE TABLE IF NOT EXISTS EVIDENCE (
 chunk_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES SOURCE(source_id),
 candidate_id TEXT NOT NULL REFERENCES CANDIDATE(candidate_id), document_id TEXT NOT NULL,
 pdf_page INTEGER CHECK(pdf_page IS NULL OR pdf_page>=1), text TEXT NOT NULL,
 citation TEXT NOT NULL, data_kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ARTICLE (
 article_id TEXT PRIMARY KEY, snapshot_id TEXT REFERENCES SNAPSHOT(event_id),
 title TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, data_kind TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ARTICLE_EVIDENCE (
 id TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES ARTICLE(article_id), sentence_no INTEGER NOT NULL,
 sentence_id TEXT NOT NULL, sentence TEXT NOT NULL,
 chunk_id TEXT REFERENCES EVIDENCE(chunk_id), row_id TEXT REFERENCES SNAPSHOT_VOTE(row_id),
 CHECK((chunk_id IS NOT NULL AND row_id IS NULL) OR (chunk_id IS NULL AND row_id IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS FACT_CHECK (
 check_id TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES ARTICLE(article_id),
 verdict TEXT NOT NULL, reason TEXT NOT NULL, checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS REVIEW (
 review_id TEXT PRIMARY KEY, article_id TEXT NOT NULL REFERENCES ARTICLE(article_id),
 action TEXT NOT NULL, reviewer TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS DISTRICT (
 district_id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS DISTRICT_VOTE (
 event_id TEXT NOT NULL REFERENCES SNAPSHOT(event_id), district_id TEXT NOT NULL REFERENCES DISTRICT(district_id),
 candidate_id TEXT NOT NULL REFERENCES CANDIDATE(candidate_id), votes INTEGER NOT NULL CHECK(votes>=0),
 PRIMARY KEY(event_id,district_id,candidate_id)
);
