"""
Flickering System Orchestrator
Main entry point for the flickering cognitive architecture.
Coordinates all 6 agents to perform diagram analysis.
"""

import numpy as np
from typing import Dict, List, Any, Optional
import time
from datetime import datetime

from .reality_anchor import RealityAnchorAgent, FeatureVector
from .memory_atlas import MemoryAtlasAgent
from .theta_oscillator import ThetaOscillatorAgent
from .anticipatory_simulation import AnticipatorySimulationAgent
from .map_integration import MapIntegrationAgent
from .pathway_generator import PathwayGeneratorAgent
from .confidence_evaluator import ConfidenceEvaluator, summarize_confidence


class FlickeringSystem:
    """
    Main orchestrator for the flickering cognitive architecture.
    
    Coordinates all 6 agents:
    1. Reality Anchor - Extract current features
    2. Memory Atlas - Retrieve historical patterns
    3. Theta Oscillator - Rhythmic flickering
    4. Anticipatory Simulation - Pre-wiring during idle
    5. Map Integration - Compositional learning
    6. Pathway Generator - Alternative hypotheses
    """
    
    def __init__(
        self,
        storage_path: str = "./memory_atlas",
        theta_frequency: float = 8.0,
        mismatch_threshold: float = 0.3,
        enable_background_simulation: bool = False
    ):
        """
        Initialize Flickering System
        
        Args:
            storage_path: Directory for memory atlas storage
            theta_frequency: Oscillation frequency in Hz (4-10)
            mismatch_threshold: Threshold for triggering learning (0.0-1.0)
            enable_background_simulation: Whether to start background pre-wiring
        """
        print("🧠 Initializing Flickering Cognitive Architecture...")
        
        # Initialize confidence evaluator
        self.confidence_evaluator = ConfidenceEvaluator()
        
        # Initialize agents
        self.reality_anchor = RealityAnchorAgent()
        self.memory_atlas = MemoryAtlasAgent(storage_path=storage_path)
        
        self.theta_oscillator = ThetaOscillatorAgent(
            reality_agent=self.reality_anchor,
            memory_agent=self.memory_atlas,
            frequency_hz=theta_frequency,
            mismatch_threshold=mismatch_threshold
        )
        
        self.anticipatory_simulation = AnticipatorySimulationAgent(
            memory_atlas=self.memory_atlas
        )
        
        self.map_integration = MapIntegrationAgent(
            memory_atlas=self.memory_atlas
        )
        
        self.pathway_generator = PathwayGeneratorAgent(
            memory_atlas=self.memory_atlas
        )
        
        # Start background simulation if enabled
        if enable_background_simulation:
            self.anticipatory_simulation.start_background_simulation()
        
        print("✅ Flickering System initialized")
        print(f"   Theta frequency: {theta_frequency} Hz")
        print(f"   Mismatch threshold: {mismatch_threshold}")
        print(f"   Memory patterns: {len(self.memory_atlas.patterns)}")
    
    def analyze(
        self,
        diagram: Any,
        num_cycles: int = 100,
        domain: Optional[str] = None,
        theta_frequency: Optional[float] = None,
        return_trace: bool = True,
        generate_alternatives: bool = True
    ) -> Dict[str, Any]:
        """
        Perform complete flickering analysis on diagram
        
        Args:
            diagram: Diagram image (file path, PIL Image, or base64)
            num_cycles: Number of oscillation cycles (default 100)
            domain: Optional domain hint (electrical, mechanical, pid, etc.)
            theta_frequency: Optional override for oscillation frequency
            return_trace: Whether to return full attention trace
            generate_alternatives: Whether to generate alternative hypotheses
            
        Returns:
            Complete analysis results with interpretation, mismatches, trace
        """
        start_time = time.time()
        
        # Reset confidence evaluator for new analysis
        self.confidence_evaluator.reset()
        
        print("\n" + "="*70)
        print("🌊 FLICKERING COGNITIVE ANALYSIS")
        print("="*70)
        
        # Update theta frequency if specified
        if theta_frequency:
            self.theta_oscillator.f_theta = theta_frequency
            print(f"⚙️  Theta frequency adjusted to {theta_frequency} Hz")
        
        # Check anticipatory cache first (fast path)
        print("\n💡 Checking anticipatory cache...")
        cached_strategy = self.anticipatory_simulation.check_cache(diagram)
        
        cache_hit = bool(cached_strategy)
        cache_similarity = cached_strategy.get('similarity', 0.0) if cached_strategy else 0.0
        
        # Evaluate anticipatory simulation confidence
        cache_confidence = self.confidence_evaluator.evaluate_anticipatory_simulation(
            cache_hit=cache_hit,
            similarity_threshold=cache_similarity,
            cache_size=len(self.anticipatory_simulation.latent_cache),
            gap_coverage=0.6,  # Could be computed from gap analysis
        )
        
        if cached_strategy:
            print(f"   ⚡ Cache hit! Confidence: {cache_confidence.overall:.1%}")
            # Still extract features for accuracy
            features = self.reality_anchor.analyze(diagram, use_vision=False)
        else:
            print(f"   📊 Cache miss - proceeding with full analysis")
            features = None
        
        # Run flickering analysis
        results = self.theta_oscillator.analyze_with_flickering(
            diagram=diagram,
            num_cycles=num_cycles,
            domain=domain,
            return_trace=return_trace
        )
        
        # Process mismatch events for learning
        mismatch_events = results.get('mismatch_events', [])
        if mismatch_events:
            print(f"\n🔥 Processing {len(mismatch_events)} mismatch event(s)...")
            
            # Trigger map integration for high novelty events
            high_novelty_events = [
                e for e in mismatch_events
                if e.get('novelty_level') in ['high', 'critical']
            ]
            
            if high_novelty_events:
                print(f"   📚 Triggering Map Integration for {len(high_novelty_events)} high-novelty events")
                
                # Get current features if not already extracted
                if features is None:
                    features = self.reality_anchor.analyze(diagram, use_vision=False)
                
                # Integrate new knowledge
                for event in high_novelty_events:
                    try:
                        new_version = self.map_integration.integrate_new_experience(
                            mismatch_event=event,
                            current_features=features,
                            domain=domain
                        )
                        print(f"      ✅ Map updated: {new_version}")
                    except Exception as e:
                        print(f"      ⚠️  Map integration failed: {e}")
        
        # Generate alternative hypotheses if requested
        alternatives = []
        if generate_alternatives and results.get('interpretation', {}).get('status') == 'success':
            print(f"\n🌳 Generating alternative interpretation pathways...")
            
            # Get features if not already extracted
            if features is None:
                features = self.reality_anchor.analyze(diagram, use_vision=False)
            
            # Find ambiguous elements (simplified - use components)
            components = results['interpretation'].get('components', [])
            
            if components:
                # Generate alternatives for first component (demo)
                context = {
                    'domain': domain or 'general',
                    'neighbors': components[1:] if len(components) > 1 else []
                }
                
                hypotheses = self.pathway_generator.generate_alternatives(
                    ambiguous_element=components[0],
                    surrounding_context=context,
                    top_k=5
                )
                
                alternatives = [h.to_dict() for h in hypotheses]
                
                # Evaluate hypothesis generation confidence
                if hypotheses:
                    scores = [h.score for h in hypotheses]
                    hypothesis_confidence = self.confidence_evaluator.evaluate_hypothesis_generation(
                        num_hypotheses=len(hypotheses),
                        top_hypothesis_score=max(scores) if scores else 0.0,
                        score_variance=float(np.var(scores)) if len(scores) > 1 else 0.0,
                        evidence_count=sum(len(h.evidence) for h in hypotheses),
                    )
                    print(f"   Hypothesis confidence: {hypothesis_confidence.overall:.1%}")
                
                # Visualize pathways
                if hypotheses:
                    pathway_viz = self.pathway_generator.visualize_pathways(hypotheses)
                    print(pathway_viz)
        
        # Compile final results
        elapsed_time = time.time() - start_time
        
        # Generate confidence summary
        confidence_summary = summarize_confidence(self.confidence_evaluator)
        
        final_results = {
            **results,
            'alternatives': alternatives,
            'system_info': {
                'theta_frequency': self.theta_oscillator.f_theta,
                'mismatch_threshold': self.theta_oscillator.mismatch_threshold,
                'memory_patterns': len(self.memory_atlas.patterns),
                'cache_size': len(self.anticipatory_simulation.latent_cache),
                'total_latency_ms': int(elapsed_time * 1000)
            },
            'learning_events': [
                {
                    'type': 'map_integration',
                    'count': len(high_novelty_events) if mismatch_events else 0
                }
            ],
            'confidence': {
                'overall': confidence_summary['final_confidence'],
                'bottleneck': confidence_summary.get('bottleneck'),
                'uncertainty': confidence_summary['uncertainty'],
                'step_confidences': confidence_summary['step_confidences'],
            }
        }
        
        print("\n" + "="*70)
        print(f"✅ Analysis complete in {elapsed_time:.2f}s")
        print(f"   Cycles: {num_cycles}")
        print(f"   Mismatches: {len(mismatch_events)}")
        print(f"   Overall Confidence: {confidence_summary['final_confidence']:.1%}")
        print(f"   Bottleneck: {confidence_summary.get('bottleneck', 'None')}")
        print(f"   Aleatoric Uncertainty: {confidence_summary['uncertainty']['aleatoric']:.1%}")
        print(f"   Epistemic Uncertainty: {confidence_summary['uncertainty']['epistemic']:.1%}")
        print("="*70 + "\n")
        
        return final_results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'memory_atlas': {
                'total_patterns': len(self.memory_atlas.patterns),
                'patterns_by_domain': {
                    domain: len(patterns)
                    for domain, patterns in self.memory_atlas.domain_maps.items()
                }
            },
            'anticipatory_simulation': self.anticipatory_simulation.get_cache_stats(),
            'map_integration': {
                'total_updates': len(self.map_integration.update_history),
                'recent_updates': self.map_integration.get_update_history()[-5:]
            },
            'theta_oscillator': {
                'frequency_hz': self.theta_oscillator.f_theta,
                'mismatch_threshold': self.theta_oscillator.mismatch_threshold,
                'total_cycles': self.theta_oscillator.cycle_count
            }
        }
    
    def shutdown(self):
        """Cleanup and shutdown system"""
        print("🛑 Shutting down Flickering System...")
        self.anticipatory_simulation.stop_background_simulation()
        print("✅ Shutdown complete")


# Convenience function for quick analysis
def analyze_diagram(
    diagram: Any,
    num_cycles: int = 100,
    theta_frequency: float = 8.0,
    domain: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick function to analyze a diagram with flickering architecture
    
    Args:
        diagram: Diagram image (file path, PIL Image, or base64)
        num_cycles: Number of oscillation cycles
        theta_frequency: Oscillation frequency in Hz
        domain: Optional domain hint
        
    Returns:
        Analysis results
    """
    system = FlickeringSystem(
        theta_frequency=theta_frequency,
        enable_background_simulation=False
    )
    
    try:
        results = system.analyze(
            diagram=diagram,
            num_cycles=num_cycles,
            domain=domain
        )
        return results
    finally:
        system.shutdown()
