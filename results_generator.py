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
        :root {{
            --bg-canvas: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --bg-surface: #ffffff;
            --bg-subtle: #f8f9fa;
            --bg-elevated: #ffffff;
            --text-primary: #333333;
            --text-secondary: #666666;
            --text-muted: #999999;
            --border-soft: #e0e0e0;
            --accent: #667eea;
            --accent-strong: #5568d3;
            --accent-soft: rgba(102, 126, 234, 0.14);
            --success: #4CAF50;
            --success-strong: #45a049;
            --shadow-lg: 0 20px 60px rgba(0, 0, 0, 0.3);
            --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.1);
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.1);
            --header-background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}

        html[data-theme='dark'] {{
            color-scheme: dark;
            --bg-canvas: radial-gradient(circle at 14% 18%, rgba(57, 199, 178, 0.16), transparent 26%), radial-gradient(circle at 86% 22%, rgba(96, 165, 250, 0.18), transparent 30%), linear-gradient(160deg, #050b14 0%, #081120 42%, #0d1728 100%);
            --bg-surface: #0d1728;
            --bg-subtle: #111d31;
            --bg-elevated: #162337;
            --text-primary: #e5edf7;
            --text-secondary: #9cb0c7;
            --text-muted: #7d92ab;
            --border-soft: rgba(148, 163, 184, 0.18);
            --accent: #7aa2ff;
            --accent-strong: #9cc9ff;
            --accent-soft: rgba(122, 162, 255, 0.16);
            --success: #43d393;
            --success-strong: #67e8a4;
            --shadow-lg: 0 20px 60px rgba(0, 0, 0, 0.4);
            --shadow-md: 0 10px 24px rgba(0, 0, 0, 0.22);
            --shadow-sm: 0 8px 20px rgba(0, 0, 0, 0.18);
            --header-background: radial-gradient(circle at 82% 18%, rgba(251, 146, 60, 0.12), transparent 28%), linear-gradient(135deg, rgba(16, 37, 52, 0.96) 0%, rgba(8, 20, 36, 0.98) 100%);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-canvas);
            padding: 2rem;
            color: var(--text-primary);
            line-height: 1.6;
            transition: background 0.25s ease, color 0.25s ease;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-surface);
            border-radius: 16px;
            box-shadow: var(--shadow-lg);
            overflow: hidden;
            border: 1px solid var(--border-soft);
        }}
        
        .header {{
            background: var(--header-background);
            color: white;
            padding: 2rem;
        }}

        .header-bar {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
        }}

        .header-copy {{
            flex: 1;
            text-align: center;
            padding-left: 3rem;
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

        .theme-toggle {{
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.12);
            color: white;
            padding: 0.55rem 0.9rem;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: transform 0.2s ease, background 0.2s ease;
            white-space: nowrap;
        }}

        .theme-toggle:hover {{
            background: rgba(255, 255, 255, 0.18);
            transform: translateY(-1px);
        }}
        
        .content {{
            padding: 2rem;
        }}
        
        .section {{
            margin-bottom: 3rem;
            padding: 2rem;
            background: var(--bg-subtle);
            border-radius: 12px;
            border-left: 4px solid var(--accent);
            border-top: 1px solid var(--border-soft);
            border-right: 1px solid var(--border-soft);
            border-bottom: 1px solid var(--border-soft);
        }}
        
        .section-title {{
            font-size: 1.8rem;
            color: var(--accent);
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
            background: var(--bg-elevated);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: var(--shadow-md);
            border-left: 4px solid var(--accent);
            border-top: 1px solid var(--border-soft);
            border-right: 1px solid var(--border-soft);
            border-bottom: 1px solid var(--border-soft);
        }}
        
        .summary-card .label {{
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        
        .summary-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }}
        
        .qa-item {{
            background: var(--bg-elevated);
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-soft);
        }}
        
        .question {{
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 1rem;
            font-size: 1.1rem;
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
        }}
        
        .question::before {{
            content: "Q:";
            background: var(--accent);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
            flex-shrink: 0;
        }}
        
        .answer {{
            color: var(--text-primary);
            padding-left: 2.5rem;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .answer::before {{
            content: "A:";
            background: var(--success);
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
            background: var(--bg-elevated);
            padding: 1rem 1.5rem;
            margin-bottom: 1rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: var(--shadow-sm);
            transition: transform 0.2s;
            border: 1px solid var(--border-soft);
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
            color: var(--text-primary);
            margin-bottom: 0.25rem;
        }}
        
        .file-path {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-family: 'Courier New', monospace;
        }}
        
        .file-size {{
            color: var(--text-muted);
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
            background: var(--accent);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: var(--accent-strong);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .btn-secondary {{
            background: var(--success);
            color: white;
        }}
        
        .btn-secondary:hover {{
            background: var(--success-strong);
            transform: translateY(-2px);
        }}
        
        .chart-container {{
            background: var(--bg-elevated);
            padding: 1rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-soft);
        }}

        .chart-title {{
            margin-bottom: 1rem;
            color: var(--accent);
        }}
        
        .chart-container iframe {{
            width: 100%;
            height: 600px;
            border: none;
            border-radius: 8px;
            background: white;
        }}
        
        .no-data {{
            text-align: center;
            padding: 3rem;
            color: var(--text-muted);
            font-style: italic;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            background: var(--bg-subtle);
            color: var(--text-secondary);
            border-top: 1px solid var(--border-soft);
        }}

        @media (max-width: 900px) {{
            .header-bar {{
                flex-direction: column;
                align-items: stretch;
            }}

            .header-copy {{
                padding-left: 0;
            }}

            .theme-toggle {{
                align-self: flex-end;
            }}

            .file-item {{
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }}
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .btn,
            .theme-toggle {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-bar">
                <button class="theme-toggle" type="button" id="theme-toggle" aria-label="Toggle color theme">Dark</button>
                <div class="header-copy">
                    <h1>
                        <span class="icon">⚡</span>
                        EDISON PRO
                        <span class="icon">📊</span>
                    </h1>
                    <div class="subtitle">Engineering Diagram Analysis Results</div>
                    <div class="timestamp">Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>
                </div>
                <div style="width: 78px;"></div>
            </div>
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
                    <h3 class="chart-title">{chart_name}</h3>
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
                            <button class="btn btn-secondary" onclick="copyToClipboard('{abs_path.replace(chr(92), chr(92)+chr(92))}', this)">Copy Path</button>
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
        const THEME_STORAGE_KEY = 'edisonpro-theme';

        function applyTheme(theme) {
            document.documentElement.dataset.theme = theme;
            const toggle = document.getElementById('theme-toggle');
            if (toggle) {
                toggle.textContent = theme === 'dark' ? 'Light' : 'Dark';
                toggle.setAttribute('aria-label', theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme');
            }
        }

        function initializeTheme() {
            const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
            const theme = storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : 'dark';
            applyTheme(theme);
        }

        function toggleTheme() {
            const nextTheme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
            window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
            applyTheme(nextTheme);
        }

        function copyToClipboard(text, button) {
            navigator.clipboard.writeText(text).then(() => {
                const originalLabel = button.textContent;
                button.textContent = '✓ Copied!';
                setTimeout(() => {
                    button.textContent = originalLabel;
                }, 2000);
            }).catch(err => {
                alert('Failed to copy: ' + err);
            });
        }

        initializeTheme();
        document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
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
