import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import app


class _FakeOrchestrator:
    def process_upload_batch(self, saved_paths):
        return {
            "status": "success",
            "input_type": "image_batch",
            "chunks": 4,
            "images_processed": len(saved_paths),
            "visual_elements": 9,
            "native_insights": {
                "backend": "rust-native",
                "cross_sheet_graph": {
                    "summary_lines": ["sheet_a <-> sheet_b via refs P-201"],
                },
                "anomaly_detection": {
                    "has_anomalies": True,
                    "risk_score": 0.5,
                },
            },
        }


class UploadApiNativeInsightsTests(unittest.TestCase):
    def test_upload_returns_native_insights(self) -> None:
        client = TestClient(app)

        with patch("api.get_orchestrator", return_value=_FakeOrchestrator()):
            response = client.post(
                "/upload",
                files=[
                    ("files", ("sheet_a.png", b"fake-image-a", "image/png")),
                    ("files", ("sheet_b.png", b"fake-image-b", "image/png")),
                ],
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("images_processed"), 2)
        self.assertEqual(payload.get("native_insights", {}).get("backend"), "rust-native")
        self.assertTrue(payload.get("native_insights", {}).get("anomaly_detection", {}).get("has_anomalies"))


if __name__ == "__main__":
    unittest.main()