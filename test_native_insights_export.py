import unittest

from edisonpro import DiagramAnalysisOrchestratorPro


class NativeInsightsExportTests(unittest.TestCase):
    def test_build_public_native_insights_trims_and_preserves_key_fields(self) -> None:
        orchestrator = object.__new__(DiagramAnalysisOrchestratorPro)
        orchestrator.insight_summary = {
            "backend": "rust-native",
            "measurement_frequency": [["480V", 3], ["125 psi", 2]],
            "standard_frequency": [["IEEE 1584", 2]],
            "tag_frequency": [["MCC-101", 2]],
            "sheet_correlation_hints": [{"sheet_id": "sheet_a"}, {"sheet_id": "sheet_b"}],
            "cross_sheet_graph": {
                "edges": [{"from_sheet_id": "sheet_a", "to_sheet_id": "sheet_b", "weight": 6}],
                "connector_hubs": [{"signal": "P-201", "kind": "reference", "sheet_count": 2}],
                "summary_lines": ["sheet_a <-> sheet_b via refs P-201"],
            },
            "anomaly_detection": {
                "has_anomalies": True,
                "risk_score": 0.75,
                "anomaly_count": 2,
                "severity_counts": {"critical": 1, "high": 1},
                "top_failure_types": [["grounding_violation", 1], ["interlock_missing", 1]],
                "anomalies": [{
                    "chunk_id": "chunk_001",
                    "sheet_id": "sheet_a",
                    "domain": "electrical",
                    "failure_type": "grounding_violation",
                    "severity": "critical",
                    "signals": ["MCC-101", "480V"],
                    "confidence": 0.88,
                    "recommendation": "ignored in public export",
                }],
                "summary_lines": ["Rule-based anomaly scan flagged 2 candidate(s) with risk score 0.75."],
            },
            "chunk_summaries": [{"chunk_id": "chunk_001"}],
        }

        exported = DiagramAnalysisOrchestratorPro._build_public_native_insights(orchestrator)

        self.assertEqual(exported.get("backend"), "rust-native")
        self.assertEqual(exported.get("measurement_frequency"), [["480V", 3], ["125 psi", 2]])
        self.assertEqual(exported.get("cross_sheet_graph", {}).get("edges", [])[0]["from_sheet_id"], "sheet_a")
        self.assertTrue(exported.get("anomaly_detection", {}).get("has_anomalies"))
        self.assertEqual(exported.get("anomaly_detection", {}).get("anomalies", [])[0]["sheet_id"], "sheet_a")
        self.assertNotIn("recommendation", exported.get("anomaly_detection", {}).get("anomalies", [])[0])
        self.assertNotIn("chunk_summaries", exported)


if __name__ == "__main__":
    unittest.main()