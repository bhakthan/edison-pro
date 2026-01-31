"""
Test script for Flickering Cognitive Architecture
Tests the complete system with confidence evaluation
"""

import sys
import json
from agents import FlickeringSystem

def test_flickering_system():
    """Test flickering analysis with confidence metrics"""
    
    print("="*70)
    print("FLICKERING COGNITIVE ARCHITECTURE - TEST SCRIPT")
    print("="*70)
    print()
    
    # Initialize system
    print("1. Initializing FlickeringSystem...")
    system = FlickeringSystem(
        storage_path="./memory_atlas",
        theta_frequency=8.0,
        mismatch_threshold=0.3,
        enable_background_simulation=False  # Disable for testing
    )
    print()
    
    # Test with sample diagram
    print("2. Running analysis on sample diagram...")
    diagram_path = "./input/image1.png"
    
    try:
        results = system.analyze(
            diagram=diagram_path,
            num_cycles=50,  # Reduced for faster testing
            domain="electrical",
            theta_frequency=8.0,
            return_trace=True,
            generate_alternatives=True
        )
        
        print("\n" + "="*70)
        print("ANALYSIS RESULTS")
        print("="*70)
        
        # Print interpretation
        interpretation = results.get('interpretation', {})
        print(f"\n📊 Interpretation:")
        print(f"   Status: {interpretation.get('status', 'N/A')}")
        print(f"   Confidence: {interpretation.get('confidence', 0):.1%}")
        print(f"   Components: {len(interpretation.get('components', []))}")
        
        # Print mismatch events
        mismatch_events = results.get('mismatch_events', [])
        print(f"\n⚡ Mismatch Events: {len(mismatch_events)}")
        for i, event in enumerate(mismatch_events[:3], 1):  # Show first 3
            print(f"   {i}. Cycle {event.get('cycle')}: "
                  f"Δ={event.get('mismatch_delta', 0):.3f} "
                  f"({event.get('novelty_level', 'N/A')})")
        
        # Print alternatives
        alternatives = results.get('alternatives', [])
        print(f"\n🌳 Alternative Hypotheses: {len(alternatives)}")
        for i, alt in enumerate(alternatives[:3], 1):  # Show first 3
            print(f"   {i}. {alt.get('interpretation', 'N/A')[:50]}... "
                  f"(Score: {alt.get('score', 0):.3f})")
        
        # Print confidence metrics (KEY NEW FEATURE)
        confidence = results.get('confidence', {})
        print(f"\n🎯 CONFIDENCE EVALUATION:")
        print(f"   Overall Confidence: {confidence.get('overall', 0):.1%}")
        print(f"   Bottleneck: {confidence.get('bottleneck', 'None')}")
        
        uncertainty = confidence.get('uncertainty', {})
        print(f"\n   Uncertainty Breakdown:")
        print(f"      Aleatoric (data noise): {uncertainty.get('aleatoric', 0):.1%}")
        print(f"      Epistemic (knowledge gap): {uncertainty.get('epistemic', 0):.1%}")
        print(f"      Total: {uncertainty.get('total', 0):.1%}")
        
        step_confidences = confidence.get('step_confidences', [])
        if step_confidences:
            print(f"\n   Step-by-Step Confidences:")
            for i, conf in enumerate(step_confidences, 1):
                print(f"      Step {i}: {conf:.1%}")
        
        # Print system info
        system_info = results.get('system_info', {})
        print(f"\n📈 System Info:")
        print(f"   Theta Frequency: {system_info.get('theta_frequency', 0)} Hz")
        print(f"   Memory Patterns: {system_info.get('memory_patterns', 0)}")
        print(f"   Total Latency: {system_info.get('total_latency_ms', 0)} ms")
        
        # Save detailed results
        output_file = "test_flickering_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Full results saved to: {output_file}")
        print("\n" + "="*70)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*70)
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find image at {diagram_path}")
        print("   Please ensure image1.png exists in ./input/ directory")
        return False
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        system.shutdown()


if __name__ == "__main__":
    success = test_flickering_system()
    sys.exit(0 if success else 1)
