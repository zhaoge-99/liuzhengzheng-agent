import threading
import time
import unittest

from agent.Concurrency import AgentAdmission, AdmissionRejected


class AgentAdmissionTest(unittest.TestCase):
    def test_capacity_rejects_when_queue_timeout_expires(self) -> None:
        admission = AgentAdmission(max_concurrent=1, queue_timeout=0)
        first = admission.acquire("first")
        try:
            with self.assertRaises(AdmissionRejected):
                admission.acquire("second")
            self.assertEqual(admission.stats()["active"], 1)
            self.assertEqual(admission.stats()["rejected"], 1)
        finally:
            admission.release()

        self.assertEqual(admission.stats()["active"], 0)
        self.assertEqual(admission.stats()["available"], 1)

    def test_waiting_request_enters_after_slot_is_released(self) -> None:
        admission = AgentAdmission(max_concurrent=1, queue_timeout=1)
        first = admission.acquire("first")
        result: list[str] = []

        def worker() -> None:
            lease = admission.acquire("second")
            result.append(lease.request_id)
            admission.release()

        thread = threading.Thread(target=worker)
        thread.start()
        time.sleep(0.03)
        admission.release()
        thread.join(timeout=1)

        self.assertEqual(result, ["second"])
        self.assertEqual(admission.stats()["active"], 0)

    def test_release_cannot_be_called_without_active_slot(self) -> None:
        admission = AgentAdmission(max_concurrent=1)
        with self.assertRaises(RuntimeError):
            admission.release()

