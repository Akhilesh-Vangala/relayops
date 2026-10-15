import copy
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from relayops.web import create_app, SCENARIOS


class PublicDemoTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                "RELAY_PUBLIC_SHOWCASE": "1",
                "RELAY_PUBLIC_DEMO": "1",
                "RELAY_DEMO_SECRET": "local-test-secret-" + "x" * 64,
            },
        )
        self.env.start()
        self.app = create_app(self.directory.name)
        self.client = TestClient(self.app, base_url="https://demo.example")
        self.client.__enter__()
        response = self.client.get("/api/demo/config")
        self.assertFalse(response.json()["live_model"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.env.stop()
        self.directory.cleanup()

    def start(self, case="short-shipment"):
        r = self.client.post("/api/demo/investigate", json={"case_id": case})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def approve(self, result):
        r = self.client.post(
            "/api/demo/review", json={"token": result["token"], "action": "approve"}
        )
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_actual_review_execution_and_same_request_idempotency(self):
        assessed = self.start()
        self.assertTrue(assessed["simulation"]["passed"])
        self.assertEqual(assessed["before"], assessed["after"])
        self.assertEqual(
            set(assessed["plan"]["evidence_ids"]),
            {e["evidence_id"] for e in assessed["evidence"]},
        )
        blocked = self.client.post(
            "/api/demo/execute", json={"token": assessed["token"]}
        )
        self.assertEqual(blocked.status_code, 409)
        approved = self.approve(assessed)
        r = self.client.post("/api/demo/execute", json={"token": approved["token"]})
        self.assertEqual(r.status_code, 200, r.text)
        final = r.json()
        self.assertTrue(final["execution"]["passed"])
        self.assertTrue(final["execution"]["same_request_retry_no_duplicates"])
        self.assertEqual(final["after"]["billing"]["held_cents"], 50000)
        self.assertEqual(final["after"]["case_management"]["reserved_units"], 20)
        self.assertEqual(len(final["receipts"]), 4)
        self.assertEqual(
            set(final["plan"]["evidence_ids"]),
            {e["evidence_id"] for e in final["evidence"]},
        )

    def test_lost_acknowledgment_reconciles_before_continuing(self):
        approved = self.approve(self.start())
        r = self.client.post(
            "/api/demo/execute",
            json={"token": approved["token"], "failure_mode": "acknowledgment_loss"},
        )
        uncertain = r.json()
        self.assertEqual(uncertain["stage"], "uncertain")
        self.assertEqual(uncertain["receipts"][0]["status"], "unknown")
        self.assertEqual(uncertain["after"]["case_management"]["status"], "open")
        self.assertEqual(
            self.client.post(
                "/api/demo/execute", json={"token": uncertain["token"]}
            ).status_code,
            409,
        )
        r = self.client.post("/api/demo/reconcile", json={"token": uncertain["token"]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["execution"]["passed"])
        self.assertEqual(r.json()["execution"]["reconciled_receipts"], 1)
        self.assertTrue(all(r["status"] == "confirmed" for r in r.json()["receipts"]))

    def test_unresolved_and_healthy_cases_make_no_changes(self):
        for name, outcome in (
            ("unknown-delivery", "needs_information"),
            ("low-stock", "needs_information"),
            ("healthy-delivery", "no_change"),
        ):
            with self.subTest(case=name):
                result = self.start(name)
                self.assertEqual(result["plan"]["outcome"], outcome)
                self.assertTrue(result["simulation"]["passed"])
                self.assertEqual(result["plan"]["actions"], [])
                self.assertEqual(result["before"], result["after"])
                self.assertEqual(
                    self.client.post(
                        "/api/demo/review",
                        json={"token": result["token"], "action": "approve"},
                    ).status_code,
                    409,
                )

    def test_rejection_cannot_execute_or_change_its_own_branch(self):
        r = self.client.post(
            "/api/demo/review",
            json={"token": self.start()["token"], "action": "reject"},
        )
        rejected = r.json()
        self.assertEqual(rejected["stage"], "rejected")
        self.assertEqual(
            self.client.post(
                "/api/demo/execute", json={"token": rejected["token"]}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                "/api/demo/review",
                json={"token": rejected["token"], "action": "approve"},
            ).status_code,
            409,
        )

    def test_signed_state_tampering_other_visitors_and_expiry(self):
        result = self.start()
        token = result["token"]
        changed = token[:-1] + ("1" if token[-1] != "1" else "2")
        self.assertEqual(
            self.client.post(
                "/api/demo/review", json={"token": changed, "action": "approve"}
            ).status_code,
            409,
        )
        with TestClient(self.app, base_url="https://demo.example") as other:
            other.get("/api/demo/config")
            self.assertEqual(
                other.post(
                    "/api/demo/review", json={"token": token, "action": "approve"}
                ).status_code,
                403,
            )
        with patch("relayops.demo_security.time.time", return_value=9999999999):
            self.assertEqual(
                self.client.post(
                    "/api/demo/review", json={"token": token, "action": "approve"}
                ).status_code,
                409,
            )

    def test_source_changes_invalidate_old_approval_scope(self):
        result = self.start()
        altered = copy.deepcopy(SCENARIOS["short-shipment"])
        altered[2]["received"] = 79
        with patch.dict(SCENARIOS, {"short-shipment": altered}):
            r = self.client.post(
                "/api/demo/review", json={"token": result["token"], "action": "approve"}
            )
        self.assertEqual(r.status_code, 409)

    def test_private_writes_live_inputs_and_shared_history_stay_unavailable(self):
        self.assertEqual(self.client.post("/api/runs", json={}).status_code, 405)
        self.assertEqual(
            self.client.post(
                "/api/demo/investigate",
                json={"case_id": "short-shipment", "mode": "live"},
            ).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/demo/investigate",
                json={"case_id": "short-shipment"},
                headers={"Origin": "https://untrusted.example"},
            ).status_code,
            403,
        )
        result = self.start()
        self.assertEqual(self.client.get("/api/demo/runs").json(), [])
        self.assertEqual(
            self.client.get("/api/demo/runs/" + result["id"]).status_code, 404
        )
        self.assertEqual(self.client.get("/").url.path, "/demo")
