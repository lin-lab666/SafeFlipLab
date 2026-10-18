"""EpisodeLedger: durable, append-only accounting of every launched episode.

Budget rule (protocol): every *launched* episode counts, including failed,
errored and interrupted attempts. There are no free retries. The ledger is
therefore written *before* an episode is launched ("reserve-before-launch")
and the outcome is appended afterwards as a separate row. Rows are never
mutated or deleted, so an interrupted run still shows the launched attempt.

Two row types share one ``episode_key``:

* ``launch``  - the attempt was started (this is what consumes budget);
* ``outcome`` - how the attempt ended (completed / error / interrupted).

A launch row without an outcome row means the process died mid-episode; it
still counts against the budget and its Y value stays missing (never assumed
to be 0 or 1).

Concurrency model
-----------------
Budget accounting must be correct across *independent* ``EpisodeLedger``
instances and across *processes* that share one CSV; a per-instance
``threading.Lock`` plus a private in-memory cache is not enough (two instances
that both cached "scope empty" would each pass their own check and both append
a launch, overspending the cap). This module therefore adds:

* a process-wide lock registry keyed by the resolved ledger path, so every
  instance in one process that points at the same CSV serialises on one lock;
* an OS-level exclusive lock on a sidecar ``<ledger>.lock`` file (Windows
  ``msvcrt.locking`` / POSIX ``fcntl.flock``) so separate processes serialise;
* an in-lock *reconciliation* step that re-reads the durable CSV (incrementally,
  from the last consumed byte) before every billing decision, so the budget and
  duplicate checks are always made against the authoritative on-disk state, not
  a possibly-stale cache.
"""
from __future__ import annotations

import contextlib
import csv
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

LEDGER_FILENAME = "episode_ledger.csv"

COLUMNS = [
    "row_type",          # launch | outcome
    "episode_key",
    "run_id",
    "phase",             # smoke | pilot | formal
    "method",            # WideExplore | VerifyFirst
    "master_seed",
    "anchor_id",
    "anchor_index",
    "repetition",
    "condition",         # 00 | 10 | 01 | 11
    "stream",            # discovery | audit
    "sim_seed",
    "exit_status",       # pending | completed | error | interrupted
    "ego_collision",     # 0 | 1 | (empty when unknown)
    "termination",       # collision | offroad | goal | timeout | ...
    "error_type",
    "started_utc",
    "ended_utc",
    "wall_time_s",
    "raw_path",
    "budget_scope",      # budget scope for the launch (phase, or phase|method|seed)
]

VALID_PHASES = ("smoke", "pilot", "formal")


class BudgetExhausted(RuntimeError):
    """Raised when launching another episode would exceed the phase budget."""


class DuplicateLaunch(RuntimeError):
    """Raised when the same episode_key is billed twice within one budget scope.

    A repeated launch attempt (same run_id + anchor + repetition + condition) is
    rejected *before* any simulator work, so a stray double-trigger can never
    "start for real several times but bill only once". Force-reruns get a fresh
    run_id and therefore a fresh episode_key, so they are billed again on purpose
    (no free retry).
    """


class LedgerLockTimeout(RuntimeError):
    """Raised when the cross-process ledger lock cannot be acquired in time.

    Failing loudly (rather than appending without the lock) is deliberate: a
    budget decision made without the lock could overspend the frozen cap.
    """


class LedgerFormatError(RuntimeError):
    """Raised when the on-disk ledger header cannot be safely reconciled.

    A header that is neither ``COLUMNS`` nor a strict *prefix* of ``COLUMNS``
    (unknown, extra, reordered, or otherwise mismatched columns) is refused
    rather than guessed at: reinterpreting it column-by-column could silently
    drop a field (e.g. ``budget_scope``), demoting a per-(method, seed) formal
    budget to phase level and letting a resumed run overspend. Failing loudly
    keeps a corrupt/incompatible ledger from being read as if it were valid.
    """


# -- process-wide + cross-process mutual exclusion -------------------------
_LOCK_REGISTRY: dict[str, threading.Lock] = {}
_LOCK_REGISTRY_GUARD = threading.Lock()


def _process_lock_for(path: Path) -> threading.Lock:
    """One shared ``threading.Lock`` per resolved ledger path, per process.

    Distinct ``EpisodeLedger`` instances opened on the same CSV in the same
    process must serialise on the *same* lock; a per-instance lock would let
    two instances race (the multi-instance overspend bug this fixes).
    """
    key = str(path.resolve())
    with _LOCK_REGISTRY_GUARD:
        lock = _LOCK_REGISTRY.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCK_REGISTRY[key] = lock
        return lock


