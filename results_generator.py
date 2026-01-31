"""
Results Page Generator for EDISON PRO
Creates comprehensive HTML results pages from analysis outputs
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class ResultsPageGenerator:
    """Generate comprehensive HTML results pages from analysis data"""
    
    def __init__(self, output_dir: str = "out"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_results_page(
        self,
        conversation_history: List[tuple],
        generated_files: List[str],
        analysis_summary: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a comprehensive HTML results page.
        
        Args:
            conversation_history: List of (question, answer) tuples
            generated_files: List of file paths generated during analysis
            analysis_summary: Optional summary statistics
            
        Returns:
            Path to generated HTML file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"analysis_results_{timestamp}.html"
        
        html_content = self._build_html(
            conversation_history,
            generated_files,
            analysis_summary,
            timestamp
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(output_file)
    
    def _build_html(
        self,
        conversation_history: List[tuple],
        generated_files: List[str],
        analysis_summary: Optional[Dict[str, Any]],
        timestamp: str
    ) -> str:
        """Build the complete HTML document"""
        
        # Separate files by type
        csv_files = [f for f in generated_files if f.endswith('.csv')]
        html_files = [f for f in generated_files if f.endswith('.html') and 'analysis_results' not in f]
        other_files = [f for f in generated_files if f not in csv_files and f not in html_files]
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EDISON PRO - Analysis Results</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 1rem;
        }}
        
        .header .icon {{
            font-size: 3rem;
        }}
        
        .header .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .header .timestamp {{
            font-size: 0.9rem;
            opacity: 0.8;
            margin-top: 0.5rem;
        }}
        
        .content {{
            padding: 2rem;
        }}
        
        .section {{
            margin-bottom: 3rem;
            padding: 2rem;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }}
        
        .section-title {{
            font-size: 1.8rem;
            color: #667eea;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .section-icon {{
            font-size: 1.5rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        
        .summary-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
        }}
        
        .summary-card .label {{
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        
        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }}
        
        .qa-item {{
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .question {{
            font-weight: 600;
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.1rem;
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
        }}
        
        .question::before {{
            content: "Q:";
            background: #667eea;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
            flex-shrink: 0;
        }}
        
        .answer {{
            color: #333;
            padding-left: 2.5rem;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .answer::before {{
            content: "A:";
            background: #4CAF50;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
            margin-left: -2.5rem;
            margin-right: 0.5rem;
        }}
        
        .file-list {{
            list-style: none;
        }}
        
        .file-item {{
            background: white;
            padding: 1rem 1.5rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}
        
        .file-item:hover {{
            transform: translateX(5px);
        }}
        
        .file-info {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .file-icon {{
            font-size: 2rem;
        }}
        
        .file-details {{
            display: flex;
            flex-direction: column;
        }}
        
        .file-name {{
            font-weight: 600;
            color: #333;
            margin-bottom: 0.25rem;
        }}
        
        .file-path {{
            font-size: 0.85rem;
            color: #666;
            font-family: 'Courier New', monospace;
        }}
        
        .file-size {{
            color: #999;
            font-size: 0.9rem;
        }}
        
        .file-actions {{
            display: flex;
            gap: 0.5rem;
        }}
        
        .btn {{
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            text-decoration: none;
            display: inline-block;
            transition: all 0.2s;
        }}
        
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .btn-secondary {{
            background: #4CAF50;
            color: white;
        }}
        
        .btn-secondary:hover {{
            background: #45a049;
            transform: translateY(-2px);
        }}
        
        .chart-container {{
            background: white;
            padding: 1rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .chart-container iframe {{
            width: 100%;
            height: 600px;
            border: none;
            border-radius: 8px;
        }}
        
        .no-data {{
            text-align: center;
            padding: 3rem;
            color: #999;
            font-style: italic;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            background: #f8f9fa;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .btn {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                <span class="icon">⚡</span>
                EDISON PRO
                <span class="icon">📊</span>
            </h1>
            <div class="subtitle">Engineering Diagram Analysis Results</div>
            <div class="timestamp">Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>
        </div>
        
        <div class="content">
"""
        
        # Summary Section
        if analysis_summary:
            html += self._build_summary_section(analysis_summary)
        
        # Quick Stats
        html += f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">📈</span>
                    Analysis Overview
                </h2>
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="label">Questions Asked</div>
                        <div class="value">{len(conversation_history)}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">Files Generated</div>
                        <div class="value">{len(generated_files)}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">CSV Exports</div>
                        <div class="value">{len(csv_files)}</div>
                    </div>
                    <div class="summary-card">
                        <div class="label">Visualizations</div>
                        <div class="value">{len(html_files)}</div>
                    </div>
                </div>
            </div>
