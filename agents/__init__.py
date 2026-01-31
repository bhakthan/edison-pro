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

# Innovative Feature Agents (Phase 1 & Phase 2)
from .anomaly_predictor import AnomalyPredictorAgent, create_anomaly_predictor
from .revision_analyzer import RevisionAnalyzerAgent, create_revision_analyzer
from .query_suggester import QuerySuggestionAgent, create_query_suggestion_agent
from .expert_network import ExpertNetworkAgent, create_expert_network
from .counterfactual_simulator import CounterfactualSimulator, create_counterfactual_simulator

# Phase 3 Enhancement Modules
from .feedback_tracker import (
    FeedbackTracker,
    FeedbackEvent,
    FeatureUsageStats,
    create_feedback_tracker
)
from .results_visualizer import (
    ResultsVisualizer,
    ReportGenerator,
    create_visualizer,
    create_report_generator
)
from .cache_manager import (
    CacheManager,
    get_cache_manager,
    create_cache_manager
)
from .azure_search_integration import (
    PatternStorage,
    create_pattern_storage
)

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
