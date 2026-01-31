"""
Phase 3 API Testing Script
Tests feedback recording, analytics retrieval, and visualization generation
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_api_status():
    """Test Phase 3 feature availability"""
    print("=" * 70)
    print("1. Testing API Status")
    print("=" * 70)
    
    try:
        response = requests.get(f"{API_BASE}/innovative-features/status")
        data = response.json()
        
        print("✅ API Status Retrieved")
        print(f"\nPhase 1 Features: {data['features']['phase_1']}")
        print(f"Phase 2 Features: {data['features']['phase_2']}")
        print(f"Phase 3 Features: {data['features']['phase_3']}")
        
        return data['features']['phase_3']['feedback_tracking']
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_feedback_recording():
    """Test feedback recording endpoint"""
    print("\n" + "=" * 70)
    print("2. Testing Feedback Recording")
    print("=" * 70)
    
    try:
        feedback_data = {
            "feature_type": "query_suggestion",
            "diagram_id": "test_diagram_123",
            "domain": "electrical",
            "feedback_type": "helpful",
            "context": {"test": "data"},
            "user_id": "test_user"
        }
        
        response = requests.post(f"{API_BASE}/feedback", json=feedback_data)
        result = response.json()
        
        print("✅ Feedback Recorded")
        print(f"   Event ID: {result['event_id']}")
        print(f"   Message: {result['message']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_analytics_retrieval():
    """Test analytics endpoint"""
    print("\n" + "=" * 70)
    print("3. Testing Analytics Retrieval")
    print("=" * 70)
    
    try:
        # Get analytics for all features
        response = requests.get(f"{API_BASE}/analytics")
        data = response.json()
        
        print("✅ Analytics Retrieved")
        print(f"\nFeature Statistics:")
        for feature, stats in data['feature_stats'].items():
            if stats:
                print(f"\n   {feature}:")
                print(f"      Total Uses: {stats.get('total_uses', 0)}")
                print(f"      Success Rate: {stats.get('successful_uses', 0)}/{stats.get('total_uses', 0)}")
        
        if data.get('report'):
            print(f"\n📊 Analytics Report Preview:")
            print(data['report'][:500] + "...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_visualization():
    """Test visualization generation"""
    print("\n" + "=" * 70)
    print("4. Testing Visualization Generation")
    print("=" * 70)
    
    try:
        # Test risk gauge
        viz_data = {
            "visualization_type": "risk_gauge",
            "data": {
                "risk_score": 0.75,
                "title": "Test Risk Assessment"
            }
        }
        
        response = requests.post(f"{API_BASE}/visualize", json=viz_data)
        result = response.json()
        
        print("✅ Visualization Generated")
        print(f"   Chart ID: {result['chart_id']}")
        print(f"   HTML Length: {len(result['html'])} characters")
        
        # Save to file for inspection
        output_file = f"test_visualization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['html'])
        
        print(f"   Saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_report_generation():
    """Test report generation (requires mock data)"""
    print("\n" + "=" * 70)
    print("5. Testing Report Generation")
    print("=" * 70)
    
    try:
        report_data = {
            "report_type": "anomaly",
            "result": {
                "risk_score": 0.65,
                "confidence": 0.82,
                "anomalies": [
                    {
                        "pattern_name": "Overcurrent Protection Gap",
                        "similarity": 0.85,
                        "risk_level": "high",
                        "description": "Missing overcurrent protection on secondary side"
                    }
                ],
                "recommendations": [
                    "Add circuit breaker CB-102 on 480V secondary",
                    "Verify breaker coordination study",
                    "Update protection relay settings"
                ],
                "prevention_cost_estimate": 5000,
                "failure_cost_estimate": 150000
            },
            "diagram_path": "/test/diagram.png",
            "domain": "electrical"
        }
        
        response = requests.post(f"{API_BASE}/generate-report", json=report_data)
        
        if response.status_code == 200:
            # Save report
            output_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print("✅ Report Generated")
            print(f"   Saved to: {output_file}")
            print(f"   Size: {len(response.content)} bytes")
            
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all Phase 3 API tests"""
    print("\n" + "=" * 70)
    print("EDISON PRO - Phase 3 API Testing Suite")
    print("=" * 70)
    print(f"API Base URL: {API_BASE}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    results = []
    
    # Test 1: API Status
    results.append(("API Status", test_api_status()))
    
    if not results[0][1]:
        print("\n⚠️  API not available. Is the server running?")
        print("Start server with: python api.py")
        return
    
    # Test 2: Feedback Recording
    results.append(("Feedback Recording", test_feedback_recording()))
    
    # Test 3: Analytics
    results.append(("Analytics Retrieval", test_analytics_retrieval()))
    
    # Test 4: Visualization
    results.append(("Visualization", test_visualization()))
    
    # Test 5: Report Generation
    results.append(("Report Generation", test_report_generation()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 3 APIs working correctly!")
    else:
        print("\n⚠️  Some tests failed. Check error messages above.")


if __name__ == "__main__":
    main()
