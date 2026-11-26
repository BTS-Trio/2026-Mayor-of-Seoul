import csv
import json
import unittest

from generate_demo import DATA, generate

class DemoTest(unittest.TestCase):
    def test_district_snapshots_match_city_and_final_csv(self):
        snapshots = list(generate())
        for snapshot in snapshots:
            districts = snapshot["districts"]
            self.assertEqual(len(districts), 25)
            self.assertEqual(sum(d["counted_units"] for d in districts.values()), snapshot["counted_units"])
            for index, candidate in enumerate(snapshot["candidates"]):
                self.assertEqual(sum(d["votes"][index] for d in districts.values()), candidate["votes"])
        with (DATA / "seoul_final_by_district.csv").open(encoding="utf-8-sig", newline="") as file:
            final = snapshots[-1]
            for row in csv.DictReader(file):
                actual = final["districts"][row["district"]]
                self.assertEqual(actual["counted_units"], actual["total_units"])
                self.assertEqual(actual["votes"], [int(row[c["candidate_id"]]) for c in final["candidates"]])

    def test_packaged_data_matches_generator(self):
        lines = (DATA / "demo_snapshots.jsonl").read_text(encoding="utf-8").splitlines()
        snapshots = [json.loads(line) for line in lines]
        self.assertEqual(snapshots, list(generate()))
        with (DATA / "demo_candidates.csv").open(encoding="utf-8-sig", newline="") as file:
            self.assertEqual(len(list(csv.DictReader(file))), 155)

    def test_balancing_and_final_totals(self):
        snapshots = list(generate())
        self.assertEqual(len(snapshots), 31)
        self.assertEqual(snapshots[0]["counted_ballots"], 0)
        self.assertEqual(snapshots[-1]["count_progress_pct"], 100)
        self.assertEqual(snapshots[-1]["counted_ballots"], 5289383)
        self.assertEqual(snapshots[-1]["invalid_ballots_counted"], 56401)
        with (DATA / "seoul_final_candidates.csv").open(encoding="utf-8", newline="") as file:
            final = list(csv.DictReader(file))
        for candidate, reported in zip(snapshots[-1]["candidates"], final):
            self.assertEqual(candidate["votes"], int(reported["votes"]))
            self.assertEqual(candidate["vote_share_pct"], float(reported["reported_share_pct"]))
        self.assertEqual(snapshots[-1]["candidates"][1]["votes"] - snapshots[-1]["candidates"][0]["votes"], 60259)
        for previous, current in zip(snapshots, snapshots[1:]):
            self.assertLess(previous["counted_ballots"], current["counted_ballots"])
            self.assertEqual(current["sequence"], previous["sequence"] + 1)
            for before, after in zip(previous["candidates"], current["candidates"]):
                self.assertLessEqual(before["votes"], after["votes"])
        for snapshot in snapshots:
            self.assertTrue(snapshot["timestamp_is_simulated"])
            self.assertEqual(snapshot["mode"], "simulation")
            self.assertEqual(sum(c["votes"] for c in snapshot["candidates"]), snapshot["valid_ballots_counted"])
            self.assertEqual(snapshot["valid_ballots_counted"] + snapshot["invalid_ballots_counted"], snapshot["counted_ballots"])

if __name__ == "__main__":
    unittest.main()
