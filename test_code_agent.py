"""
Test script for Code Agent integration
Tests the hybrid agent system with sample questions
"""

import asyncio
from edisonpro_ui import EdisonProUI

async def test_code_agent():
    """Test code agent with sample questions"""
    print("=== Testing Code Agent Integration ===\n")
    
    # Initialize the app
    app = EdisonProUI()
    app.initialize()
    
    if not app.initialized:
        print("❌ App initialization failed")
        return
    
    print(f"✅ App initialized")
    print(f"Code Agent available: {app.code_agent.available if app.code_agent else False}\n")
    
    # Test questions
    test_questions = [
        {
            "question": "Show me all transformers as a table",
            "expected_agent": "Code Agent",
            "description": "Data transformation - should use Code Agent"
        },
        {
            "question": "What is the voltage rating of transformer T-101?",
            "expected_agent": "o3-pro",
            "description": "Understanding question - should use o3-pro"
        },
        {
            "question": "Calculate the total power load across all circuits",
            "expected_agent": "Code Agent",
            "description": "Calculation - should use Code Agent"
        },
        {
            "question": "Why is this circuit breaker rated at 100A?",
            "expected_agent": "o3-pro",
            "description": "Engineering reasoning - should use o3-pro"
        }
    ]
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {test['description']}")
        print(f"Question: {test['question']}")
        print(f"Expected: {test['expected_agent']}")
        print('-'*70)
        
        # Check detection
        if app.code_agent:
            should_use_code = app.code_agent.should_use_code_agent(test['question'])
            detected_agent = "Code Agent" if should_use_code else "o3-pro"
            print(f"Detected: {detected_agent}")
            
            if detected_agent == test['expected_agent']:
                print("✅ Detection correct")
            else:
                print(f"⚠️ Detection mismatch: expected {test['expected_agent']}, got {detected_agent}")
        
        # Get response
        try:
            answer, table_html, download_html = await app.ask_question_async(test['question'], [])
            
            print(f"\nAnswer preview: {answer[:200]}...")
            
            if table_html:
                print(f"✅ Table generated ({len(table_html)} chars)")
            
            if download_html:
                print(f"✅ Download links generated ({len(download_html)} chars)")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print(f"\n{'='*70}")
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_code_agent())
