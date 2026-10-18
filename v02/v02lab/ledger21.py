"""Independent canonical 21-column ledger (V02 L-01 design, offline).

This is a **self-contained** re-implementation for the V02 protocol (proposal
section 9): a fresh file gets the canonical 21-column header atomically, reads
are **strict** (header must equal :data:`COLUMNS21`; legacy prefix tolerance is
NOT applied here), row width is guarded, billing is reserve-before-launch under a
process lock + cross-process OS lock, duplicate keys are refused before any work
and force-reruns are billed again (no free retry).

It never touches a V01 ledger. Standard library only.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA_ID = "sfl-v02-21col"
COLUMNS21 = [
    "row_type", "episode_key", "run_id", "phase", "method", "master_seed",
    "anchor_id", "anchor_index", "repetition", "condition", "stream", "sim_seed",
    "exit_status", "ego_collision", "termination", "error_type", "started_utc",
    "ended_utc", "wall_time_s", "raw_path", "budget_scope",
]
assert len(COLUMNS21) == 21, "canonical schema must have exactly 21 columns"


class Ledger21Error(RuntimeError):
    pass


class LedgerFormatError(Ledger21Error):
    pass


class BudgetExhausted(Ledger21Error):
    pass


class DuplicateLaunch(Ledger21Error):
    pass


class LedgerLockTimeout(Ledger21Error):
    pass


_LOCK_REGISTRY: dict[str, threading.Lock] = {}
_LOCK_GUARD = threading.Lock()


def _process_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCK_GUARD:
        lock = _LOCK_REGISTRY.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCK_REGISTRY[key] = lock
        return lock


@contextlib.contextmanager
def _file_lock(lock_path: Path, timeout_s: float = 60.0) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if os.name == "nt":  # pragma: no cover - Windows
            import msvcrt
            deadline = time.monotonic() + timeout_s
            while True:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LedgerLockTimeout(f"could not lock {lock_path} in {timeout_s}s")
                    time.sleep(0.02)
            try:
                yield
            finally:
                with contextlib.suppress(OSError):
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover - POSIX
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def header_sha256(path: str | Path) -> str:
    with open(path, "rb") as fh:
        head = fh.readline()
    return hashlib.sha256(head).hexdigest()


def validate_header(names: list[str]) -> None:
    if names != COLUMNS21:
        raise LedgerFormatError(
            f"V02 ledger header must equal COLUMNS21 exactly; got {names!r}")


@dataclass(frozen=True)
class EpisodeKey21:
    run_id: str
    anchor_id: str
    repetition: int
    condition: str

    def __str__(self) -> str:
        return f"{self.run_id}|{self.anchor_id}|r{self.repetition}|{self.condition}"


class EpisodeLedger21:
    """Thread- and process-safe append-only 21-column ledger."""

    def __init__(self, path: str | Path, *, phase: str = "formal") -> None:
        self.path = Path(path)
        self.phase = phase
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = _process_lock(self.path)
        self._lock_path = self.path.with_name(self.path.name + ".lock")
        self._fieldnames: list[str] | None = None
        self._consumed = 0
        self._reset()
        with self._lock, _file_lock(self._lock_path):
            if not self.path.exists() or self.path.stat().st_size == 0:
                self._write_header_unlocked()
        self._rebuild()

    # -- counters ---------------------------------------------------------
    def _reset(self) -> None:
        self._launched: set[str] = set()
        self._scope: dict[str, set[str]] = {}
        self._outcomed: dict[str, set[str]] = {}

    def _ingest(self, row: dict[str, str]) -> None:
        if row.get("row_type") == "launch":
            ek = row.get("episode_key", "")
            scope = row.get("budget_scope") or self.phase
            self._launched.add(ek)
            self._scope.setdefault(scope, set()).add(ek)
        elif row.get("row_type") == "outcome":
            self._outcomed.setdefault(row.get("exit_status", ""), set()).add(row.get("episode_key", ""))

    def _resync(self) -> None:
        if not self.path.exists():
            return
        size = self.path.stat().st_size
        if size < self._consumed:
            self._reset()
            self._consumed = 0
            self._fieldnames = None
        if self._fieldnames is None:
            with open(self.path, "rb") as fh:
                head = fh.readline()
            if not head:
                return
            names = next(csv.reader([head.decode("utf-8").rstrip("\r\n")]))
            validate_header(names)
            self._fieldnames = list(COLUMNS21)
            self._consumed = len(head)
        if size <= self._consumed:
            return
        with open(self.path, "rb") as fh:
            fh.seek(self._consumed)
            chunk = fh.read()
        nl = chunk.rfind(b"\n")
        if nl < 0:
            return
        complete = chunk[: nl + 1]
        parsed: list[dict[str, str]] = []
        for line in complete.decode("utf-8").splitlines():
            if not line.strip():
                continue
            fields = next(csv.reader([line]))
            if len(fields) > len(self._fieldnames):
                raise LedgerFormatError(
                    f"row has {len(fields)} fields > {len(self._fieldnames)} header columns; "
                    "refusing to drop surplus fields")
            parsed.append({n: (fields[i] if i < len(fields) else "")
                           for i, n in enumerate(self._fieldnames)})
        self._consumed += len(complete)
        for row in parsed:
            self._ingest(row)

    def _rebuild(self) -> None:
        with self._lock, _file_lock(self._lock_path):
            self._reset()
            self._consumed = 0
            self._fieldnames = None
            self._resync()

    # -- low level --------------------------------------------------------
    def _write_header_unlocked(self) -> None:
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=COLUMNS21, extrasaction="ignore").writeheader()
            fh.flush()
            os.fsync(fh.fileno())

    def _append_unlocked(self, rows: Iterable[dict[str, Any]]) -> None:
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS21, extrasaction="ignore")
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in COLUMNS21})
            fh.flush()
            os.fsync(fh.fileno())

    # -- accounting -------------------------------------------------------
    def launched_count_scope(self, scope: str) -> int:
        return len(self._scope.get(scope, set()))

    def outcome_count(self, exit_status: str | None = None) -> int:
        if exit_status is None:
            return len(set().union(*self._outcomed.values())) if self._outcomed else 0
        return len(self._outcomed.get(exit_status, set()))

    # -- writing ----------------------------------------------------------
    def reserve_launch(self, key: EpisodeKey21, *, method: str, master_seed: int,
                       anchor_id: str, anchor_index: int, repetition: int, condition: str,
                       sim_seed: int, stream: str = "discovery", max_episodes: int | None = None,
                       budget_scope: str | None = None, run_id: str | None = None) -> dict[str, Any]:
        if stream not in ("discovery", "audit"):
            raise ValueError(f"stream must be discovery/audit, got {stream!r}")
        scope = budget_scope or self.phase
        row = {
            "row_type": "launch", "episode_key": str(key), "run_id": run_id or key.run_id,
            "phase": self.phase, "method": method, "master_seed": master_seed,
            "anchor_id": anchor_id, "anchor_index": anchor_index, "repetition": repetition,
            "condition": condition, "stream": stream, "sim_seed": sim_seed,
            "exit_status": "pending", "budget_scope": scope, "started_utc": utc_now_iso(),
        }
        with self._lock, _file_lock(self._lock_path):
            self._resync()
            scoped = self._scope.setdefault(scope, set())
            if max_episodes is not None and len(scoped) >= max_episodes:
                raise BudgetExhausted(f"scope {scope!r} exhausted: {len(scoped)}/{max_episodes}")
            ek = str(key)
            if ek in scoped:
                raise DuplicateLaunch(f"episode_key {ek} already billed in scope {scope!r}")
            scoped.add(ek)
            self._launched.add(ek)
            self._append_unlocked([row])
        return row

    def record_outcome(self, key: EpisodeKey21, *, launch_row: dict[str, Any], exit_status: str,
                       ego_collision: int | None, termination: str = "", error_type: str = "",
                       wall_time_s: float | None = None, raw_path: str = "") -> None:
        if exit_status not in ("completed", "error", "interrupted"):
            raise ValueError(f"invalid exit_status {exit_status!r}")
        if ego_collision is not None and ego_collision not in (0, 1):
            raise ValueError(f"ego_collision must be 0/1/None, got {ego_collision!r}")
        if exit_status == "completed" and ego_collision is None:
            raise ValueError("a completed episode must record ego_collision 0/1")
        row = {
            "row_type": "outcome", "episode_key": str(key), "run_id": launch_row.get("run_id", ""),
            "phase": launch_row.get("phase", self.phase), "method": launch_row.get("method", ""),
            "master_seed": launch_row.get("master_seed", ""), "anchor_id": launch_row.get("anchor_id", ""),
            "anchor_index": launch_row.get("anchor_index", ""), "repetition": launch_row.get("repetition", ""),
            "condition": launch_row.get("condition", ""), "stream": launch_row.get("stream", ""),
            "sim_seed": launch_row.get("sim_seed", ""), "exit_status": exit_status,
            "ego_collision": "" if ego_collision is None else ego_collision,
            "termination": termination, "error_type": error_type, "ended_utc": utc_now_iso(),
            "wall_time_s": "" if wall_time_s is None else round(float(wall_time_s), 6),
            "raw_path": raw_path,
        }
        with self._lock, _file_lock(self._lock_path):
            self._resync()
            self._append_unlocked([row])
            self._outcomed.setdefault(exit_status, set()).add(row["episode_key"])

    # -- diagnostics / fingerprint ---------------------------------------
    def diagnose(self) -> dict[str, Any]:
        rows = []
        if self.path.exists():
            with open(self.path, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
        return {
            "path": str(self.path),
            "schema_id": SCHEMA_ID,
            "total_rows": len(rows),
            "launch_rows": sum(1 for r in rows if r.get("row_type") == "launch"),
            "outcome_rows": sum(1 for r in rows if r.get("row_type") == "outcome"),
            "header_sha256": header_sha256(self.path) if self.path.exists() else None,
        }

    def schema_fingerprint(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "columns": list(COLUMNS21),
            "header_sha256": header_sha256(self.path) if self.path.exists() else None,
        }

    def write_schema_fingerprint(self, path: str | Path) -> Path:
        import json
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(self.schema_fingerprint(), written_utc=utc_now_iso())
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
        return p

    def verify_schema_fingerprint(self, path: str | Path) -> None:
        import json
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if payload.get("schema_id") != SCHEMA_ID:
            raise LedgerFormatError(f"schema_id mismatch: {payload.get('schema_id')!r}")
        cur = header_sha256(self.path) if self.path.exists() else None
        if payload.get("header_sha256") != cur:
            raise LedgerFormatError("header SHA-256 drift detected (schema tamper/mismatch)")
