"""
Theta Oscillator Agent (CORE INNOVATION)
Orchestrates rhythmic switching between Reality Anchor and Memory Atlas at high frequency.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class AttentionState:
    """Represents attention state at a specific cycle"""
    cycle: int
    alpha: float  # Modulation coefficient
    attention: np.ndarray
    source: str  # 'reality' or 'memory'
    timestamp: float
    mismatch: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'cycle': self.cycle,
            'alpha': float(self.alpha),
            'attention': self.attention.tolist() if self.attention is not None else None,
            'source': self.source,
            'timestamp': self.timestamp,
            'mismatch': float(self.mismatch) if self.mismatch is not None else None
        }


@dataclass
class MismatchEvent:
    """Represents a detected mismatch/novelty event"""
    cycle: int
    mismatch_score: float
    features_reality: np.ndarray
    features_memory: np.ndarray
    timestamp: str
    novelty_level: str  # 'low', 'medium', 'high', 'critical'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'cycle': self.cycle,
            'mismatch_score': float(self.mismatch_score),
            'timestamp': self.timestamp,
            'novelty_level': self.novelty_level
        }


class ThetaOscillatorAgent:
    """
    CORE INNOVATION: Orchestrate rhythmic flickering between reality and memory.
    
    Implements theta-rhythm-inspired oscillation:
    - α(t) = 0.5 + 0.5·sin(2πf_θ t)
    - S(t) = α(t)·R(t) + (1-α(t))·M(t)
    """
    
    def __init__(
        self,
        reality_agent,
        memory_agent,
        frequency_hz: float = 8.0,
        mismatch_threshold: float = 0.3
    ):
        """
        Initialize Theta Oscillator
        
        Args:
            reality_agent: RealityAnchorAgent instance
            memory_agent: MemoryAtlasAgent instance
            frequency_hz: Theta oscillation frequency (4-10 Hz)
            mismatch_threshold: Threshold for triggering learning (0.0-1.0)
        """
        self.reality = reality_agent
        self.memory = memory_agent
        self.f_theta = frequency_hz
        self.mismatch_threshold = mismatch_threshold
        self.cycle_count = 0
        
    def analyze_with_flickering(
        self,
        diagram: Any,
        num_cycles: int = 100,
        domain: Optional[str] = None,
        return_trace: bool = True
    ) -> Dict[str, Any]:
        """
        Main flickering analysis loop
        
        Args:
            diagram: Diagram image (file path, PIL Image, or base64)
            num_cycles: Number of oscillation cycles to run
            domain: Optional domain hint for memory retrieval
            return_trace: Whether to return full attention trace
            
        Returns:
            Analysis results with interpretation, mismatch events, attention trace
        """
        start_time = time.time()
        
        # Phase 1: Extract current features (Reality Anchor)
        print(f"🎯 Reality Anchor: Extracting features from current diagram...")
        F_current = self.reality.analyze(diagram, use_vision=False)
        
        # Initialize traces
        attention_trace = []
        mismatch_events = []
        
        # Phase 2: Flickering Loop
        print(f"🌊 Theta Oscillator: Starting {num_cycles} oscillation cycles at {self.f_theta} Hz...")
        
        for cycle in range(num_cycles):
            t = cycle / self.f_theta  # Time in seconds
            alpha = self.compute_alpha(t)
            
            if cycle % 2 == 0:  # Reality phase
                attention = alpha * F_current.embedding if F_current.embedding is not None else None
                source = 'reality'
                memory_pattern = None
                
            else:  # Memory phase
                # Query memory atlas
                memory_results = self.memory.retrieve(
                    F_current,
                    top_k=1,
                    domain=domain
                )
                
                if memory_results:
                    memory_pattern, score = memory_results[0]
                    attention = (1 - alpha) * memory_pattern.features
                else:
                    # No memory found, use zero vector
                    attention = np.zeros_like(F_current.embedding) if F_current.embedding is not None else None
                    memory_pattern = None
                
                source = 'memory'
            
            # Record attention state
            state = AttentionState(
                cycle=cycle,
                alpha=alpha,
                attention=attention,
                source=source,
                timestamp=time.time()
            )
            
            # Compute mismatch after memory phase
            if cycle > 0 and cycle % 2 == 1 and len(attention_trace) > 0:
                mismatch = self.compute_mismatch(
                    attention_trace[-1].attention,  # Reality from previous cycle
                    attention  # Memory from current cycle
                )
                state.mismatch = mismatch
                
                # Check if mismatch exceeds threshold
                if mismatch > self.mismatch_threshold:
                    novelty_level = self._classify_novelty(mismatch)
                    event = MismatchEvent(
                        cycle=cycle,
                        mismatch_score=mismatch,
                        features_reality=attention_trace[-1].attention,
                        features_memory=attention,
                        timestamp=datetime.now().isoformat(),
                        novelty_level=novelty_level
                    )
                    mismatch_events.append(event)
                    
                    if novelty_level in ['high', 'critical']:
                        print(f"  ⚡ Cycle {cycle}: High novelty detected (Δ={mismatch:.3f})")
            
            attention_trace.append(state)
            
            # Progress indicator (every 20 cycles)
            if cycle > 0 and cycle % 20 == 0:
                avg_mismatch = np.mean([s.mismatch for s in attention_trace if s.mismatch is not None])
                print(f"  📊 Cycle {cycle}/{num_cycles}: Avg mismatch = {avg_mismatch:.3f}")
        
        # Phase 3: Synthesize final interpretation
        print(f"🔮 Synthesizing final interpretation from {len(attention_trace)} cycles...")
        interpretation = self.synthesize_interpretation(
            attention_trace,
            F_current,
            mismatch_events
        )
        
        elapsed_time = time.time() - start_time
        
        # Prepare results
        results = {
            'interpretation': interpretation,
            'mismatch_events': [e.to_dict() for e in mismatch_events],
            'num_cycles': num_cycles,
            'num_mismatches': len(mismatch_events),
            'theta_frequency': self.f_theta,
            'latency_ms': int(elapsed_time * 1000),
            'convergence_cycle': self._detect_convergence(attention_trace)
        }
        
        if return_trace:
            results['attention_trace'] = [s.to_dict() for s in attention_trace]
        
        return results
    
    def compute_alpha(self, t: float) -> float:
        """
        Compute theta rhythm modulation coefficient
        
        α(t) = 0.5 + 0.5·sin(2πf_θ t)
        
        Returns value in [0, 1]
        """
        return 0.5 + 0.5 * np.sin(2 * np.pi * self.f_theta * t)
    
    def compute_mismatch(
        self,
        attention_reality: Optional[np.ndarray],
        attention_memory: Optional[np.ndarray]
    ) -> float:
        """
        Compute mismatch between reality and memory attention
        
        Δ = ||R - M||₂ / ||R||₂
        
        Returns normalized Euclidean distance in [0, ∞)
        """
        if attention_reality is None or attention_memory is None:
            return 0.0
        
        delta = np.linalg.norm(attention_reality - attention_memory)
        norm_reality = np.linalg.norm(attention_reality)
        
        if norm_reality < 1e-8:
            return 0.0
        
        normalized_delta = delta / norm_reality
        return normalized_delta
    
    def _classify_novelty(self, mismatch: float) -> str:
        """Classify novelty level based on mismatch score"""
        if mismatch > 0.7:
            return 'critical'
        elif mismatch > 0.5:
            return 'high'
        elif mismatch > 0.3:
            return 'medium'
        else:
            return 'low'
    
    def synthesize_interpretation(
        self,
        attention_trace: List[AttentionState],
        current_features: Any,
        mismatch_events: List[MismatchEvent]
    ) -> Dict[str, Any]:
        """
        Synthesize final interpretation from attention trace
        
        Emphasizes later cycles (convergence) and integrates mismatch events
        """
        if not attention_trace:
            return {
                'status': 'error',
                'message': 'No attention trace available'
            }
        
        # Compute weighted interpretation (later cycles weighted more)
        total_weight = 0.0
        weighted_attention = None
        
        for i, state in enumerate(attention_trace):
            if state.attention is None:
                continue
                
            # Weight: linear increase (later cycles more important)
            weight = (i + 1) / len(attention_trace)
            total_weight += weight
            
            if weighted_attention is None:
                weighted_attention = weight * state.attention
            else:
                weighted_attention += weight * state.attention
        
        if total_weight > 0 and weighted_attention is not None:
            weighted_attention /= total_weight
        
        # Compute confidence based on mismatch variance
        mismatch_scores = [s.mismatch for s in attention_trace if s.mismatch is not None]
        if mismatch_scores:
            mismatch_variance = np.var(mismatch_scores)
            # Lower variance = more confident (more stable)
            confidence = max(0.5, 1.0 - mismatch_variance)
        else:
            confidence = 0.7
        
        # Generate explanation
        explanation = self._generate_explanation(
            current_features,
            mismatch_events,
            attention_trace
        )
        
        return {
            'status': 'success',
            'confidence': float(confidence),
            'explanation': explanation,
            'num_mismatches': len(mismatch_events),
            'avg_mismatch': float(np.mean(mismatch_scores)) if mismatch_scores else 0.0,
            'final_attention': weighted_attention.tolist() if weighted_attention is not None else None,
            'components': self._extract_components(current_features, weighted_attention)
        }
    
    def _generate_explanation(
        self,
        current_features: Any,
        mismatch_events: List[MismatchEvent],
        attention_trace: List[AttentionState]
    ) -> str:
        """Generate human-readable explanation of flickering analysis"""
        num_events = len(mismatch_events)
        
        if num_events == 0:
            return (
                f"Analysis completed with {len(attention_trace)} oscillation cycles. "
                f"Diagram matched expected patterns from memory with minimal novelty detected. "
                f"Interpretation is highly confident based on historical knowledge."
            )
        elif num_events < 5:
            return (
                f"Analysis detected {num_events} novelty event(s) during {len(attention_trace)} cycles. "
                f"Some diagram elements differed from expected patterns, indicating minor novel features. "
                f"System adapted interpretation by integrating new observations with historical knowledge."
            )
        else:
            critical_events = sum(1 for e in mismatch_events if e.novelty_level in ['high', 'critical'])
            return (
                f"Analysis detected significant novelty: {num_events} mismatch events "
                f"({critical_events} high/critical) during {len(attention_trace)} cycles. "
                f"Diagram contains substantial novel elements requiring learning. "
                f"Interpretation combines current observations with adapted historical patterns."
            )
    
    def _extract_components(
        self,
        current_features: Any,
        weighted_attention: Optional[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """Extract component list from features (placeholder for now)"""
        if hasattr(current_features, 'visual_elements'):
            return current_features.visual_elements
        else:
            return []
    
    def _detect_convergence(self, attention_trace: List[AttentionState]) -> Optional[int]:
        """
        Detect cycle at which interpretation converged
        
        Convergence = when mismatch stabilizes (variance becomes low)
        """
        if len(attention_trace) < 10:
            return None
        
        window_size = 10
        variance_threshold = 0.01
        
        for i in range(window_size, len(attention_trace)):
            window = attention_trace[i-window_size:i]
            mismatches = [s.mismatch for s in window if s.mismatch is not None]
            
            if len(mismatches) >= window_size // 2:
                variance = np.var(mismatches)
                if variance < variance_threshold:
                    return i - window_size  # Return start of convergence window
        
        return None
    
    def signal_learning_event(self, mismatch_score: float, features: Any):
        """
        Signal to Map Integration Agent that learning is needed
        
        This method publishes an event that Map Integration Agent can subscribe to
        """
        # TODO: Implement event publishing (e.g., message queue, callback)
        print(f"📢 Learning Event: Mismatch={mismatch_score:.3f} - Triggering Map Integration")
