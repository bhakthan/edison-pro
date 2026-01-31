"""
Quick script to generate comprehensive HTML results page
from current analysis outputs in the 'out' directory
"""

import os
import glob
import webbrowser
from pathlib import Path
from results_generator import generate_results_page


def main():
    """Generate results page from current analysis outputs"""
    
    print("🔍 Scanning for analysis outputs...")
    
    # Collect all files from out directory
    out_dir = Path("out")
    if not out_dir.exists():
        print("❌ No 'out' directory found. Run some analysis first!")
        return
    
    all_files = [str(f) for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('analysis_results')]
    
    if not all_files:
        print("❌ No analysis files found in 'out' directory")
        return
    
    print(f"✓ Found {len(all_files)} files:")
    for f in all_files:
        print(f"  - {os.path.basename(f)}")
    
    # Create dummy conversation history from file names (for demonstration)
    # In real usage, this would come from the actual Q&A session
    conversation_history = [
        ("What components are in the diagram?", "Analysis complete. See generated files for details."),
        ("Show me the load distribution", "Load distribution chart has been generated."),
        ("Export all components to CSV", "Components exported to engineering_diagram_components.csv"),
    ]
    
    print("\n📊 Generating comprehensive results page...")
    
    # Summary stats
    csv_files = [f for f in all_files if f.endswith('.csv')]
    html_files = [f for f in all_files if f.endswith('.html') and 'analysis_results' not in f]
    
    summary = {
        'total_files': len(all_files),
        'csv_exports': len(csv_files),
        'visualizations': len(html_files),
        'total_questions': len(conversation_history)
    }
    
    # Generate the results page
    results_path = generate_results_page(
        conversation_history=conversation_history,
        generated_files=all_files,
        analysis_summary=summary
    )
    
    print(f"\n✅ Results page generated successfully!")
    print(f"📄 Location: {os.path.abspath(results_path)}")
    
    # Open in browser
    print("\n🌐 Opening results page in browser...")
    webbrowser.open(f"file:///{os.path.abspath(results_path)}")
    
    print("\n✨ Done! Your comprehensive analysis results are now open in your browser.")


if __name__ == "__main__":
    main()
