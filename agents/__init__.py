"""
Flickering Cognitive Architecture - Multi-Agent System
Based on Yale neuroscience research on hippocampal navigation

Extended with innovative proactive features:
- Anomaly Prediction (failure prevention)
- Revision Analysis (change tracking)
- Query Suggestion (intelligent mentorship)
- Expert Network Synthesis (multi-disciplinary review)
- Counterfactual Simulation (what-if optimization)

Phase 3 Enhancements:
- Feedback Tracking (continuous learning)
- Results Visualization (rich reports)
"""

from .reality_anchor import RealityAnchorAgent
from .memory_atlas import MemoryAtlasAgent
from .theta_oscillator import ThetaOscillatorAgent
from .anticipatory_simulation import AnticipatorySimulationAgent
from .map_integration import MapIntegrationAgent
from .pathway_generator import PathwayGeneratorAgent
from .flickering_system import FlickeringSystem
from .confidence_evaluator import ConfidenceEvaluator, ConfidenceMetrics, ConfidenceChain

try:
    from .anomaly_predictor import AnomalyPredictorAgent, create_anomaly_predictor
except Exception:
    AnomalyPredictorAgent = None
    create_anomaly_predictor = None

try:
    from .revision_analyzer import RevisionAnalyzerAgent, create_revision_analyzer
except Exception:
    RevisionAnalyzerAgent = None
    create_revision_analyzer = None

try:
    from .query_suggester import QuerySuggestionAgent, create_query_suggestion_agent
except Exception:
    QuerySuggestionAgent = None
    create_query_suggestion_agent = None

try:
    from .expert_network import ExpertNetworkAgent, create_expert_network
except Exception:
    ExpertNetworkAgent = None
    create_expert_network = None

try:
    from .counterfactual_simulator import CounterfactualSimulator, create_counterfactual_simulator
except Exception:
    CounterfactualSimulator = None
    create_counterfactual_simulator = None

try:
    from .feedback_tracker import (
        FeedbackTracker,
        FeedbackEvent,
        FeatureUsageStats,
        create_feedback_tracker
    )
except Exception:
    FeedbackTracker = None
    FeedbackEvent = None
    FeatureUsageStats = None
    create_feedback_tracker = None

try:
    from .results_visualizer import (
        ResultsVisualizer,
        ReportGenerator,
        create_visualizer,
        create_report_generator
    )
except Exception:
    ResultsVisualizer = None
    ReportGenerator = None
    create_visualizer = None
    create_report_generator = None

try:
    from .cache_manager import (
        CacheManager,
        get_cache_manager,
        create_cache_manager
    )
except Exception:
    CacheManager = None
    get_cache_manager = None
    create_cache_manager = None

try:
    from .azure_search_integration import (
        PatternStorage,
        create_pattern_storage
    )
except Exception:
    PatternStorage = None
    create_pattern_storage = None

__all__ = [
    # Core Flickering System
    'RealityAnchorAgent',
    'MemoryAtlasAgent',
    'ThetaOscillatorAgent',
    'AnticipatorySimulationAgent',
    'MapIntegrationAgent',
    'PathwayGeneratorAgent',
    'FlickeringSystem',
    'ConfidenceEvaluator',
    'ConfidenceMetrics',
    'ConfidenceChain',
    
    # Innovative Features (Phase 1)
    'AnomalyPredictorAgent',
    'create_anomaly_predictor',
    'RevisionAnalyzerAgent',
    'create_revision_analyzer',
    # Phase 3 Enhancements
    'FeedbackTracker',
    'FeedbackEvent',
    'FeatureUsageStats',
    'create_feedback_tracker',
    'ResultsVisualizer',
    'ReportGenerator',
    'create_visualizer',
    'create_report_generator',
    'CacheManager',
    'get_cache_manager',
    'create_cache_manager',
    'PatternStorage',
    'create_pattern_storage',
]
