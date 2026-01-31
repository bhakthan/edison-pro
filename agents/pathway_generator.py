"""
Pathway Generator Agent
Generates multiple interpretation hypotheses for ambiguous diagram elements.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Hypothesis:
    """Represents an interpretation hypothesis"""
    type: str
    probability: float
    rationale: str
    supporting_evidence: List[Dict[str, Any]]
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'type': self.type,
            'probability': float(self.probability),
            'rationale': self.rationale,
            'supporting_evidence': self.supporting_evidence,
            'rank': self.rank
        }


class PathwayGeneratorAgent:
    """
    Generate multiple interpretation hypotheses for ambiguous elements.
    Explores alternative "detours" through interpretation space.
    """
    
    def __init__(self, hypothesis_engine=None, memory_atlas=None, context_analyzer=None):
        """
        Initialize Pathway Generator
        
        Args:
            hypothesis_engine: Engine for generating candidate hypotheses
            memory_atlas: MemoryAtlasAgent for retrieving priors
            context_analyzer: Analyzer for contextual compatibility
        """
        self.engine = hypothesis_engine
        self.atlas = memory_atlas
        self.context = context_analyzer
        
    def generate_alternatives(
        self,
        ambiguous_element: Dict[str, Any],
        surrounding_context: Dict[str, Any],
        top_k: int = 5
    ) -> List[Hypothesis]:
        """
        Explore multiple interpretation paths for ambiguous element
        
        Args:
            ambiguous_element: Element features to interpret
            surrounding_context: Context from surrounding diagram
            top_k: Number of top hypotheses to return
            
        Returns:
            Ranked list of hypotheses with probabilities
        """
        # Generate candidate hypotheses
        candidates = self._propose_candidates(ambiguous_element, surrounding_context)
        
        # Score each hypothesis
        scored_hypotheses = []
        for h in candidates:
            score = self.score_hypothesis(h, surrounding_context)
            h.probability = score
            scored_hypotheses.append(h)
        
        # Rank by probability
        ranked = sorted(scored_hypotheses, key=lambda h: h.probability, reverse=True)
        
        # Assign ranks
        for i, h in enumerate(ranked):
            h.rank = i + 1
        
        return ranked[:top_k]
    
    def _propose_candidates(
        self,
        element: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Hypothesis]:
        """
        Generate candidate hypotheses for an element
        
        For now, uses simple heuristics. Will be enhanced with ML/LLM.
        """
        candidates = []
        
        # Example: If circular symbol with "M"
        element_type = element.get('type', 'unknown')
        text = element.get('text', '')
        
        if 'M' in text.upper() or element_type == 'circular_with_m':
            candidates.extend([
                Hypothesis(
                    type='electric_motor',
                    probability=0.0,  # Will be scored
                    rationale='M commonly denotes motor in electrical diagrams',
                    supporting_evidence=[]
                ),
                Hypothesis(
                    type='mixer',
                    probability=0.0,
                    rationale='M denotes mixer in P&ID context',
                    supporting_evidence=[]
                ),
                Hypothesis(
                    type='meter',
                    probability=0.0,
                    rationale='M sometimes indicates measurement device',
                    supporting_evidence=[]
                )
            ])
        else:
            # Generic candidates
            candidates.extend([
                Hypothesis(
                    type='unknown_component',
                    probability=0.0,
                    rationale='Generic component',
                    supporting_evidence=[]
                ),
                Hypothesis(
                    type='connector',
                    probability=0.0,
                    rationale='Possible connection point',
                    supporting_evidence=[]
                )
            ])
        
        return candidates
    
    def score_hypothesis(
        self,
        hypothesis: Hypothesis,
        context: Dict[str, Any]
    ) -> float:
        """
        Compute likelihood of hypothesis given context
        
        Score = α₁·local_similarity + α₂·neighbor_compatibility + α₃·prior + α₄·evidence
        """
        # Weights (sum to 1.0)
        alpha1 = 0.4  # Local similarity
        alpha2 = 0.3  # Neighbor compatibility
        alpha3 = 0.2  # Prior probability
        alpha4 = 0.1  # Evidence strength
        
        # Local similarity (placeholder)
        local_score = self._compute_local_similarity(hypothesis, context)
        
        # Neighbor compatibility
        neighbor_score = self._check_compatibility(hypothesis, context)
        
        # Prior from memory atlas
        prior_score = self._get_prior_probability(hypothesis, context)
        
        # Evidence strength
        evidence_score = len(hypothesis.supporting_evidence) / 10.0  # Normalize
        
        # Composite score
        total_score = (
            alpha1 * local_score
            + alpha2 * neighbor_score
            + alpha3 * prior_score
            + alpha4 * evidence_score
        )
        
        # Apply softmax in generate_alternatives to normalize
        return total_score
    
    def _compute_local_similarity(
        self,
        hypothesis: Hypothesis,
        context: Dict[str, Any]
    ) -> float:
        """Compute similarity between hypothesis and local features"""
        # Simplified scoring based on hypothesis type and context domain
        domain = context.get('domain', 'general')
        h_type = hypothesis.type
        
        # Domain-specific scoring
        if domain == 'electrical' and h_type == 'electric_motor':
            return 0.8
        elif domain == 'pid' and h_type == 'mixer':
            return 0.8
        elif domain == 'electrical' and h_type == 'meter':
            return 0.6
        else:
            return 0.5
    
    def _check_compatibility(
        self,
        hypothesis: Hypothesis,
        context: Dict[str, Any]
    ) -> float:
        """Check compatibility with neighboring elements"""
        neighbors = context.get('neighbors', [])
        
        if not neighbors:
            return 0.5  # Neutral if no neighbors
        
        # Check engineering rules (simplified)
        h_type = hypothesis.type
        compatible_count = 0
        
        for neighbor in neighbors:
            neighbor_type = neighbor.get('type', 'unknown')
            
            # Example rules
            if h_type == 'electric_motor' and 'power' in neighbor_type:
                compatible_count += 1
            elif h_type == 'mixer' and 'flow' in neighbor_type:
                compatible_count += 1
        
        return compatible_count / len(neighbors) if neighbors else 0.5
    
    def _get_prior_probability(
        self,
        hypothesis: Hypothesis,
        context: Dict[str, Any]
    ) -> float:
        """Get prior probability from memory atlas"""
        if not self.atlas:
            return 0.5  # Uniform prior if no atlas
        
        # Query atlas for frequency of this hypothesis type
        domain = context.get('domain', 'general')
        patterns = self.atlas.get_patterns_by_domain(domain)
        
        if not patterns:
            return 0.5
        
        # Count how often this hypothesis type appears
        h_type = hypothesis.type
        type_count = sum(
            1 for p in patterns
            if any(c.get('type') == h_type for c in p.components)
        )
        
        prior = type_count / len(patterns) if patterns else 0.5
        return min(prior, 0.9)  # Cap at 0.9
    
    def find_evidence(
        self,
        hypothesis: Hypothesis,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Retrieve supporting examples from history"""
        if not self.atlas:
            return []
        
        domain = context.get('domain', 'general')
        patterns = self.atlas.get_patterns_by_domain(domain)
        
        evidence = []
        h_type = hypothesis.type
        
        for pattern in patterns[:3]:  # Top 3 examples
            # Check if pattern contains this hypothesis type
            matching_components = [
                c for c in pattern.components
                if c.get('type') == h_type
            ]
            
            if matching_components:
                evidence.append({
                    'pattern_id': pattern.pattern_id,
                    'domain': pattern.domain,
                    'accuracy': pattern.accuracy,
                    'components': matching_components
                })
        
        return evidence
    
    def visualize_pathways(
        self,
        hypotheses: List[Hypothesis]
    ) -> str:
        """
        Generate text visualization of alternative pathways
        
        Returns ASCII art showing decision tree
        """
        lines = []
        lines.append("🌳 Alternative Interpretation Pathways:")
        lines.append("")
        
        for h in hypotheses:
            bar_length = int(h.probability * 40)
            bar = "█" * bar_length + "░" * (40 - bar_length)
            
            lines.append(f"  {h.rank}. {h.type}")
            lines.append(f"     {bar} {h.probability:.2%}")
            lines.append(f"     {h.rationale}")
            
            if h.supporting_evidence:
                lines.append(f"     Evidence: {len(h.supporting_evidence)} examples")
            
            lines.append("")
        
        return "\n".join(lines)
