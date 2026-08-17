from __future__ import annotations

import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.task_runtime_store import TaskRuntimeStore


CONCURRENT_STORE_TEST_TIMEOUT_SECONDS = 300.0


@dataclass
class Item:
    email: str
    name: str = ""
    status: str = "pending"
    attempts: int = 0
    message: str = ""
    result: str = ""


class TaskRuntimeStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TaskRuntimeStore(Path(self.tmp.name) / "runtime.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_one_recipient_one_latest_result_and_recovery(self):
        items = [Item("a@example.com"), Item("b@example.com")]
        run_id = self.store.start_run(
            slot_id=1,
            target_url="https://example.test/",
            source_file="input.txt",
            source_fingerprint="abc",
            items=items,
            created_at="2026-08-08 22:00:00",
        )
        self.store.upsert_result(
            run_id,
            0,
            {
                "timestamp": "2026-08-08 22:00:01",
                "slot_id": 1,
                "email": "a@example.com",
                "status": "processing",
                "message": "start",
                "attempts": 1,
                "target_url": "https://example.test/",
                "result": "",
            },
        )
        self.store.upsert_result(
            run_id,
            0,
            {
                "timestamp": "2026-08-08 22:00:02",
                "slot_id": 1,
                "email": "a@example.com",
                "status": "success",
                "message": "confirmed",
                "attempts": 1,
                "target_url": "https://example.test/",
                "result": "sent",
            },
        )
        rows = self.store.results(limit=None)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "success")

        self.store.save_progress(
            run_id=run_id,
            current_index=1,
            total=2,
            success_count=1,
            failed_count=0,
            send_limit_used=1,
            task_status="Stopped",
            manual_review_required=False,
            updated_at="2026-08-08 22:00:03",
            target_url="https://example.test/changed",
        )
        recovered = self.store.load_run(run_id)
        self.assertEqual(recovered["current_index"], 1)
        self.assertEqual(recovered["send_limit_used"], 1)
        self.assertEqual(recovered["target_url"], "https://example.test/changed")
        self.assertTrue(any(row["run_id"] == run_id for row in self.store.recoverable_runs()))


    def test_four_worker_threads_persist_independent_results_without_cross_run_leak(self):
        # This is a correctness/isolation stress test, not a storage-throughput
        # SLA. Hosted Windows runner I/O can spend well over one minute flushing
        # FULL-synchronous WAL transactions while the finite writer workload is
        # still making forward progress. Keep a bounded five-minute deadlock guard
        # without turning normal durable-I/O variance into a CI product failure.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            store = TaskRuntimeStore(Path(temp) / "store.sqlite3")
            run_ids = []
            count_per_run = 100
            for slot in range(1, 5):
                items = [Item(f"s{slot}-{i}@example.com") for i in range(count_per_run)]
                run_ids.append(
                    store.start_run(
                        slot_id=slot, target_url="https://example.test", source_file=f"{slot}.txt",
                        source_fingerprint=str(slot), items=items, created_at=f"t{slot}"
                    )
                )
            errors = []

            def writer(slot, run_id):
                try:
                    for index in range(count_per_run):
                        item = Item(f"s{slot}-{index}@example.com", status="success", attempts=1, result="sent")
                        store.persist_item_result_progress(
                            run_id=run_id,
                            item_index=index,
                            item=item,
                            result_row={
                                "timestamp": f"{slot:02d}-{index:04d}",
                                "slot_id": slot,
                                "email": item.email,
                                "status": "success",
                                "message": "ok",
                                "attempts": 1,
                                "target_url": "https://example.test",
                                "result": "sent",
                            },
                            current_index=index + 1,
                            total=count_per_run,
                            success_count=index + 1,
                            failed_count=0,
                            send_limit_used=index + 1,
                            task_status="Running",
                            manual_review_required=False,
                            updated_at=f"u{index}",
                        )
                except BaseException as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=writer, args=(slot, run_id))
                for slot, run_id in enumerate(run_ids, start=1)
            ]
            for thread in threads:
                thread.start()

            deadline = time.monotonic() + CONCURRENT_STORE_TEST_TIMEOUT_SECONDS
            for thread in threads:
                remaining = max(0.0, deadline - time.monotonic())
                thread.join(timeout=remaining)

            alive = [thread for thread in threads if thread.is_alive()]
            self.assertFalse(
                alive,
                "concurrent runtime-store writers did not finish within "
                f"{CONCURRENT_STORE_TEST_TIMEOUT_SECONDS:.0f}s",
            )
            self.assertEqual(errors, [])
            self.assertEqual(len(store.results(limit=None)), 4 * count_per_run)
            for slot in range(1, 5):
                rows = store.results(slot_id=slot, limit=None)
                self.assertEqual(len(rows), count_per_run)
                self.assertTrue(all(row["email"].startswith(f"s{slot}-") for row in rows))

    def test_manual_review_skip_never_retries_current_recipient(self):
        item = Item(
            "ambiguous@example.com",
            status="interrupted",
            attempts=1,
            message="Send clicked but outcome unknown",
        )
        run_id = self.store.start_run(
            slot_id=2,
            target_url="https://example.test/",
            source_file="input.txt",
            source_fingerprint="def",
            items=[item, Item("next@example.com")],
            created_at="2026-08-08 22:00:00",
        )
        self.store.save_item(run_id, 0, item)
        self.store.save_progress(
            run_id=run_id,
            current_index=0,
            total=2,
            success_count=0,
            failed_count=0,
            send_limit_used=1,
            task_status="Interrupted",
            manual_review_required=True,
            updated_at="2026-08-08 22:00:01",
        )
        self.store.skip_current_manual_review(run_id, "2026-08-08 22:00:02")
        run = self.store.load_run(run_id)
        self.assertEqual(run["current_index"], 1)
        self.assertEqual(run["manual_review_required"], 0)
        self.assertEqual(run["items"][0]["status"], "interrupted")
        self.assertIn("without automatic retry", run["items"][0]["message"])


if __name__ == "__main__":
    unittest.main()
