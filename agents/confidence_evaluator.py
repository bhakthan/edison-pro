"""
Confidence Evaluator for Flickering Cognitive Architecture

Provides probabilistic confidence metrics for each agent's output,
enabling transparent uncertainty quantification throughout the analysis pipeline.

Based on Bayesian confidence propagation with evidence accumulation.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from datetime import datetime
import json


@dataclass
class ConfidenceMetrics:
    """Confidence metrics for a single operation."""
    
    # Overall confidence score [0.0, 1.0]
    overall: float
    
    # Component-level confidence scores
    components: Dict[str, float] = field(default_factory=dict)
    
    # Evidence quality metrics
    evidence_strength: float = 0.0  # [0, 1] - How strong is the supporting evidence?
    evidence_consistency: float = 0.0  # [0, 1] - How consistent across sources?
    evidence_recency: float = 0.0  # [0, 1] - How recent is the evidence?
    
    # Uncertainty decomposition
    aleatoric_uncertainty: float = 0.0  # Data noise/randomness (irreducible)
    epistemic_uncertainty: float = 0.0  # Model/knowledge gaps (reducible)
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    agent_name: str = ""
    operation: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "overall": float(self.overall),
            "components": {k: float(v) for k, v in self.components.items()},
            "evidence_strength": float(self.evidence_strength),
            "evidence_consistency": float(self.evidence_consistency),
            "evidence_recency": float(self.evidence_recency),
            "aleatoric_uncertainty": float(self.aleatoric_uncertainty),
            "epistemic_uncertainty": float(self.epistemic_uncertainty),
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "operation": self.operation,
        }
    
    def __str__(self) -> str:
        """Human-readable confidence report."""
        return (
            f"{self.agent_name}.{self.operation}: "
            f"Confidence={self.overall:.1%} "
            f"(Evidence: {self.evidence_strength:.1%}, "
            f"Epistemic: {self.epistemic_uncertainty:.1%})"
        )


@dataclass
class ConfidenceChain:
    """Tracks confidence propagation through the agent pipeline."""
    
    steps: List[ConfidenceMetrics] = field(default_factory=list)
    
    def add_step(self, metrics: ConfidenceMetrics):
        """Add a confidence measurement step."""
        self.steps.append(metrics)
    
    def get_final_confidence(self) -> float:
        """
        Compute final confidence using Bayesian confidence propagation.
        
        Formula: C_final = ∏(C_i^w_i) where w_i are importance weights
        Uses geometric mean to penalize weak links in the chain.
        """
        if not self.steps:
            return 0.0
        
        # Weight recent steps more heavily
        weights = np.exp(np.linspace(-1, 0, len(self.steps)))
        weights = weights / weights.sum()
        
        # Geometric mean (multiplicative combination)
        log_confidences = np.log(np.maximum([s.overall for s in self.steps], 1e-10))
        weighted_log_conf = np.dot(log_confidences, weights)
        
        return float(np.exp(weighted_log_conf))
    
    def get_bottleneck(self) -> Optional[ConfidenceMetrics]:
        """Identify the weakest link in the confidence chain."""
        if not self.steps:
            return None
        return min(self.steps, key=lambda s: s.overall)
    
    def get_uncertainty_breakdown(self) -> Dict[str, float]:
        """Get average aleatoric vs epistemic uncertainty."""
        if not self.steps:
            return {"aleatoric": 0.0, "epistemic": 0.0}
        
        aleatoric = np.mean([s.aleatoric_uncertainty for s in self.steps])
        epistemic = np.mean([s.epistemic_uncertainty for s in self.steps])
        
        return {
            "aleatoric": float(aleatoric),
            "epistemic": float(epistemic),
            "total": float(np.sqrt(aleatoric**2 + epistemic**2)),
        }
    
    def to_dict(self) -> Dict:
        """Export full confidence chain."""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "final_confidence": self.get_final_confidence(),
            "bottleneck": self.get_bottleneck().to_dict() if self.get_bottleneck() else None,
            "uncertainty_breakdown": self.get_uncertainty_breakdown(),
        }
    
    def generate_report(self) -> str:
        """Generate human-readable confidence report."""
        if not self.steps:
            return "No confidence data available."
        
        lines = [
            "=" * 60,
            "CONFIDENCE EVALUATION REPORT",
            "=" * 60,
            "",
            f"Final Confidence: {self.get_final_confidence():.1%}",
            "",
            "Step-by-Step Breakdown:",
            "-" * 60,
        ]
        
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")
        
        bottleneck = self.get_bottleneck()
        if bottleneck:
            lines.extend([
                "",
                "⚠️  Bottleneck (Weakest Link):",
                f"   {bottleneck}",
            ])
        
        uncertainty = self.get_uncertainty_breakdown()
        lines.extend([
            "",
            "Uncertainty Breakdown:",
            f"   Aleatoric (data noise): {uncertainty['aleatoric']:.1%}",
            f"   Epistemic (knowledge gap): {uncertainty['epistemic']:.1%}",
            f"   Total: {uncertainty['total']:.1%}",
            "",
            "=" * 60,
        ])
        
        return "\n".join(lines)


class ConfidenceEvaluator:
    """
    Evaluates confidence for each agent operation in the flickering system.
    
    Provides methods to compute confidence based on:
    - Feature quality
    - Pattern match strength
    - Mismatch magnitude
    - Evidence availability
    - Historical performance
    """
    
    def __init__(self):
        self.chain = ConfidenceChain()
    
    def evaluate_feature_extraction(
        self,
        feature_vector: np.ndarray,
        image_quality: float = 1.0,
        ocr_confidence: float = 1.0,
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence in Reality Anchor feature extraction.
        
        Args:
            feature_vector: Extracted feature vector
            image_quality: Image quality metric [0, 1]
            ocr_confidence: OCR confidence if text was extracted
        
        Returns:
            ConfidenceMetrics for feature extraction
        """
        # Check feature vector properties
        if feature_vector is None or len(feature_vector) == 0:
            overall = 0.0
        else:
            # Confidence based on feature magnitude and diversity
            magnitude = float(np.linalg.norm(feature_vector))
            entropy = self._compute_entropy(feature_vector)
            
            # Higher entropy = more diverse features = higher confidence
            # Magnitude should be reasonable (not too small/large)
            magnitude_score = 1.0 - min(abs(magnitude - 1.0), 1.0)
            entropy_score = min(entropy / 5.0, 1.0)  # Normalize entropy
            
            overall = 0.3 * magnitude_score + 0.3 * entropy_score + 0.2 * image_quality + 0.2 * ocr_confidence
        
        # Epistemic uncertainty: Do we have enough knowledge about this feature type?
        epistemic = 1.0 - overall
        
        # Aleatoric uncertainty: Image noise, lighting variations
        aleatoric = 1.0 - image_quality
        
        metrics = ConfidenceMetrics(
            overall=overall,
            components={
                "magnitude": magnitude_score if feature_vector is not None else 0.0,
                "entropy": entropy_score if feature_vector is not None else 0.0,
                "image_quality": image_quality,
                "ocr": ocr_confidence,
            },
            evidence_strength=image_quality,
            evidence_consistency=ocr_confidence,
            evidence_recency=1.0,  # Current image is always recent
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            agent_name="RealityAnchor",
            operation="extract_features",
        )
        
        self.chain.add_step(metrics)
        return metrics
    
    def evaluate_memory_retrieval(
        self,
        similarity_score: float,
        num_matches: int,
        pattern_age_days: float,
        pattern_accuracy: float = 1.0,
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence in Memory Atlas pattern retrieval.
        
        Args:
            similarity_score: Cosine similarity [0, 1]
            num_matches: Number of matching patterns found
            pattern_age_days: Age of retrieved pattern in days
            pattern_accuracy: Historical accuracy of this pattern
        
        Returns:
            ConfidenceMetrics for memory retrieval
        """
        # Confidence increases with similarity and number of matches
        similarity_conf = similarity_score
        coverage_conf = min(num_matches / 5.0, 1.0)  # Saturate at 5 matches
        
        # Recency factor: Exponential decay with 30-day half-life
        recency = np.exp(-pattern_age_days / 30.0)
        
        # Overall confidence
        overall = 0.4 * similarity_conf + 0.2 * coverage_conf + 0.2 * recency + 0.2 * pattern_accuracy
        
        # Epistemic: Are these patterns representative?
        epistemic = 1.0 - coverage_conf
        
        # Aleatoric: Pattern variability
        aleatoric = 1.0 - similarity_conf
        
        metrics = ConfidenceMetrics(
            overall=overall,
            components={
                "similarity": similarity_conf,
                "coverage": coverage_conf,
                "recency": recency,
                "accuracy": pattern_accuracy,
            },
            evidence_strength=similarity_conf,
            evidence_consistency=pattern_accuracy,
            evidence_recency=recency,
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            agent_name="MemoryAtlas",
            operation="retrieve_patterns",
        )
        
        self.chain.add_step(metrics)
        return metrics
    
    def evaluate_mismatch_detection(
        self,
        mismatch_delta: float,
        cycle_number: int,
        total_cycles: int,
        convergence_rate: float = 0.0,
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence in Theta Oscillator mismatch detection.
        
        Args:
            mismatch_delta: Computed mismatch Δ [0, ∞]
            cycle_number: Current oscillation cycle
            total_cycles: Total cycles to run
            convergence_rate: Rate of mismatch decay (negative = converging)
        
        Returns:
            ConfidenceMetrics for mismatch detection
        """
        # Confidence increases as mismatch becomes clear (not borderline)
        # Threshold is typically 0.3, so confidence peaks at extremes
        threshold = 0.3
        distance_from_threshold = abs(mismatch_delta - threshold)
        clarity_conf = min(distance_from_threshold / 0.3, 1.0)
        
        # Confidence increases with more cycles (more evidence)
        sampling_conf = cycle_number / total_cycles
        
        # Confidence increases if converging (stable result)
        convergence_conf = 1.0 - min(abs(convergence_rate), 1.0)
        
        overall = 0.4 * clarity_conf + 0.3 * sampling_conf + 0.3 * convergence_conf
        
        # Epistemic: Is this mismatch meaningful or noise?
        epistemic = 1.0 - clarity_conf
        
        # Aleatoric: Oscillation inherent randomness
        aleatoric = 1.0 - sampling_conf
        
        metrics = ConfidenceMetrics(
            overall=overall,
            components={
                "clarity": clarity_conf,
                "sampling": sampling_conf,
                "convergence": convergence_conf,
            },
            evidence_strength=clarity_conf,
            evidence_consistency=convergence_conf,
            evidence_recency=sampling_conf,
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            agent_name="ThetaOscillator",
            operation="detect_mismatch",
        )
        
        self.chain.add_step(metrics)
        return metrics
    
    def evaluate_map_integration(
        self,
        novelty_score: float,
        interaction_magnitude: float,
        version_count: int,
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence in Map Integration compositional learning.
        
        Args:
            novelty_score: How novel is the new experience [0, 1]
            interaction_magnitude: Strength of emergent interactions
            version_count: Number of versions in map history
        
        Returns:
            ConfidenceMetrics for map integration
        """
        # High novelty = uncertain (need more data)
        # Low novelty = confident (well-understood)
        familiarity_conf = 1.0 - novelty_score
        
        # Interaction strength indicates meaningful learning
        interaction_conf = min(interaction_magnitude, 1.0)
        
        # More versions = more experience = higher confidence
        experience_conf = min(version_count / 10.0, 1.0)
        
        overall = 0.4 * familiarity_conf + 0.3 * interaction_conf + 0.3 * experience_conf
        
        # Epistemic: Knowledge gap for novel patterns
        epistemic = novelty_score
        
        # Aleatoric: Inherent pattern variability
        aleatoric = 1.0 - interaction_conf
        
        metrics = ConfidenceMetrics(
            overall=overall,
            components={
                "familiarity": familiarity_conf,
                "interaction_strength": interaction_conf,
                "experience": experience_conf,
            },
            evidence_strength=familiarity_conf,
            evidence_consistency=experience_conf,
            evidence_recency=1.0,  # Current integration
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            agent_name="MapIntegration",
            operation="integrate_experience",
        )
        
        self.chain.add_step(metrics)
        return metrics
    
    def evaluate_hypothesis_generation(
        self,
        num_hypotheses: int,
        top_hypothesis_score: float,
        score_variance: float,
        evidence_count: int,
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence in Pathway Generator hypothesis generation.
        
        Args:
            num_hypotheses: Number of alternatives generated
            top_hypothesis_score: Score of best hypothesis [0, 1]
            score_variance: Variance in hypothesis scores
            evidence_count: Number of supporting evidence pieces
        
        Returns:
            ConfidenceMetrics for hypothesis generation
        """
        # Diversity: Having multiple hypotheses increases robustness
        diversity_conf = min(num_hypotheses / 5.0, 1.0)
        
        # Quality: Top hypothesis should be strong
        quality_conf = top_hypothesis_score
        
        # Separation: Large variance = clear winner
        separation_conf = min(score_variance / 0.1, 1.0)
        
        # Evidence: More evidence = higher confidence
        evidence_conf = min(evidence_count / 3.0, 1.0)
        
        overall = 0.3 * diversity_conf + 0.3 * quality_conf + 0.2 * separation_conf + 0.2 * evidence_conf
        
        # Epistemic: Lack of evidence or diversity
        epistemic = 1.0 - max(diversity_conf, evidence_conf)
        
        # Aleatoric: Score variance (ambiguity)
        aleatoric = 1.0 - separation_conf
        
        metrics = ConfidenceMetrics(
            overall=overall,
            components={
                "diversity": diversity_conf,
                "quality": quality_conf,
                "separation": separation_conf,
                "evidence": evidence_conf,
            },
            evidence_strength=quality_conf,
            evidence_consistency=separation_conf,
            evidence_recency=1.0,
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            agent_name="PathwayGenerator",
            operation="generate_hypotheses",
        )
        
        self.chain.add_step(metrics)
        return metrics
    
    def evaluate_anticipatory_simulation(
        self,
        cache_hit: bool,
        similarity_threshold: float,
        cache_size: int,
        gap_coverage: float = 0.5,
    ) -> ConfidenceMetrics:
        """
        Evaluate confidence in Anticipatory Simulation pre-wiring.
        
        Args:
            cache_hit: Whether cache had a hit
            similarity_threshold: Similarity to cached scenario [0, 1]
            cache_size: Number of pre-computed scenarios
            gap_coverage: Fraction of knowledge gaps covered
        
        Returns:
            ConfidenceMetrics for anticipatory simulation
        """
        if cache_hit:
            # Cache hit = high confidence
            match_conf = similarity_threshold
            preparedness_conf = 1.0
        else:
            # Cache miss = lower confidence
            match_conf = 0.0
            preparedness_conf = 0.5
        
        # Larger cache = better coverage
        coverage_conf = min(cache_size / 50.0, 1.0)
        
        overall = 0.4 * match_conf + 0.3 * preparedness_conf + 0.3 * gap_coverage
        
        # Epistemic: Knowledge gaps
        epistemic = 1.0 - gap_coverage
        
        # Aleatoric: Scenario variability
        aleatoric = 1.0 - match_conf if cache_hit else 0.5
        
        metrics = ConfidenceMetrics(
            overall=overall,
            components={
                "cache_match": match_conf,
                "preparedness": preparedness_conf,
                "coverage": coverage_conf,
                "gap_coverage": gap_coverage,
            },
            evidence_strength=match_conf,
            evidence_consistency=coverage_conf,
            evidence_recency=1.0 if cache_hit else 0.5,
            aleatoric_uncertainty=aleatoric,
            epistemic_uncertainty=epistemic,
            agent_name="AnticipatorySimulation",
            operation="check_cache",
        )
        
        self.chain.add_step(metrics)
        return metrics
    
    @staticmethod
    def _compute_entropy(vector: np.ndarray) -> float:
        """Compute Shannon entropy of a vector."""
        # Normalize to probability distribution
        probs = np.abs(vector) + 1e-10
        probs = probs / probs.sum()
        
        # Shannon entropy
        entropy = -np.sum(probs * np.log(probs + 1e-10))
        return float(entropy)
    
    def reset(self):
        """Reset confidence chain for new analysis."""
        self.chain = ConfidenceChain()
    
    def get_confidence_chain(self) -> ConfidenceChain:
        """Get the current confidence chain."""
        return self.chain
    
    def export_report(self, filepath: str):
        """Export confidence report to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.chain.to_dict(), f, indent=2)


# Convenience function for quick confidence reporting
def summarize_confidence(evaluator: ConfidenceEvaluator) -> Dict:
    """Generate a summary of confidence metrics."""
    chain = evaluator.get_confidence_chain()
    
    return {
        "final_confidence": chain.get_final_confidence(),
        "total_steps": len(chain.steps),
        "bottleneck": chain.get_bottleneck().agent_name if chain.get_bottleneck() else None,
        "uncertainty": chain.get_uncertainty_breakdown(),
        "step_confidences": [s.overall for s in chain.steps],
        "report": chain.generate_report(),
    }