@contextlib.contextmanager
def _exclusive_file_lock(lock_path: Path, timeout_s: float = 60.0) -> Iterator[None]:
    """Cross-process exclusive lock over an OS-level lock file.

    Windows uses ``msvcrt.locking`` (mandatory byte-range lock); POSIX uses
    ``fcntl.flock``. Both are held for the whole billing critical section so the
    read-check-append sequence is atomic across processes. A distinct sidecar
    file is locked (never the ledger CSV itself), so no historical ledger byte
    is ever touched.

    A single deadline bounds the *whole* acquisition: creating the parent
    directory, opening/creating the sidecar and taking the byte-range lock. The
    open/create step is inside the retry loop because on Windows it can fail
    transiently with a sharing violation (``PermissionError``) while another
    process is concurrently creating or deleting the same sidecar. Previously
    that ``os.open`` sat outside the loop, so such a transient error escaped as
    an *uncaught* exception instead of being retried (observed as a cross-process
    cap test worker exiting with no output). Persistent failure now surfaces as
    ``LedgerLockTimeout``, which callers already handle.
    """
    deadline = time.monotonic() + timeout_s

    fd: int | None = None
    while True:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
            break
        except OSError as exc:  # transient sharing/create race on Windows
            if time.monotonic() >= deadline:
                raise LedgerLockTimeout(
                    f"could not open ledger lock {lock_path} within {timeout_s}s: "
                    f"{exc!r}") from exc
            time.sleep(0.02)

    try:
        if os.name == "nt":  # pragma: no cover - exercised on Windows
            import msvcrt

            while True:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise LedgerLockTimeout(
                            f"could not acquire ledger lock {lock_path} within "
                            f"{timeout_s}s")
                    time.sleep(0.02)
            try:
                yield
            finally:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:  # pragma: no cover - best-effort unlock
                    pass
        else:  # pragma: no cover - POSIX path
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


def resolve_fieldnames(header_names: list[str]) -> list[str]:
    """Return the effective column names for reading an on-disk ledger.

    * exact match with ``COLUMNS`` -> use as-is;
    * a strict *prefix* of ``COLUMNS`` (a ledger written before later columns
      such as ``budget_scope`` existed) -> extend with the remaining canonical
      names, so a surplus field in a newer row is mapped instead of dropped and
      a legacy 20-field row falls back to phase scope;
    * anything else (unknown / extra / reordered / non-prefix columns) ->
      :class:`LedgerFormatError`, because guessing could silently lose a
      column and under-count a scoped budget.
    """
    if header_names == COLUMNS:
        return list(COLUMNS)
    k = len(header_names)
    if 0 < k < len(COLUMNS) and header_names == COLUMNS[:k]:
        return list(COLUMNS)
    raise LedgerFormatError(
        "ledger header is incompatible with this build; refusing to read it "
        "(reading it could drop or misalign columns). "
        f"on-disk={header_names!r}; expected an exact match or a prefix of "
        f"COLUMNS={COLUMNS!r}")


@dataclass(frozen=True)
class EpisodeKey:
    run_id: str
    anchor_id: str
    repetition: int
    condition: str

    def __str__(self) -> str:
        return f"{self.run_id}|{self.anchor_id}|r{self.repetition}|{self.condition}"


