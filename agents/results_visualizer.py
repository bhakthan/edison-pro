"""
Phase 3 Enhancements: Results Visualization & Report Generation
Generate visual reports with charts for innovative features

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import base64
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

# Try to import visualization libraries
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

logger = logging.getLogger(__name__)


class ResultsVisualizer:
    """
    Generate visual charts and reports for innovative feature results
    
    Phase 3 Enhancement: Rich visualizations for better decision-making
    
    Capabilities:
    1. Risk heatmaps for anomaly predictions
    2. Consensus gauges for expert reviews
    3. Scenario comparison charts
    4. Trend analysis over time
    5. PDF/HTML report generation
    """
    
    def __init__(self, use_plotly: bool = True):
        """
        Initialize visualizer
        
        Args:
            use_plotly: Prefer Plotly over Matplotlib if available
        """
        self.use_plotly = use_plotly and HAS_PLOTLY
        self.use_matplotlib = not use_plotly and HAS_MATPLOTLIB
        
        if not self.use_plotly and not self.use_matplotlib:
            logger.warning("⚠️ No visualization libraries available")
        
        logger.info(f"📊 Results Visualizer initialized (Engine: {'Plotly' if self.use_plotly else 'Matplotlib' if self.use_matplotlib else 'None'})")
    
    def create_risk_gauge(
        self,
        risk_score: float,
        title: str = "Risk Assessment"
    ) -> str:
        """
        Create risk gauge visualization
        
        Args:
            risk_score: Risk score (0.0-1.0)
            title: Chart title
            
        Returns:
            HTML string with embedded chart
        """
        if not self.use_plotly:
            return f"<p>Risk Score: {risk_score:.0%}</p>"
        
        try:
            # Determine color based on risk level
            if risk_score < 0.3:
                color = "green"
            elif risk_score < 0.7:
                color = "yellow"
            else:
                color = "red"
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=risk_score * 100,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': title, 'font': {'size': 20}},
                delta={'reference': 50},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': color},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 30], 'color': '#d4edda'},
                        {'range': [30, 70], 'color': '#fff3cd'},
                        {'range': [70, 100], 'color': '#f8d7da'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 70
                    }
                }
            ))
            
            fig.update_layout(
                height=300,
                font={'size': 14}
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=f"risk_gauge_{datetime.now().timestamp()}")
            
        except Exception as e:
            logger.error(f"❌ Error creating risk gauge: {e}")
            return f"<p>Risk Score: {risk_score:.0%}</p>"
    
    def create_consensus_chart(
        self,
        expert_opinions: List[Dict[str, Any]],
        consensus_level: float
    ) -> str:
        """
        Create expert consensus visualization
        
        Args:
            expert_opinions: List of expert opinions with approval status
            consensus_level: Overall consensus (0.0-1.0)
            
        Returns:
            HTML string with embedded chart
        """
        if not self.use_plotly:
            return f"<p>Consensus: {consensus_level:.0%}</p>"
        
        try:
            # Count approvals by type
            approval_counts = {
                'Approved': 0,
                'Conditional': 0,
                'Rejected': 0
            }
            
            for opinion in expert_opinions:
                status = opinion.get('approval_status', 'unknown')
                if status == 'approved':
                    approval_counts['Approved'] += 1
                elif status == 'conditional':
                    approval_counts['Conditional'] += 1
                elif status == 'rejected':
                    approval_counts['Rejected'] += 1
            
            # Create pie chart
            fig = go.Figure(data=[go.Pie(
                labels=list(approval_counts.keys()),
                values=list(approval_counts.values()),
                marker=dict(colors=['#28a745', '#ffc107', '#dc3545']),
                textinfo='label+value+percent',
                hole=0.3
            )])
            
            fig.update_layout(
                title=f"Expert Panel Consensus: {consensus_level:.0%}",
                height=400,
                font={'size': 14},
                showlegend=True
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=f"consensus_chart_{datetime.now().timestamp()}")
            
        except Exception as e:
            logger.error(f"❌ Error creating consensus chart: {e}")
            return f"<p>Consensus: {consensus_level:.0%}</p>"
    
    def create_scenario_comparison(
        self,
        scenarios: List[Dict[str, Any]],
        comparison_matrix: Dict[str, List[float]]
    ) -> str:
        """
        Create scenario comparison visualization
        
        Args:
            scenarios: List of scenario outcomes
            comparison_matrix: Matrix of comparison metrics
            
        Returns:
            HTML string with embedded chart
        """
        if not self.use_plotly:
            return "<p>Scenario comparison chart not available</p>"
        
        try:
            # Create spider/radar chart for multi-dimensional comparison
            categories = ['Cost', 'Performance', 'Safety', 'Feasibility']
            
            fig = go.Figure()
            
            for i, scenario in enumerate(scenarios[:5]):  # Limit to top 5
                metrics = scenario.get('performance_metrics', {})
                values = [
                    metrics.get('cost_multiplier', 1.0),
                    metrics.get('performance_score', 0.5),
                    metrics.get('safety_score', 0.5),
                    scenario.get('feasibility_score', 0.5)
                ]
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=scenario.get('description', f'Scenario {i+1}')[:30]
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1]
                    )),
                showlegend=True,
                title="Scenario Comparison (Multi-Dimensional)",
                height=500
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=f"scenario_comparison_{datetime.now().timestamp()}")
            
        except Exception as e:
            logger.error(f"❌ Error creating scenario comparison: {e}")
            return "<p>Scenario comparison chart not available</p>"
    
    def create_trend_chart(
        self,
        data: List[Dict[str, Any]],
        metric_key: str,
        title: str = "Trend Analysis"
    ) -> str:
        """
        Create trend line chart over time
        
        Args:
            data: List of data points with timestamps
            metric_key: Key for metric to plot
            title: Chart title
            
        Returns:
            HTML string with embedded chart
        """
        if not self.use_plotly:
            return f"<p>{title}: {len(data)} data points</p>"
        
        try:
            timestamps = [d.get('timestamp', '') for d in data]
            values = [d.get(metric_key, 0) for d in data]
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                mode='lines+markers',
                name=metric_key,
                line=dict(color='#4f46e5', width=2),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title=title,
                xaxis_title="Time",
                yaxis_title=metric_key.replace('_', ' ').title(),
                height=400,
                hovermode='x unified'
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=f"trend_chart_{datetime.now().timestamp()}")
            
        except Exception as e:
            logger.error(f"❌ Error creating trend chart: {e}")
            return f"<p>{title}: {len(data)} data points</p>"


class ReportGenerator:
    """
    Generate comprehensive HTML/PDF reports for innovative features
    
    Phase 3 Enhancement: Professional report generation
    """
    
    def __init__(self, visualizer: Optional[ResultsVisualizer] = None):
        """Initialize report generator"""
        self.visualizer = visualizer or ResultsVisualizer()
        logger.info("📄 Report Generator initialized")
    
    def generate_anomaly_report(
        self,
        result: Dict[str, Any],
        diagram_path: str,
        domain: str
    ) -> str:
        """Generate anomaly prediction report"""
        
        report_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Anomaly Prediction Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #4f46e5; }}
        .header {{ background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #4f46e5; background: #f9fafb; }}
        .risk-high {{ color: #dc3545; font-weight: bold; }}
        .risk-medium {{ color: #ffc107; font-weight: bold; }}
        .risk-low {{ color: #28a745; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4f46e5; color: white; }}
    </style>
</head>
<body>
    <h1>⚠️ Anomaly Prediction Report</h1>
    
    <div class="header">
        <p><strong>Diagram:</strong> {Path(diagram_path).name}</p>
        <p><strong>Domain:</strong> {domain.title()}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Risk Score:</strong> <span class="risk-{'high' if result.get('risk_score', 0) > 0.7 else 'medium' if result.get('risk_score', 0) > 0.4 else 'low'}">{result.get('risk_score', 0):.0%}</span></p>
        <p><strong>Confidence:</strong> {result.get('confidence', 0):.0%}</p>
    </div>
    
    <div class="section">
        <h2>Risk Assessment</h2>
        {self.visualizer.create_risk_gauge(result.get('risk_score', 0), "Overall Risk")}
    </div>
"""
        
        if result.get('anomalies'):
            report_html += """
    <div class="section">
        <h2>Detected Anomalies</h2>
        <table>
            <tr>
                <th>Pattern</th>
                <th>Similarity</th>
                <th>Risk Level</th>
                <th>Description</th>
            </tr>
"""
            for anomaly in result['anomalies']:
                report_html += f"""
            <tr>
                <td>{anomaly.get('pattern_name', 'N/A')}</td>
                <td>{anomaly.get('similarity', 0):.0%}</td>
                <td class="risk-{anomaly.get('risk_level', 'unknown')}">{anomaly.get('risk_level', 'N/A').upper()}</td>
                <td>{anomaly.get('description', 'N/A')}</td>
            </tr>
"""
            report_html += """
        </table>
    </div>
"""
        
        if result.get('recommendations'):
            report_html += """
    <div class="section">
        <h2>Recommendations</h2>
        <ol>
"""
            for rec in result['recommendations']:
                report_html += f"            <li>{rec}</li>\n"
            report_html += """
        </ol>
    </div>
"""
        
        if result.get('prevention_cost_estimate') and result.get('failure_cost_estimate'):
            report_html += f"""
    <div class="section">
        <h2>💰 Cost-Benefit Analysis</h2>
        <p><strong>Prevention Cost:</strong> ${result['prevention_cost_estimate']:,.0f}</p>
        <p><strong>Potential Failure Cost:</strong> ${result['failure_cost_estimate']:,.0f}</p>
        <p><strong>Potential Savings:</strong> ${result['failure_cost_estimate'] - result['prevention_cost_estimate']:,.0f}</p>
    </div>
"""
        
        report_html += """
</body>
</html>
"""
        
        return report_html
    
    def generate_expert_review_report(
        self,
        result: Dict[str, Any],
        diagram_path: str,
        domain: str
    ) -> str:
        """Generate expert panel review report"""
        
        report_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Expert Panel Review Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #4f46e5; }}
        .header {{ background: #f3f4f6; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #4f46e5; background: #f9fafb; }}
        .expert {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
        .approved {{ background: #d4edda; }}
        .conditional {{ background: #fff3cd; }}
        .rejected {{ background: #f8d7da; }}
    </style>
</head>
<body>
    <h1>👥 Expert Panel Review Report</h1>
    
    <div class="header">
        <p><strong>Diagram:</strong> {Path(diagram_path).name}</p>
        <p><strong>Domain:</strong> {domain.title()}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Overall Recommendation:</strong> {result.get('overall_recommendation', 'N/A')}</p>
        <p><strong>Consensus Level:</strong> {result.get('consensus_level', 0):.0%}</p>
    </div>
    
    <div class="section">
        <h2>Consensus Breakdown</h2>
        {self.visualizer.create_consensus_chart(result.get('expert_opinions', []), result.get('consensus_level', 0))}
    </div>
    
    <div class="section">
        <h2>Expert Opinions</h2>
"""
        
        for opinion in result.get('expert_opinions', []):
            approval_class = opinion.get('approval_status', 'unknown')
            report_html += f"""
        <div class="expert {approval_class}">
            <h3>{opinion.get('domain', 'Unknown').title()} Expert</h3>
            <p><strong>Approval:</strong> {opinion.get('approval_status', 'N/A').upper()}</p>
            <p><strong>Confidence:</strong> {opinion.get('confidence', 0):.0%}</p>
            <p><strong>Assessment:</strong> {opinion.get('assessment', 'N/A')}</p>
        </div>
"""
        
        report_html += """
    </div>
</body>
</html>
"""
        
        return report_html
    
    def save_report(self, html_content: str, output_path: str) -> bool:
        """Save HTML report to file"""
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"✅ Report saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Error saving report: {e}")
            return False


def create_visualizer(use_plotly: bool = True) -> ResultsVisualizer:
    """Factory function for results visualizer"""
    return ResultsVisualizer(use_plotly=use_plotly)


def create_report_generator(visualizer: Optional[ResultsVisualizer] = None) -> ReportGenerator:
    """Factory function for report generator"""
    return ReportGenerator(visualizer=visualizer)
