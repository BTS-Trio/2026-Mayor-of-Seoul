"""Build reproducible cumulative replay snapshots from reported final totals."""
import csv
import json
import random
from itertools import groupby
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
START = datetime(2026, 6, 3, 20, tzinfo=timezone(timedelta(hours=9)))
STEPS = 30

def read_official_units(candidates):
    labels = {f"{candidate['party']} {candidate['candidate']}": candidate["candidate_id"]
              for candidate in candidates}
    fields = {"선거인수": "registered_voters", "투표수": "ballots",
              "무효 투표수": "invalid", "기권자수": "abstained", **labels}
    raw = DATA / "raw" / "nec_governors_20260603.csv"
    with raw.open(encoding="utf-8-sig", newline="") as file:
        source_rows = csv.DictReader(file)
        rows = (row for row in source_rows if row["시도명"] == "서울특별시")
        for key, group in groupby(rows, key=lambda row: (row["구시군명"], row["읍면동명"], row["구분명"])):
            group_rows = list(group)
            values = {fields[row["후보자"]]: int(row["득표수"]) for row in group_rows}
            if len(group_rows) != len(fields) or len(values) != len(fields):
                raise ValueError(f"Duplicate or missing categories in {key!r}")
            if sum(values[cid] for cid in labels.values()) + values["invalid"] != values["ballots"]:
                raise ValueError(f"Unbalanced votes in {key!r}")
            if values["ballots"] + values["abstained"] != values["registered_voters"]:
                raise ValueError(f"Unbalanced electorate in {key!r}")
            district, locality, category = key
            yield {"district": district, "locality": locality if category else "",
                   "vote_category": category or locality, **values}

def load_data():
    meta = json.loads((DATA / "seoul_final_totals.json").read_text(encoding="utf-8"))
    with (DATA / "seoul_final_candidates.csv").open(encoding="utf-8", newline="") as file:
        candidates = list(csv.DictReader(file))
    units = list(read_official_units(candidates))
    for field, expected in {"ballots": meta["total_ballots"], "registered_voters": meta["registered_voters"],
                            "invalid": meta["invalid_ballots"],
                            **{c["candidate_id"]: int(c["votes"]) for c in candidates}}.items():
        if sum(unit[field] for unit in units) != expected:
            raise ValueError(f"Official aggregate mismatch: {field}")
    return meta, candidates, units

def batch_number(index, total):
    return index * STEPS // total + 1

def reporting_order(units):
    ordered = list(units)
    random.Random(20260603).shuffle(ordered)
    return ordered

def generate():
    meta, candidates, units = load_data()
    ordered = reporting_order(units)
    batches = [[] for _ in range(STEPS + 1)]
    for i, unit in enumerate(ordered):
        batches[batch_number(i, len(ordered))].append(unit)
    votes_by_candidate = {c["candidate_id"]: 0 for c in candidates}
    invalid_count = 0
    counted_units = 0
    for step, batch in enumerate(batches):
        for unit in batch:
            invalid_count += unit["invalid"]
            for candidate_id in votes_by_candidate:
                votes_by_candidate[candidate_id] += unit[candidate_id]
        counted_units += len(batch)
        valid_count = sum(votes_by_candidate.values())
        counted = valid_count + invalid_count
        row_id = f"SIM-SEOUL-{step:03}"
        yield {
            "event": "snapshot", "event_id": row_id, "sequence": step,
            "mode": "simulation", "label": "교육용 시뮬레이션 · 가상 개표",
            "scope": "서울시 전체", "count_unit": "공식 개표 단위의 가상 순서",
            "counted_units": counted_units, "total_units": len(units),
            "timestamp_is_simulated": True,
            "simulated_at": (START + step * timedelta(minutes=15)).isoformat(),
            "race": meta["race"], "region": meta["region"],
            "registered_voters": meta["registered_voters"], "total_ballots": meta["total_ballots"],
            "counted_ballots": counted, "valid_ballots_counted": valid_count,
            "invalid_ballots_counted": invalid_count,
            "count_progress_pct": round(counted / meta["total_ballots"] * 100, 2),
            "final_turnout_pct": round(meta["total_ballots"] / meta["registered_voters"] * 100, 2),
            "fact_source_id": "SRC-NEC-01", "verified_source_ids": meta["verified_source_ids"],
            "schema_source_id": meta["official_dataset_id"], "complete": step == STEPS,
            "candidates": [
                {"candidate_id": c["candidate_id"], "name": c["candidate"], "party": c["party"],
                 "row_id": f"{row_id}-{i + 1:02}", "votes": votes,
                 "vote_share_pct": (votes * 10000 // valid_count) / 100 if valid_count else None}
                for i, c in enumerate(candidates) for votes in [votes_by_candidate[c["candidate_id"]]]
            ],
        }

def main():
    rows = list(generate())
    with (DATA / "demo_snapshots.jsonl").open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            print(json.dumps(row, ensure_ascii=False), file=file)
    columns = ["event_id", "sequence", "mode", "simulated_at", "region", "race",
               "count_progress_pct", "counted_ballots", "valid_ballots_counted",
               "invalid_ballots_counted", "fact_source_id", "candidate_id", "row_id",
               "name", "party", "votes", "vote_share_pct"]
    with (DATA / "demo_candidates.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            for candidate in row["candidates"]:
                writer.writerow({**row, **candidate})
    _, candidates, units = load_data()
    ordered = reporting_order(units)
    unit_fields = ["district", "locality", "vote_category", "registered_voters", "ballots",
                   "invalid", "abstained", *(c["candidate_id"] for c in candidates)]
    with (DATA / "demo_reporting_schedule.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, ["sequence", "simulated_at", *unit_fields])
        writer.writeheader()
        for index, unit in enumerate(ordered):
            step = batch_number(index, len(ordered))
            writer.writerow({"sequence": step, "simulated_at": rows[step]["simulated_at"], **unit})
    with (DATA / "seoul_final_by_district.csv").open("w", encoding="utf-8-sig", newline="") as file:
        fields = ["district", "registered_voters", "ballots", "invalid", "abstained",
                  *(c["candidate_id"] for c in candidates)]
        writer = csv.DictWriter(file, fields)
        writer.writeheader()
        for district, items in groupby(sorted(units, key=lambda unit: unit["district"]),
                                       key=lambda unit: unit["district"]):
            district_units = list(items)
            writer.writerow({"district": district, **{field: sum(u[field] for u in district_units)
                                                       for field in fields[1:]}})
    template = DATA.parent.joinpath("index.html").read_text(encoding="utf-8")
    preview = template.replace(
        'let current;',
        'const offlineFrames = ' + json.dumps(rows, ensure_ascii=False) + ';\nlet current;'
    ).replace(
        "    set('status', 'README의 실행 명령으로 서버를 시작한 뒤 접속하세요.');",
        """    clearInterval(current);
    let index = 0;
    render(offlineFrames[index]);
    set('status', '오프라인 재생 · 시뮬레이션 진행 중');
    current = setInterval(() => {
      const frame = offlineFrames[++index];
      render(frame);
      if (frame.complete) {
        clearInterval(current);
        current = undefined;
        set('status', '시뮬레이션 완료 · 공식 최종 득표수 일치');
      }
    }, 2000);"""
    ).replace('  if (current) current.close();', "  if (current && location.protocol !== 'file:') current.close();")
    DATA.parent.joinpath("offline-preview.html").write_text(preview, encoding="utf-8")
    print(f"{len(rows)} snapshots, {sum(len(row['candidates']) for row in rows)} candidate rows")

if __name__ == "__main__":
    main()
