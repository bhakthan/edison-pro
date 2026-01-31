"""
Memory Atlas Agent
Maintains versioned "cognitive maps" of successful analysis patterns from historical diagrams.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import pickle


@dataclass
class AnalysisPattern:
    """Represents a stored analysis pattern in the Memory Atlas"""
    pattern_id: str
    features: np.ndarray
    domain: str  # electrical, mechanical, P&ID, civil, etc.
    components: List[Dict[str, Any]]
    accuracy: float
    timestamp: str
    contexts: List[str]  # When to use this pattern
    version_id: str
    parent_version: Optional[str] = None
    success_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'pattern_id': self.pattern_id,
            'features': self.features.tolist(),
            'domain': self.domain,
            'components': self.components,
            'accuracy': self.accuracy,
            'timestamp': self.timestamp,
            'contexts': self.contexts,
            'version_id': self.version_id,
            'parent_version': self.parent_version,
            'success_count': self.success_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisPattern':
        """Create from dictionary"""
        data['features'] = np.array(data['features'])
        return cls(**data)


class MemoryAtlasAgent:
    """
    Maintain versioned cognitive maps of analysis patterns.
    Stores successful interpretations and retrieves relevant historical knowledge.
    """
    
    def __init__(self, storage_path: str = "./memory_atlas", use_vector_db: bool = False):
        """
        Initialize Memory Atlas
        
        Args:
            storage_path: Directory to store pattern files
            use_vector_db: Whether to use vector database (Azure AI Search)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.use_vector_db = use_vector_db
        
        # In-memory cache of patterns
        self.patterns: Dict[str, AnalysisPattern] = {}
        
        # Domain-specific maps
        self.domain_maps: Dict[str, List[str]] = {
            'electrical': [],
            'mechanical': [],
            'pid': [],
            'civil': [],
            'structural': [],
            'hybrid': [],
            'general': []
        }
        
        # Version control
        self.version_counter = 0
        
        # Load existing patterns from JSON
        self._load_patterns()
        
        # Initialize Azure Search if enabled
        self.azure_atlas = None
        if use_vector_db:
            try:
                from agents.azure_memory_atlas import create_azure_memory_atlas
                self.azure_atlas = create_azure_memory_atlas()
                if self.azure_atlas:
                    print("✅ Memory Atlas: Azure AI Search enabled")
                else:
                    print("⚠️  Memory Atlas: Azure Search unavailable, using JSON only")
            except ImportError:
                print("⚠️  Memory Atlas: azure_memory_atlas not found, using JSON only")
    
    def retrieve(
        self, 
        query_features: Any,  # FeatureVector or np.ndarray
        top_k: int = 5,
        domain: Optional[str] = None,
        context: Optional[str] = None
    ) -> List[Tuple[AnalysisPattern, float]]:
        """
        Retrieve most relevant historical patterns
        
        Uses Azure AI Search if enabled, falls back to local JSON.
        
        Args:
            query_features: Current diagram features (FeatureVector or embedding)
            top_k: Number of top matches to return
            domain: Optional domain filter (electrical, mechanical, etc.)
            context: Optional context filter (standard_layout, space_constrained, etc.)
            
        Returns:
            List of (pattern, score) tuples, sorted by score descending
        """
        # Extract embedding
        if hasattr(query_features, 'embedding'):
            query_embedding = query_features.embedding
        elif isinstance(query_features, np.ndarray):
            query_embedding = query_features
        else:
            raise ValueError("query_features must be FeatureVector or np.ndarray")
        
        if query_embedding is None:
            return []
        
        # Try Azure Search first if enabled
        if self.azure_atlas and self.azure_atlas.is_available():
            try:
                azure_results = self.azure_atlas.retrieve_similar(
                    query_embedding=query_embedding,
                    domain=domain,
                    top_k=top_k,
                    min_accuracy=0.0,
                    contexts=[context] if context else None
                )
                
                if azure_results:
                    # Convert Azure results to (pattern, score) tuples
                    results = []
                    for result in azure_results:
                        # Reconstruct AnalysisPattern from Azure result
                        pattern = AnalysisPattern(
                            pattern_id=result["pattern_id"],
                            features=np.array(result["pattern_data"]["features"]),
                            domain=result["domain"],
                            components=result["components"],
                            accuracy=result["accuracy"],
                            timestamp=result["timestamp"],
                            contexts=result["contexts"],
                            version_id=result["version_id"],
                            parent_version=result.get("parent_version"),
                            success_count=result.get("success_count", 0)
                        )
                        
                        score = result.get("similarity_score", 0.0)
                        results.append((pattern, score))
                        
                        # Update usage stats
                        self.azure_atlas.update_usage_stats(
                            pattern_id=result["pattern_id"],
                            version_id=result["version_id"],
                            similarity_score=score
                        )
                    
                    print(f"🔍 Retrieved {len(results)} patterns from Azure AI Search")
                    return results
                    
            except Exception as e:
                print(f"⚠️  Azure Search retrieval failed: {e}, falling back to JSON")
        
        # Fallback to local JSON retrieval
        # Filter patterns by domain if specified
        candidate_patterns = []
        for pattern_id, pattern in self.patterns.items():
            if domain and pattern.domain != domain and pattern.domain != 'hybrid':
                continue
            if context and context not in pattern.contexts:
                continue
            candidate_patterns.append(pattern)
        
        # Score each candidate
        scored = []
        for pattern in candidate_patterns:
            score = self._compute_similarity_score(
                query_embedding,
                pattern,
                domain=domain,
                context=context
            )
            scored.append((pattern, score))
        
        # Sort by score and return top-k
        scored.sort(key=lambda x: x[1], reverse=True)
        print(f"🔍 Retrieved {len(scored[:top_k])} patterns from local JSON")
        return scored[:top_k]
    
    def _compute_similarity_score(
        self,
        query_embedding: np.ndarray,
        pattern: AnalysisPattern,
        domain: Optional[str] = None,
        context: Optional[str] = None
    ) -> float:
        """
        Compute composite similarity score
        
        Score = α₁·cosine_sim + α₂·temporal_decay + α₃·accuracy + α₄·context_match
        """
        # Cosine similarity (α₁ = 0.5)
        cosine_sim = self._cosine_similarity(query_embedding, pattern.features)
        
        # Temporal decay (α₂ = 0.2) - newer patterns weighted higher
        age_days = self._compute_age_days(pattern.timestamp)
        temporal_decay = np.exp(-0.01 * age_days)  # Decay with λ=0.01
        
        # Accuracy weight (α₃ = 0.2)
        accuracy_weight = pattern.accuracy
        
        # Context match (α₄ = 0.1)
        context_match = 1.0 if context and context in pattern.contexts else 0.5
        
        # Success frequency bonus
        success_bonus = min(0.1, pattern.success_count * 0.01)
        
        # Composite score
        score = (
            0.5 * cosine_sim
            + 0.2 * temporal_decay
            + 0.2 * accuracy_weight
            + 0.1 * context_match
            + success_bonus
        )
        
        return score
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _compute_age_days(self, timestamp: str) -> float:
        """Compute age in days from timestamp"""
        try:
            pattern_time = datetime.fromisoformat(timestamp)
            age = datetime.now() - pattern_time
            return age.total_seconds() / 86400.0  # Convert to days
        except:
            return 0.0
    
    def store(
        self,
        analysis_result: Dict[str, Any],
        features: Any,  # FeatureVector or np.ndarray
        domain: str = 'general',
        contexts: Optional[List[str]] = None
    ) -> str:
        """
        Store new successful pattern in atlas
        
        Args:
            analysis_result: Analysis results to store
            features: Feature vector from Reality Anchor
            domain: Domain classification
            contexts: Context rules for when to use this pattern
            
        Returns:
            pattern_id of stored pattern
        """
        # Extract embedding
        if hasattr(features, 'embedding'):
            embedding = features.embedding
        elif isinstance(features, np.ndarray):
            embedding = features
        else:
            raise ValueError("features must be FeatureVector or np.ndarray")
        
        # Generate pattern ID
        pattern_id = self._generate_pattern_id(domain)
        
        # Create version ID
        self.version_counter += 1
        version_id = f"v{self.version_counter}"
        
        # Create pattern
        pattern = AnalysisPattern(
            pattern_id=pattern_id,
            features=embedding,
            domain=domain,
            components=analysis_result.get('components', []),
            accuracy=analysis_result.get('accuracy', 0.9),
            timestamp=datetime.now().isoformat(),
            contexts=contexts or ['general'],
            version_id=version_id,
            parent_version=None,
            success_count=1
        )
        
        # Store in memory
        self.patterns[pattern_id] = pattern
        
        # Add to domain map
        if domain in self.domain_maps:
            self.domain_maps[domain].append(pattern_id)
        
        # Persist to disk (JSON backup)
        self._save_pattern(pattern)
        
        # Upload to Azure Search if enabled
        if self.azure_atlas and self.azure_atlas.is_available():
            try:
                self.azure_atlas.store_pattern(
                    pattern_id=pattern_id,
                    version_id=version_id,
                    feature_embedding=embedding,
                    domain=domain,
                    components=analysis_result.get('components', []),
                    accuracy=analysis_result.get('accuracy', 0.9),
                    contexts=contexts or ['general'],
                    parent_version=None,
                    confidence_score=analysis_result.get('confidence', 1.0),
                    source_diagram_id=analysis_result.get('diagram_id'),
                    interpretation_summary=analysis_result.get('interpretation', {}).get('explanation', '')
                )
            except Exception as e:
                print(f"⚠️  Failed to store pattern in Azure Search: {e}")
        
        return pattern_id
    
    def update_pattern(
        self,
        pattern_id: str,
        new_features: np.ndarray,
        new_components: List[Dict[str, Any]],
        parent_version: str
    ) -> str:
        """
        Create new version of existing pattern (for Map Integration)
        
        Args:
            pattern_id: ID of pattern to update
            new_features: Updated feature vector
            new_components: Updated component list
            parent_version: Version ID of parent
            
        Returns:
            New version_id
        """
        if pattern_id not in self.patterns:
            raise ValueError(f"Pattern {pattern_id} not found")
        
        old_pattern = self.patterns[pattern_id]
        
        # Create new version
        self.version_counter += 1
        new_version_id = f"v{self.version_counter}"
        
        # Create updated pattern
        updated_pattern = AnalysisPattern(
            pattern_id=pattern_id,
            features=new_features,
            domain=old_pattern.domain,
            components=new_components,
            accuracy=old_pattern.accuracy,
            timestamp=datetime.now().isoformat(),
            contexts=old_pattern.contexts,
            version_id=new_version_id,
            parent_version=parent_version,
            success_count=old_pattern.success_count + 1
        )
        
        # Update in memory (replace old version)
        self.patterns[pattern_id] = updated_pattern
        
        # Persist to disk
        self._save_pattern(updated_pattern)
        
        return new_version_id
    
    def _generate_pattern_id(self, domain: str) -> str:
        """Generate unique pattern ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{domain}_{timestamp}_{len(self.patterns)}"
    
    def _save_pattern(self, pattern: AnalysisPattern):
        """Save pattern to disk"""
        pattern_file = self.storage_path / f"{pattern.pattern_id}.json"
        with open(pattern_file, 'w') as f:
            json.dump(pattern.to_dict(), f, indent=2)
    
    def _load_patterns(self):
        """Load existing patterns from disk"""
        if not self.storage_path.exists():
            return
        
        for pattern_file in self.storage_path.glob("*.json"):
            try:
                with open(pattern_file, 'r') as f:
                    data = json.load(f)
                    pattern = AnalysisPattern.from_dict(data)
                    self.patterns[pattern.pattern_id] = pattern
                    
                    # Update domain map
                    if pattern.domain in self.domain_maps:
                        self.domain_maps[pattern.domain].append(pattern.pattern_id)
                    
                    # Update version counter
                    if pattern.version_id.startswith('v'):
                        version_num = int(pattern.version_id[1:])
                        self.version_counter = max(self.version_counter, version_num)
            except Exception as e:
                print(f"⚠️  Failed to load pattern {pattern_file}: {e}")
    
    def get_all_patterns(self) -> List[AnalysisPattern]:
        """Get all stored patterns"""
        return list(self.patterns.values())
    
    def get_patterns_by_domain(self, domain: str) -> List[AnalysisPattern]:
        """Get all patterns for a specific domain"""
        return [
            self.patterns[pid] 
            for pid in self.domain_maps.get(domain, [])
            if pid in self.patterns
        ]
    
    def clear_cache(self):
        """Clear in-memory cache"""
        self.patterns.clear()
        for domain in self.domain_maps:
            self.domain_maps[domain].clear()
