"""Real uploaded quantities, multi-case stock conservation and exact-source approval."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from relayops.uploads.api import attach
from relayops.uploads.ingestion import Upload
from relayops.uploads.service import run


class CustomerUploadTests(unittest.TestCase):
    def upload(self, csv=None):
        return Upload(csv=csv or "id,ordered,received,invoiced,stock,price,confirmed,pool\nA,10,7,10,5,1.25,true,P\nB,10,7,10,5,1.25,true,P\nC,2,2,2,0,8.00,true,Q\n",
            mapping=dict(zip(("order_id", "ordered", "received", "invoiced", "available", "unit_price", "confirmed", "pool"), (f"c{i}" for i in range(8)))), options={"unit": "dollars"})

    def test_actual_langgraph_plans_and_shared_pool_prevent_oversubscription(self):
        result = run(self.upload())
        self.assertEqual([r["plan"]["outcome"] for r in result["results"]], ["resolve", "needs_information", "no_change"])
        self.assertEqual(result["inventory_remaining"]["P"], 2)
        self.assertEqual(result["results"][0]["plan"]["actions"][0]["amount"], 375)
        self.assertIn("policy-validated", result["results"][0]["activity"])
        self.assertIsNone(result["csv"])

    def test_reviewed_export_has_actual_checked_effect_receipts(self):
        result = run(self.upload(), approved=True)
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(len(result["results"][0]["receipts"]), 4)
        self.assertEqual(result["results"][1]["receipts"], [])
        self.assertIn("A,resolve,375,3,3,resolved", result["csv"])

    def test_new_customer_values_change_plans(self):
        upload = self.upload(self.upload().csv.replace("A,10,7,10,5,1.25", "A,10,9,10,5,2.50"))
        self.assertEqual(run(upload)["results"][0]["plan"]["actions"][0]["amount"], 250)

    def test_ambiguous_source_and_policy_limits_refuse(self):
        for source in (self.upload().csv.replace("B,10,7,10,5", "B,10,7,10,6"),
                       self.upload().csv.replace("A,10,7", "A,10,11"),
                       self.upload().csv.replace("1.25,true", "1.25,maybe"),
                       self.upload().csv.replace("B,10,7", "A,10,7")):
            with self.assertRaises(ValueError):
                run(self.upload(source))

    def test_unconfirmed_delivery_is_not_acted_on(self):
        result = run(self.upload(self.upload().csv.replace("true", "false")), approved=True)
        self.assertTrue(all(not r["receipts"] for r in result["results"]))

    def test_signed_review_is_browser_bound_source_bound_and_tamper_resistant(self):
        app = FastAPI()
        with patch.dict(os.environ, {"RELAY_DEMO_SECRET": "upload-test-"+"x"*64}):
            attach(app, "RelayOps", Path(__file__).resolve().parents[3])
        with TestClient(app, base_url="https://upload.test") as first, TestClient(app, base_url="https://upload.test") as second:
            first.get("/api/uploads/capabilities"); second.get("/api/uploads/capabilities")
            payload = self.upload().model_dump()
            response = first.post("/api/uploads/analyze", json=payload)
            self.assertEqual(response.status_code, 200, response.text)
            token = response.json()["review"]
            payload["review"] = token
            self.assertEqual(second.post("/api/uploads/approve", json=payload).status_code, 403)
            changed = dict(payload, csv=payload["csv"].replace("1.25", "2.50"))
            self.assertEqual(first.post("/api/uploads/approve", json=changed).status_code, 409)
            self.assertEqual(first.post("/api/uploads/approve", json=dict(payload, review=token[:-1]+("a" if token[-1] != "a" else "b"))).status_code, 409)
            result = first.post("/api/uploads/approve", json=payload)
            self.assertEqual(result.status_code, 200, result.text)
            self.assertTrue(result.json()["summary"]["approved_export"])
            self.assertEqual(first.post("/api/uploads/approve", json=payload).json()["csv"], result.json()["csv"])