"""
        
        # Q&A Section
        html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">💬</span>
                    Questions & Answers
                </h2>
"""
        
        if conversation_history:
            for i, (question, answer) in enumerate(conversation_history, 1):
                html += f"""
                <div class="qa-item">
                    <div class="question">{self._escape_html(question)}</div>
                    <div class="answer">{self._escape_html(answer)}</div>
                </div>
"""
        else:
            html += '<div class="no-data">No conversation history available</div>'
        
        html += """
            </div>
"""
        
        # Charts Section
        if html_files:
            html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">📊</span>
                    Interactive Visualizations
                </h2>
"""
            for chart_file in html_files:
                chart_name = Path(chart_file).stem.replace('_', ' ').title()
                rel_path = os.path.relpath(chart_file, self.output_dir)
                html += f"""
                <div class="chart-container">
                    <h3 style="margin-bottom: 1rem; color: #667eea;">{chart_name}</h3>
                    <iframe src="{rel_path}" title="{chart_name}"></iframe>
                </div>
"""
            html += """
            </div>
"""
        
        # Generated Files Section
        if generated_files:
            html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">📁</span>
                    Generated Files
                </h2>
                <ul class="file-list">
"""
            for file_path in generated_files:
                file_name = os.path.basename(file_path)
                file_size = self._format_file_size(file_path)
                file_ext = Path(file_path).suffix.lower()
                
                icon = {
                    '.csv': '📊',
                    '.html': '🌐',
                    '.xlsx': '📈',
                    '.json': '📋',
                    '.txt': '📄'
                }.get(file_ext, '📄')
                
                abs_path = os.path.abspath(file_path)
                rel_path = os.path.relpath(file_path, self.output_dir)
                
                html += f"""
                    <li class="file-item">
                        <div class="file-info">
                            <span class="file-icon">{icon}</span>
                            <div class="file-details">
                                <div class="file-name">{file_name}</div>
                                <div class="file-path">{abs_path}</div>
                            </div>
                            <span class="file-size">{file_size}</span>
                        </div>
                        <div class="file-actions">
                            <a href="{rel_path}" class="btn btn-primary" download>Download</a>
                            <button class="btn btn-secondary" onclick="copyToClipboard('{abs_path.replace(chr(92), chr(92)+chr(92))}')">Copy Path</button>
                        </div>
                    </li>
"""
            
            html += """
                </ul>
            </div>
"""
        
        # Footer
        html += """
        </div>
        
        <div class="footer">
            <p>Generated by EDISON PRO - Engineering Diagram Analysis System</p>
            <p style="font-size: 0.85rem; margin-top: 0.5rem;">
                Powered by Azure OpenAI o3-pro & GPT-4.1 Code Agent
            </p>
        </div>
    </div>
    
    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                event.target.textContent = '✓ Copied!';
                setTimeout(() => {
                    event.target.textContent = 'Copy Path';
                }, 2000);
            }).catch(err => {
                alert('Failed to copy: ' + err);
            });
        }
    </script>
</body>
</html>
"""
        return html
    
    def _build_summary_section(self, summary: Dict[str, Any]) -> str:
        """Build summary statistics section"""
        html = """
            <div class="section">
                <h2 class="section-title">
                    <span class="section-icon">📋</span>
                    Analysis Summary
                </h2>
                <div class="summary-grid">
"""
        for key, value in summary.items():
            label = key.replace('_', ' ').title()
            html += f"""
                    <div class="summary-card">
                        <div class="label">{label}</div>
                        <div class="value">{value}</div>
                    </div>
"""
        html += """
                </div>
            </div>
"""
        return html
    
    def _format_file_size(self, file_path: str) -> str:
        """Format file size in human-readable format"""
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return "Unknown"
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))


def generate_results_page(
    conversation_history: List[tuple],
    generated_files: List[str],
    analysis_summary: Optional[Dict[str, Any]] = None,
    output_dir: str = "out"
) -> str:
    """
    Convenience function to generate a results page.
    
    Args:
        conversation_history: List of (question, answer) tuples
        generated_files: List of file paths generated
        analysis_summary: Optional summary statistics
        output_dir: Output directory for results page
        
    Returns:
        Path to generated HTML file
    """
    generator = ResultsPageGenerator(output_dir)
    return generator.generate_results_page(
        conversation_history,
        generated_files,
        analysis_summary
    )
