"""
Map Integration Agent
Creates updated cognitive maps through compositional learning when encountering novel patterns.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MapUpdateEvent:
    """Represents a map update event"""
    map_id: str
    version_id: str
    parent_version: str
    mismatch_score: float
    novel_features: np.ndarray
    timestamp: str
    contexts: List[str]


class MapIntegrationAgent:
    """
    Create composite maps from old + new knowledge (not replacement).
    
    Formula: Map_new = λ·Map_old + (1-λ)·Experience_new + β·Interaction(old, new)
    """
    
    def __init__(
        self,
        memory_atlas,
        lambda_decay: float = 0.7,
        beta_interaction: float = 0.2
    ):
        """
        Initialize Map Integration
        
        Args:
            memory_atlas: MemoryAtlasAgent instance
            lambda_decay: Weight for preserving old knowledge (0.0-1.0)
            beta_interaction: Weight for emergent feature interactions (0.0-0.3)
        """
        self.atlas = memory_atlas
        self.lambda_decay = lambda_decay
        self.beta_interaction = beta_interaction
        self.update_history: List[MapUpdateEvent] = []
        
    def integrate_new_experience(
        self,
        mismatch_event: Dict[str, Any],
        current_features: Any,
        domain: Optional[str] = None
    ) -> str:
        """
        Create composite map from old + new when novelty detected
        
        Args:
            mismatch_event: Event from Theta Oscillator with mismatch details
            current_features: Current diagram features (FeatureVector)
            domain: Optional domain classification
            
        Returns:
            New version_id of updated map
        """
        # Extract current features
        if hasattr(current_features, 'embedding'):
            F_current = current_features.embedding
        elif isinstance(current_features, np.ndarray):
            F_current = current_features
        else:
            raise ValueError("current_features must be FeatureVector or np.ndarray")
        
        if F_current is None:
            raise ValueError("Features embedding is None")
        
        # Retrieve relevant memory pattern
        memory_results = self.atlas.retrieve(
            current_features,
            top_k=1,
            domain=domain
        )
        
        if not memory_results:
            # No existing pattern - store as new
            print("  📝 No existing pattern found - creating new map")
            pattern_id = self.atlas.store(
                analysis_result={'components': [], 'accuracy': 0.8},
                features=F_current,
                domain=domain or 'general',
                contexts=['general']
            )
            return f"new_{pattern_id}"
        
        memory_pattern, score = memory_results[0]
        F_memory = memory_pattern.features
        
        # Extract novel component
        F_novel = F_current - F_memory
        
        # Compositional update: Map_new = λ·Map_old + (1-λ)·F_novel + β·Interaction
        interaction_term = self.compute_interaction(F_memory, F_novel)
        
        Map_new = (
            self.lambda_decay * F_memory
            + (1 - self.lambda_decay) * F_novel
            + self.beta_interaction * interaction_term
        )
        
        # Normalize
        norm = np.linalg.norm(Map_new)
        if norm > 0:
            Map_new = Map_new / norm
        
        # Derive contexts for when to use this map
        contexts = self.derive_contexts(current_features, F_novel, mismatch_event)
        
        # Update pattern in memory atlas
        new_version_id = self.atlas.update_pattern(
            pattern_id=memory_pattern.pattern_id,
            new_features=Map_new,
            new_components=[],  # TODO: Extract actual components
            parent_version=memory_pattern.version_id
        )
        
        # Record update event
        update_event = MapUpdateEvent(
            map_id=memory_pattern.pattern_id,
            version_id=new_version_id,
            parent_version=memory_pattern.version_id,
            mismatch_score=mismatch_event.get('mismatch_score', 0.0),
            novel_features=F_novel,
            timestamp=datetime.now().isoformat(),
            contexts=contexts
        )
        self.update_history.append(update_event)
        
        print(f"  ✅ Map updated: {memory_pattern.pattern_id} → {new_version_id}")
        print(f"     Contexts: {', '.join(contexts)}")
        
        return new_version_id
    
    def compute_interaction(
        self,
        old_features: np.ndarray,
        new_features: np.ndarray
    ) -> np.ndarray:
        """
        Detect emergent patterns from combining old + new
        
        Uses element-wise product to capture feature interactions
        """
        # Element-wise product (Hadamard product)
        interaction = old_features * new_features
        
        # Alternative: Outer product for full interaction (expensive)
        # interaction_matrix = np.outer(old_features, new_features)
        # interaction = interaction_matrix.flatten()[:len(old_features)]
        
        return interaction
    
    def derive_contexts(
        self,
        current_features: Any,
        novel_features: np.ndarray,
        mismatch_event: Dict[str, Any]
    ) -> List[str]:
        """
        Determine when to use this updated map vs old maps
        
        Returns list of context tags
        """
        contexts = ['general']
        
        # Analyze novel features to infer contexts
        novelty_level = mismatch_event.get('novelty_level', 'medium')
        
        if novelty_level in ['high', 'critical']:
            contexts.append('high_novelty')
        
        # Check feature characteristics (simplified)
        if hasattr(current_features, 'visual_elements'):
            num_elements = len(current_features.visual_elements)
            if num_elements > 50:
                contexts.append('complex_diagram')
            elif num_elements < 10:
                contexts.append('simple_diagram')
        
        # Spatial characteristics
        if hasattr(current_features, 'spatial_layout'):
            density = current_features.spatial_layout.get('spatial_density', 0)
            if density > 0.5:
                contexts.append('high_density')
            elif density < 0.1:
                contexts.append('space_constrained')
        
        return contexts
    
    def get_update_history(self) -> List[Dict[str, Any]]:
        """Get history of map updates"""
        return [
            {
                'map_id': event.map_id,
                'version_id': event.version_id,
                'parent_version': event.parent_version,
                'mismatch_score': float(event.mismatch_score),
                'timestamp': event.timestamp,
                'contexts': event.contexts
            }
            for event in self.update_history
        ]
    
    def get_version_lineage(self, pattern_id: str) -> List[str]:
        """
        Get version history for a pattern (like git log)
        
        Args:
            pattern_id: Pattern to trace
            
        Returns:
            List of version IDs from oldest to newest
        """
        lineage = []
        
        # Find all updates for this pattern
        updates = [
            event for event in self.update_history
            if event.map_id == pattern_id
        ]
        
        # Sort by timestamp
        updates.sort(key=lambda e: e.timestamp)
        
        for update in updates:
            lineage.append(update.version_id)
        
        return lineage