class EpisodeLedger:
    """Thread-safe append-only CSV ledger with phase budget accounting."""

    def __init__(self, ledger_path: str | Path) -> None:
        self.path = Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Shared process-wide lock (same CSV -> same lock) *and* a cross-process
        # OS lock. Billing decisions are made under both, after reconciling with
        # the durable CSV, so independent instances/processes cannot overspend.
        self._lock = _process_lock_for(self.path)
        self._lock_path = self.path.with_name(self.path.name + ".lock")
        self._listeners: list[Any] = []
        # in-memory accounting, kept in sync with the CSV. ``_consumed_bytes`` is
        # how much of the file we have already ingested, so the in-lock reconcile
        # only reads what other instances/processes appended since last time.
        self._fieldnames: list[str] | None = None
        self._consumed_bytes = 0
        self._reset_counters()
        with self._lock, _exclusive_file_lock(self._lock_path):
            if not self.path.exists() or self.path.stat().st_size == 0:
                # Header ONLY: an all-empty data row creates a phantom row that
                # breaks row counts and confuses downstream readers.
                self._write_header_unlocked()
        self._rebuild_counters()

    def _reset_counters(self) -> None:
        self._launched: dict[str, set[str]] = {p: set() for p in VALID_PHASES}
        self._scope_launched: dict[str, set[str]] = {}
        self._outcomed: dict[str, dict[str, set[str]]] = {
            p: {"completed": set(), "error": set(), "interrupted": set()} for p in VALID_PHASES
        }

    def _ingest_row(self, row: dict[str, str]) -> None:
        phase = row.get("phase", "")
        if phase not in self._launched:
            return
        if row.get("row_type") == "launch":
            self._launched[phase].add(row["episode_key"])
            # Legacy rows (pre budget_scope column) fall back to phase scope.
            scope = row.get("budget_scope") or phase
            self._scope_launched.setdefault(scope, set()).add(row["episode_key"])
        elif row.get("row_type") == "outcome":
            status = row.get("exit_status")
            if status in self._outcomed[phase]:
                self._outcomed[phase][status].add(row["episode_key"])

    def _resync_from_disk(self) -> None:
        """Incrementally ingest rows appended since the last read.

        Must be called while holding the process lock AND the file lock. Only
        complete lines are consumed (a trailing partial line is left for next
        time), and the run is idempotent because accounting uses sets. If the
        file shrank (rewritten by a foreign process) the counters are rebuilt
        from scratch.
        """
        if not self.path.exists():
            return
        try:
            size = self.path.stat().st_size
        except OSError:
            return
        if size < self._consumed_bytes:
            self._reset_counters()
            self._consumed_bytes = 0
            self._fieldnames = None
        if self._fieldnames is None:
            with open(self.path, "rb") as fh:
                head = fh.readline()
            if not head:
                return
            raw_names = next(csv.reader([head.decode("utf-8").rstrip("\r\n")]))
            # Validate + resolve once (raises LedgerFormatError on an
            # incompatible header instead of silently mis-reading columns). A
            # ledger created before the ``budget_scope`` column was added
            # carries a 20-column header while newly appended rows are 21 wide;
            # resolving the header to the full COLUMNS lets the surplus field
            # map onto ``budget_scope`` rather than being dropped on re-read
            # (otherwise a scoped formal budget degrades to phase level for any
            # fresh instance, e.g. a resumed run in a new process).
            self._fieldnames = resolve_fieldnames(raw_names)
            self._consumed_bytes = len(head)
        if size <= self._consumed_bytes:
            return
        with open(self.path, "rb") as fh:
            fh.seek(self._consumed_bytes)
            chunk = fh.read()
        nl = chunk.rfind(b"\n")
        if nl < 0:
            return  # only a partial line so far; wait for the newline
        complete = chunk[: nl + 1]
        names = self._fieldnames
        # Parse (and width-check) every line BEFORE advancing ``_consumed_bytes``
        # or mutating counters, so a rejected row leaves the reader untouched.
        parsed: list[dict[str, str]] = []
        for line in complete.decode("utf-8").splitlines():
            if not line.strip():
                continue
            fields = next(csv.reader([line]))
            if len(fields) > len(names):
                raise LedgerFormatError(
                    f"ledger row has {len(fields)} fields but the header "
                    f"declares {len(names)}; refusing to drop surplus fields. "
                    f"row={line[:120]!r}")
            parsed.append({n: (fields[i] if i < len(fields) else "")
                           for i, n in enumerate(names)})
        self._consumed_bytes += len(complete)
        for row in parsed:
            self._ingest_row(row)

    def _rebuild_counters(self) -> None:
        with self._lock, _exclusive_file_lock(self._lock_path):
            self._reset_counters()
            self._consumed_bytes = 0
            self._fieldnames = None
            self._resync_from_disk()

    # -- listeners (in-process cache sync) --------------------------------
    def add_listener(self, fn: Any) -> None:
        """Register fn(launch_row, outcome_row), called after each outcome."""
        self._listeners.append(fn)

    # -- low level --------------------------------------------------------
    def _write_header_unlocked(self) -> None:
        """Write the CSV header only. Caller must hold both locks."""
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
            writer.writeheader()
            fh.flush()
            os.fsync(fh.fileno())

    def _append_rows_unlocked(self, rows: Iterable[dict[str, Any]], header: bool = False) -> None:
        """Append rows. Caller must hold both the process and file locks."""
        with open(self.path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
            if header:
                writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in COLUMNS})
            fh.flush()
            os.fsync(fh.fileno())

    def _append_rows(self, rows: Iterable[dict[str, Any]], header: bool = False) -> None:
        with self._lock, _exclusive_file_lock(self._lock_path):
            # Reconcile with any rows another instance/process appended, then
            # write. Keeps our cache honest without a full re-read every time.
            self._resync_from_disk()
            self._append_rows_unlocked(rows, header=header)

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        with open(self.path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    # -- accounting -------------------------------------------------------
    def launched_count(self, phase: str) -> int:
        """Distinct episodes launched in a phase (launches consume budget)."""
        if phase not in VALID_PHASES:
            raise ValueError(f"unknown phase {phase!r}")
        return len(self._launched[phase])

    def launched_count_scope(self, scope: str) -> int:
        """Distinct episodes launched under an explicit budget scope.

        For formal this is ``"formal|method|master_seed"``; for smoke/pilot the
        scope equals the phase name (see ``reserve_launch``).
        """
        return len(self._scope_launched.get(scope, set()))

    def outcome_count(self, phase: str, exit_status: str | None = None) -> int:
        if phase not in VALID_PHASES:
            raise ValueError(f"unknown phase {phase!r}")
        if exit_status is None:
            return len(set().union(*self._outcomed[phase].values()))
        if exit_status not in self._outcomed[phase]:
            raise ValueError(f"unknown exit_status {exit_status!r}")
        return len(self._outcomed[phase][exit_status])

    # -- writing ----------------------------------------------------------
    def record_launch(self, key: EpisodeKey, *, run_id: str, phase: str, method: str,
                      master_seed: int, anchor_id: str, anchor_index: int,
                      repetition: int, condition: str, sim_seed: int,
                      stream: str = "discovery", budget_scope: str | None = None) -> dict[str, Any]:
        """Bill one episode launch. Returns the row written (pass it to
        ``record_outcome`` so outcome rows stay self-describing).

        Prefer ``reserve_launch`` for the real run path: it performs the budget
        check and the write atomically and rejects duplicate keys.
        """
        if phase not in VALID_PHASES:
            raise ValueError(f"unknown phase {phase!r}")
        if stream not in ("discovery", "audit"):
            raise ValueError(f"stream must be discovery/audit, got {stream!r}")
        row = {
            "row_type": "launch",
            "episode_key": str(key),
            "run_id": run_id,
            "phase": phase,
            "method": method,
            "master_seed": master_seed,
            "anchor_id": anchor_id,
            "anchor_index": anchor_index,
            "repetition": repetition,
            "condition": condition,
            "stream": stream,
            "sim_seed": sim_seed,
            "exit_status": "pending",
            "budget_scope": budget_scope or phase,
            "started_utc": utc_now_iso(),
        }
        with self._lock, _exclusive_file_lock(self._lock_path):
            self._resync_from_disk()
            self._append_rows_unlocked([row])
            self._launched[row["phase"]].add(row["episode_key"])
            self._scope_launched.setdefault(row["budget_scope"], set()).add(row["episode_key"])
        return row

    def reserve_launch(self, key: EpisodeKey, *, run_id: str, phase: str, method: str,
                       master_seed: int, anchor_id: str, anchor_index: int,
                       repetition: int, condition: str, sim_seed: int,
                       stream: str = "discovery", max_episodes: int | None = None,
                       budget_scope: str | None = None) -> dict[str, Any]:
        """Atomically check the budget AND bill one launch under the lock.

        ``check_budget`` + ``record_launch`` used to be two separate calls in the
        runner, so two threads/processes could both pass the check and both
        launch, bypassing the cap. This single locked step removes that window.

        * ``max_episodes`` bounds the ``budget_scope`` (phase by default, or
          ``phase|method|master_seed`` for formal so each seed is independent).
        * a launch whose ``episode_key`` is already billed in this scope is
          rejected *before* any simulator work (``DuplicateLaunch``). Force-reruns
          use a fresh run_id, hence a fresh key, and are billed again on purpose.
        """
        if phase not in VALID_PHASES:
            raise ValueError(f"unknown phase {phase!r}")
        if stream not in ("discovery", "audit"):
            raise ValueError(f"stream must be discovery/audit, got {stream!r}")
        scope = budget_scope or phase
        row = {
            "row_type": "launch",
            "episode_key": str(key),
            "run_id": run_id,
            "phase": phase,
            "method": method,
            "master_seed": master_seed,
            "anchor_id": anchor_id,
            "anchor_index": anchor_index,
            "repetition": repetition,
            "condition": condition,
            "stream": stream,
            "sim_seed": sim_seed,
            "exit_status": "pending",
            "budget_scope": scope,
            "started_utc": utc_now_iso(),
        }
        with self._lock, _exclusive_file_lock(self._lock_path):
            # Authoritative reconciliation BEFORE the decision: reflect every row
            # any *other* instance or process has already billed to this scope, so
            # the cap and the duplicate guard are evaluated against on-disk truth
            # rather than this instance's possibly-stale cache.
            self._resync_from_disk()
            scoped = self._scope_launched.setdefault(scope, set())
            if max_episodes is not None and len(scoped) >= max_episodes:
                raise BudgetExhausted(
                    f"budget scope {scope!r} exhausted: {len(scoped)}/{max_episodes} "
                    f"episodes already launched")
            ek = str(key)
            if ek in scoped:
                raise DuplicateLaunch(
                    f"episode_key {ek} already billed in scope {scope!r}; refusing to "
                    f"launch a duplicate before any simulator work")
            scoped.add(ek)
            self._launched[phase].add(ek)
            self._append_rows_unlocked([row])
        return row

    def empty_data_rows(self) -> int:
        """Count all-empty phantom data rows (legacy init wrote one).

        A fresh ledger (after the init fix) has zero; the pre-fix activity ledger
        carries one such row, which is harmless for counting but is reported here
        so independent verification can reconcile row counts.
        """
        return sum(1 for r in self._read_rows() if not r.get("episode_key") and not r.get("row_type"))

    def diagnose(self) -> dict[str, Any]:
        """Independent reconciliation of the durable CSV (read-only)."""
        rows = self._read_rows()
        return {
            "path": str(self.path),
            "total_rows": len(rows),
            "launch_rows": sum(1 for r in rows if r.get("row_type") == "launch"),
            "outcome_rows": sum(1 for r in rows if r.get("row_type") == "outcome"),
            "empty_data_rows": self.empty_data_rows(),
            "launched_by_phase": {p: len(self._launched[p]) for p in VALID_PHASES},
        }

    def record_outcome(self, key: EpisodeKey, *, launch_row: dict[str, Any],
                       exit_status: str, ego_collision: int | None,
                       termination: str = "", error_type: str = "",
                       wall_time_s: float | None = None,
                       raw_path: str = "") -> None:
        if exit_status not in ("completed", "error", "interrupted"):
            raise ValueError(f"invalid exit_status {exit_status!r}")
        if ego_collision is not None and ego_collision not in (0, 1):
            raise ValueError(f"ego_collision must be 0/1/None, got {ego_collision!r}")
        if exit_status == "completed" and ego_collision is None:
            raise ValueError("a completed episode must record ego_collision 0 or 1")
        row = {
            "row_type": "outcome",
            "episode_key": str(key),
            "run_id": launch_row.get("run_id", ""),
            "phase": launch_row.get("phase", ""),
            "method": launch_row.get("method", ""),
            "master_seed": launch_row.get("master_seed", ""),
            "anchor_id": launch_row.get("anchor_id", ""),
            "anchor_index": launch_row.get("anchor_index", ""),
            "repetition": launch_row.get("repetition", ""),
            "condition": launch_row.get("condition", ""),
            "stream": launch_row.get("stream", ""),
            "sim_seed": launch_row.get("sim_seed", ""),
            "exit_status": exit_status,
            "ego_collision": "" if ego_collision is None else ego_collision,
            "termination": termination,
            "error_type": error_type,
            "ended_utc": utc_now_iso(),
            "wall_time_s": "" if wall_time_s is None else round(float(wall_time_s), 6),
            "raw_path": raw_path,
        }
        with self._lock, _exclusive_file_lock(self._lock_path):
            self._resync_from_disk()
            self._append_rows_unlocked([row])
            phase = row["phase"]
            if phase in self._outcomed:
                self._outcomed[phase][row["exit_status"]].add(row["episode_key"])
        for fn in self._listeners:
            fn(launch_row, row)

    def check_budget(self, phase: str, max_episodes: int) -> None:
        used = self.launched_count(phase)
        if used >= max_episodes:
            raise BudgetExhausted(
                f"phase {phase!r} budget exhausted: {used}/{max_episodes} episodes already launched"
            )
