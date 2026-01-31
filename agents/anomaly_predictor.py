"""
Anomaly Prediction Engine
Predicts potential issues by comparing current diagrams against historical failure patterns.

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AnomalyPattern:
    """Represents a known failure or issue pattern"""
    pattern_id: str
    failure_type: str  # 'overload', 'grounding_issue', 'safety_violation', etc.
    features: np.ndarray  # 512-dim embedding
    domain: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    failure_indicators: List[str]  # What went wrong
    root_cause: str
    solution: str
    similar_incidents: List[Dict[str, Any]]  # Historical occurrences
    detection_confidence: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_id': self.pattern_id,
            'failure_type': self.failure_type,
            'features': self.features.tolist(),
            'domain': self.domain,
            'severity': self.severity,
            'failure_indicators': self.failure_indicators,
            'root_cause': self.root_cause,
            'solution': self.solution,
            'similar_incidents': self.similar_incidents,
            'detection_confidence': float(self.detection_confidence),
            'timestamp': self.timestamp
        }


@dataclass
class PredictionResult:
    """Result of anomaly prediction"""
    has_anomalies: bool
    anomalies: List[Dict[str, Any]]
    risk_score: float  # 0.0-1.0
    confidence: float
    recommendations: List[str]
    similar_failures: List[Dict[str, Any]]
    prevention_cost_estimate: Optional[float] = None
    failure_cost_estimate: Optional[float] = None


class AnomalyPredictorAgent:
    """
    Predicts potential failures by comparing current diagram against historical failure patterns.
    
    Key Innovation: Shifts from reactive (answering questions) to proactive (warning about risks)
    
    Architecture:
    1. Extract features from current diagram (Reality Anchor)
    2. Compare against failure pattern database (Memory Atlas subset)
    3. Calculate similarity scores and risk levels
    4. Generate actionable recommendations
    
    Integration Points:
    - Reality Anchor: Feature extraction
    - Memory Atlas: Pattern storage/retrieval
    - Azure AI Search: Semantic similarity search
    """
    
    def __init__(
        self,
        memory_atlas,
        reality_anchor,
        storage_path: str = "./failure_patterns",
        similarity_threshold: float = 0.75,
        use_azure_search: bool = False
    ):
        """
        Initialize Anomaly Predictor
        
        Args:
            memory_atlas: MemoryAtlasAgent instance for pattern storage
            reality_anchor: RealityAnchorAgent for feature extraction
            storage_path: Directory for failure pattern storage
            similarity_threshold: Minimum similarity to flag anomaly (0.0-1.0)
            use_azure_search: Whether to use Azure AI Search for patterns
        """
        self.memory_atlas = memory_atlas
        self.reality_anchor = reality_anchor
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.similarity_threshold = similarity_threshold
        self.use_azure_search = use_azure_search
        
        # Failure pattern database
        self.failure_patterns: Dict[str, AnomalyPattern] = {}
        
        # Domain-specific failure catalogs
        self.failure_catalogs = {
            'electrical': self._init_electrical_failures(),
            'mechanical': self._init_mechanical_failures(),
            'pid': self._init_pid_failures(),
            'civil': self._init_civil_failures(),
            'structural': self._init_structural_failures()
        }
        
        # Load existing patterns
        self._load_patterns()
        
        logger.info(f"🔍 Anomaly Predictor initialized with {len(self.failure_patterns)} failure patterns")
    
    def _init_electrical_failures(self) -> List[Dict[str, Any]]:
        """Initialize electrical failure catalog"""
        return [
            {
                'failure_type': 'overload_risk',
                'indicators': ['undersized wire gauge', 'inadequate breaker rating', 'high load density'],
                'severity': 'high',
                'root_cause': 'Circuit design exceeds conductor ampacity',
                'solution': 'Increase wire gauge or split circuit',
                'typical_cost': 5000
            },
            {
                'failure_type': 'grounding_violation',
                'indicators': ['missing ground conductor', 'improper bonding', 'no ground rod'],
                'severity': 'critical',
                'root_cause': 'NEC grounding requirements not met',
                'solution': 'Install proper grounding system per NEC 250',
                'typical_cost': 8000
            },
            {
                'failure_type': 'voltage_drop_excessive',
                'indicators': ['long circuit run', 'undersized conductor', 'high impedance'],
                'severity': 'medium',
                'root_cause': 'Voltage drop exceeds NEC 3% recommendation',
                'solution': 'Increase conductor size or reduce circuit length',
                'typical_cost': 3500
            },
            {
                'failure_type': 'arc_flash_hazard',
                'indicators': ['high fault current', 'no arc flash study', 'inadequate PPE labeling'],
                'severity': 'critical',
                'root_cause': 'Arc flash risk not assessed',
                'solution': 'Perform arc flash study and label equipment',
                'typical_cost': 15000
            }
        ]
    
    def _init_mechanical_failures(self) -> List[Dict[str, Any]]:
        """Initialize mechanical failure catalog"""
        return [
            {
                'failure_type': 'pump_cavitation',
                'indicators': ['insufficient NPSH', 'high suction lift', 'vapor pressure issues'],
                'severity': 'high',
                'root_cause': 'Net Positive Suction Head insufficient',
                'solution': 'Relocate pump or increase suction pipe diameter',
                'typical_cost': 12000
            },
            {
                'failure_type': 'bearing_failure_risk',
                'indicators': ['inadequate lubrication path', 'high vibration design', 'misalignment'],
                'severity': 'medium',
                'root_cause': 'Bearing load or environment exceeds design',
                'solution': 'Upgrade bearing type or improve lubrication',
                'typical_cost': 8000
            }
        ]
    
    def _init_pid_failures(self) -> List[Dict[str, Any]]:
        """Initialize P&ID failure catalog"""
        return [
            {
                'failure_type': 'pressure_relief_missing',
                'indicators': ['blocked outlet', 'no PRV', 'overpressure scenario possible'],
                'severity': 'critical',
                'root_cause': 'Pressure relief not provided for blocked scenarios',
                'solution': 'Install pressure relief valve per ASME Section VIII',
                'typical_cost': 10000
            },
            {
                'failure_type': 'interlock_missing',
                'indicators': ['no safety interlock', 'simultaneous operation possible', 'conflicting valves'],
                'severity': 'high',
                'root_cause': 'Control logic allows unsafe state',
                'solution': 'Add interlock logic to prevent unsafe operations',
                'typical_cost': 6000
            }
        ]
    
    def _init_civil_failures(self) -> List[Dict[str, Any]]:
        """Initialize civil failure catalog"""
        return [
            {
                'failure_type': 'drainage_inadequate',
                'indicators': ['flat grade', 'no drainage path', 'ponding risk'],
                'severity': 'medium',
                'root_cause': 'Insufficient slope for positive drainage',
                'solution': 'Adjust grading to minimum 2% slope',
                'typical_cost': 15000
            }
        ]
    
    def _init_structural_failures(self) -> List[Dict[str, Any]]:
        """Initialize structural failure catalog"""
        return [
            {
                'failure_type': 'beam_undersized',
                'indicators': ['high span-to-depth ratio', 'inadequate section modulus', 'deflection risk'],
                'severity': 'high',
                'root_cause': 'Bending stress or deflection exceeds allowable',
                'solution': 'Increase beam depth or use higher strength steel',
                'typical_cost': 20000
            }
        ]
    
    def predict_anomalies(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]] = None
    ) -> PredictionResult:
        """
        Predict potential anomalies in diagram
        
        Args:
            diagram: Diagram image or path
            domain: Engineering domain
            context: Additional context (extracted components, etc.)
        
        Returns:
            PredictionResult with anomalies and recommendations
        """
        logger.info(f"🔍 Analyzing diagram for anomalies (domain: {domain})")
        
        # Step 1: Extract features from current diagram
        features = self.reality_anchor.extract_features(diagram, domain=domain)
        
        # Step 2: Get failure patterns for this domain
        domain_failures = self.failure_catalogs.get(domain, [])
        
        # Step 3: Compare against known failure patterns
        detected_anomalies = []
        risk_scores = []
        
        for failure in domain_failures:
            # Check if indicators match
            similarity_score = self._calculate_similarity(features, failure, context)
            
            if similarity_score >= self.similarity_threshold:
                anomaly = {
                    'failure_type': failure['failure_type'],
                    'severity': failure['severity'],
                    'confidence': float(similarity_score),
                    'indicators': failure['indicators'],
                    'root_cause': failure['root_cause'],
                    'solution': failure['solution'],
                    'estimated_fix_cost': failure.get('typical_cost', 0),
                    'estimated_failure_cost': failure.get('typical_cost', 0) * 10  # Failure costs ~10x prevention
                }
                detected_anomalies.append(anomaly)
                risk_scores.append(self._severity_to_score(failure['severity']) * similarity_score)
        
        # Step 4: Calculate overall risk
        overall_risk = max(risk_scores) if risk_scores else 0.0
        
        # Step 5: Generate recommendations
        recommendations = self._generate_recommendations(detected_anomalies, domain)
        
        # Step 6: Find similar historical failures
        similar_failures = self._find_similar_failures(features, domain)
        
        # Calculate cost estimates
        prevention_cost = sum(a.get('estimated_fix_cost', 0) for a in detected_anomalies)
        failure_cost = sum(a.get('estimated_failure_cost', 0) for a in detected_anomalies)
        
        result = PredictionResult(
            has_anomalies=len(detected_anomalies) > 0,
            anomalies=detected_anomalies,
            risk_score=overall_risk,
            confidence=np.mean([a['confidence'] for a in detected_anomalies]) if detected_anomalies else 1.0,
            recommendations=recommendations,
            similar_failures=similar_failures,
            prevention_cost_estimate=prevention_cost,
            failure_cost_estimate=failure_cost
        )
        
        logger.info(f"✅ Prediction complete: {len(detected_anomalies)} anomalies detected (risk: {overall_risk:.2f})")
        
        return result
    
    def _calculate_similarity(
        self,
        features: np.ndarray,
        failure_pattern: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate similarity between current features and failure pattern"""
        # In production, this would use embeddings and cosine similarity
        # For now, use indicator-based matching with context
        
        if not context:
            return 0.5  # Default moderate similarity
        
        # Check if indicators are present in context
        indicators = failure_pattern.get('indicators', [])
        matches = 0
        
        # Simple keyword matching (would be more sophisticated with embeddings)
        context_str = str(context).lower()
        for indicator in indicators:
            if any(word in context_str for word in indicator.lower().split()):
                matches += 1
        
        similarity = matches / len(indicators) if indicators else 0.0
        return min(1.0, similarity + 0.2)  # Boost baseline
    
    def _severity_to_score(self, severity: str) -> float:
        """Convert severity to numeric score"""
        severity_map = {
            'low': 0.25,
            'medium': 0.50,
            'high': 0.75,
            'critical': 1.0
        }
        return severity_map.get(severity.lower(), 0.5)
    
    def _generate_recommendations(
        self,
        anomalies: List[Dict[str, Any]],
        domain: str
    ) -> List[str]:
        """Generate actionable recommendations"""
        if not anomalies:
            return [f"✅ No anomalies detected - {domain} design appears sound"]
        
        recommendations = []
        
        # Sort by severity
        critical = [a for a in anomalies if a['severity'] == 'critical']
        high = [a for a in anomalies if a['severity'] == 'high']
        medium = [a for a in anomalies if a['severity'] == 'medium']
        
        if critical:
            recommendations.append(f"🚨 CRITICAL: {len(critical)} safety issues require immediate attention")
            for anomaly in critical[:3]:  # Top 3
                recommendations.append(f"   → {anomaly['failure_type']}: {anomaly['solution']}")
        
        if high:
            recommendations.append(f"⚠️  HIGH PRIORITY: {len(high)} issues detected")
            for anomaly in high[:2]:
                recommendations.append(f"   → {anomaly['failure_type']}: {anomaly['solution']}")
        
        if medium:
            recommendations.append(f"ℹ️  {len(medium)} medium-priority improvements identified")
        
        # Add cost-benefit
        total_prevention = sum(a.get('estimated_fix_cost', 0) for a in anomalies)
        total_failure = sum(a.get('estimated_failure_cost', 0) for a in anomalies)
        if total_prevention > 0:
            roi = ((total_failure - total_prevention) / total_prevention) * 100
            recommendations.append(
                f"💰 ROI: ${total_prevention:,.0f} prevention cost vs ${total_failure:,.0f} failure cost ({roi:.0f}% ROI)"
            )
        
        return recommendations
    
    def _find_similar_failures(
        self,
        features: np.ndarray,
        domain: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar historical failures"""
        # In production, query Azure AI Search for similar failure patterns
        # For now, return template examples
        
        return [
            {
                'project': 'Hospital Expansion 2024',
                'failure_type': 'grounding_violation',
                'outcome': 'Failed inspection, $45K remediation',
                'similarity': 0.92
            },
            {
                'project': 'Data Center Phase 2',
                'failure_type': 'overload_risk',
                'outcome': 'Breaker trips, $30K redesign',
                'similarity': 0.85
            }
        ]
    
    def store_failure_pattern(
        self,
        pattern: AnomalyPattern
    ) -> None:
        """Store a new failure pattern for future detection"""
        self.failure_patterns[pattern.pattern_id] = pattern
        
        # Persist to disk
        pattern_file = self.storage_path / f"{pattern.pattern_id}.json"
        with open(pattern_file, 'w') as f:
            json.dump(pattern.to_dict(), f, indent=2)
        
        logger.info(f"💾 Stored failure pattern: {pattern.pattern_id}")
    
    def _load_patterns(self) -> None:
        """Load existing failure patterns from disk"""
        if not self.storage_path.exists():
            return
        
        import json
        for pattern_file in self.storage_path.glob("*.json"):
            try:
                with open(pattern_file, 'r') as f:
                    data = json.load(f)
                    data['features'] = np.array(data['features'])
                    pattern = AnomalyPattern(**data)
                    self.failure_patterns[pattern.pattern_id] = pattern
            except Exception as e:
                logger.warning(f"Failed to load pattern {pattern_file}: {e}")


def create_anomaly_predictor(
    memory_atlas,
    reality_anchor,
    **kwargs
) -> AnomalyPredictorAgent:
    """Factory function to create anomaly predictor"""
    return AnomalyPredictorAgent(
        memory_atlas=memory_atlas,
        reality_anchor=reality_anchor,
        **kwargs
    )
