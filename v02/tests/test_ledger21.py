"""Independent canonical 21-column ledger: schema, safety and concurrency."""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from v02lab.ledger21 import (  # noqa: E402
    COLUMNS21,
    SCHEMA_ID,
    BudgetExhausted,
    DuplicateLaunch,
    EpisodeKey21,
    EpisodeLedger21,
    LedgerFormatError,
    header_sha256,
)

WORKER = Path(__file__).resolve().parent / "ledger21_worker.py"


def _key(tag, rep=0, cond="00"):
    return EpisodeKey21(run_id=tag, anchor_id="anchor-0000", repetition=rep, condition=cond)


def _reserve(led, tag, *, scope="race", cap=10, rep=0, cond="00"):
    return led.reserve_launch(_key(tag, rep, cond), method="WideExplore", master_seed=1,
                              anchor_id="anchor-0000", anchor_index=0, repetition=rep,
                              condition=cond, sim_seed=1, stream="discovery",
                              max_episodes=cap, budget_scope=scope)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "runs" / "episode_ledger.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self):
        with open(self.path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))


class TestSchema(Base):
    def test_canonical_header_on_create(self):
        EpisodeLedger21(self.path)
        with open(self.path, encoding="utf-8") as fh:
            head = fh.readline().rstrip("\r\n")
        self.assertEqual(next(csv.reader([head])), COLUMNS21)

    def test_columns_count(self):
        self.assertEqual(len(COLUMNS21), 21)

    def test_fingerprint_roundtrip(self):
        led = EpisodeLedger21(self.path)
        fp = led.write_schema_fingerprint(self.path.with_name("episode_ledger.schema.json"))
        led.verify_schema_fingerprint(fp)
        self.assertEqual(led.schema_fingerprint()["schema_id"], SCHEMA_ID)

    def test_fingerprint_detects_tamper(self):
        led = EpisodeLedger21(self.path)
        fp = led.write_schema_fingerprint(self.path.with_name("episode_ledger.schema.json"))
        # append a row -> header SHA unchanged (only header is hashed) so no drift;
        # instead corrupt the fingerprint value to simulate tamper
        import json
        payload = json.loads(fp.read_text())
        payload["header_sha256"] = "0" * 64
        fp.write_text(json.dumps(payload))
        with self.assertRaises(LedgerFormatError):
            led.verify_schema_fingerprint(fp)

    def test_bad_header_rejected(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("a,b,c\n", encoding="utf-8")
        with self.assertRaises(LedgerFormatError):
            EpisodeLedger21(self.path)

    def test_row_width_guard(self):
        led = EpisodeLedger21(self.path)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(",".join(["x"] * (len(COLUMNS21) + 4)) + "\n")
        with self.assertRaises(LedgerFormatError):
            EpisodeLedger21(self.path)


class TestBudget(Base):
    def test_reserve_and_outcome_roundtrip(self):
        led = EpisodeLedger21(self.path)
        row = _reserve(led, "A", cap=5)
        led.record_outcome(_key("A"), launch_row=row, exit_status="completed", ego_collision=0,
                           termination="goal", wall_time_s=0.01, raw_path="x.json")
        self.assertEqual(led.launched_count_scope("race"), 1)
        self.assertEqual(led.outcome_count("completed"), 1)

    def test_cap_enforced(self):
        led = EpisodeLedger21(self.path)
        _reserve(led, "A", cap=1)
        with self.assertRaises(BudgetExhausted):
            _reserve(led, "B", cap=1)

    def test_scopes_independent(self):
        led = EpisodeLedger21(self.path)
        _reserve(led, "A", scope="s1", cap=1)
        _reserve(led, "B", scope="s2", cap=1)  # different scope -> allowed
        self.assertEqual(led.launched_count_scope("s1"), 1)
        self.assertEqual(led.launched_count_scope("s2"), 1)

    def test_duplicate_key_refused(self):
        led = EpisodeLedger21(self.path)
        _reserve(led, "A", cap=5)
        with self.assertRaises(DuplicateLaunch):
            _reserve(led, "A", cap=5)

    def test_no_free_retry_new_run_id_billed(self):
        led = EpisodeLedger21(self.path)
        _reserve(led, "A", cap=5)
        _reserve(led, "A2", cap=5)  # new run id -> new key -> billed again
        self.assertEqual(led.launched_count_scope("race"), 2)

    def test_scope_state_survives_reopen(self):
        EpisodeLedger21(self.path)
        led1 = EpisodeLedger21(self.path)
        _reserve(led1, "A", scope="s1", cap=1)
        led2 = EpisodeLedger21(self.path)  # fresh instance reads disk
        self.assertEqual(led2.launched_count_scope("s1"), 1)
        with self.assertRaises(BudgetExhausted):
            _reserve(led2, "B", scope="s1", cap=1)


class TestCrossProcess(Base):
    def test_eight_processes_cap_three(self):
        EpisodeLedger21(self.path)  # create header
        procs = []
        for i in range(8):
            procs.append(subprocess.Popen(
                [sys.executable, str(WORKER), str(self.path), f"p{i}", "3", "race"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        outs = [p.communicate()[0].strip() for p in procs]
        self.assertEqual(outs.count("OK"), 3, outs)
        self.assertEqual(len([r for r in self.rows() if r["row_type"] == "launch"]), 3)


if __name__ == "__main__":
    unittest.main()
