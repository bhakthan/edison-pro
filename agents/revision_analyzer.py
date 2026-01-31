"""
Differential Analysis / Revision Analyzer
Automatically detects and explains changes between diagram revisions.

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
from PIL import Image
import cv2

logger = logging.getLogger(__name__)


@dataclass
class RevisionChange:
    """Represents a detected change between revisions"""
    change_id: str
    change_type: str  # 'addition', 'deletion', 'modification', 'relocation'
    location: Tuple[int, int, int, int]  # (x, y, width, height)
    component_type: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    significance: str = 'medium'  # 'low', 'medium', 'high', 'critical'
    engineering_impact: Optional[str] = None
    requires_reapproval: bool = False
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'change_id': self.change_id,
            'change_type': self.change_type,
            'location': self.location,
            'component_type': self.component_type,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'significance': self.significance,
            'engineering_impact': self.engineering_impact,
            'requires_reapproval': self.requires_reapproval,
            'confidence': float(self.confidence)
        }


@dataclass
class RevisionAnalysisResult:
    """Result of revision comparison"""
    revision_a: str
    revision_b: str
    total_changes: int
    changes: List[RevisionChange]
    summary: str
    critical_changes: List[str]
    requires_review: bool
    change_categories: Dict[str, int]
    visual_diff_path: Optional[str] = None


class RevisionAnalyzerAgent:
    """
    Analyzes differences between diagram revisions.
    
    Key Innovation: Automates tedious manual revision tracking with AI interpretation
    
    Capabilities:
    1. Visual diff detection (computer vision)
    2. Component change detection (added/removed/modified)
    3. Engineering significance assessment (o3-pro reasoning)
    4. Automatic change documentation
    5. Compliance impact analysis
    
    Integration Points:
    - Reality Anchor: Feature extraction from both revisions
    - o3-pro: Interpret significance of changes
    - Code Agent: Generate comparison reports/tables
    - Memory Atlas: Learn common revision patterns
    """
    
    def __init__(
        self,
        reality_anchor,
        orchestrator,
        memory_atlas=None,
        sensitivity: float = 0.05
    ):
        """
        Initialize Revision Analyzer
        
        Args:
            reality_anchor: RealityAnchorAgent for feature extraction
            orchestrator: o3-pro orchestrator for change interpretation
            memory_atlas: Optional memory atlas for pattern learning
            sensitivity: Change detection sensitivity (0.0-1.0)
        """
        self.reality_anchor = reality_anchor
        self.orchestrator = orchestrator
        self.memory_atlas = memory_atlas
        self.sensitivity = sensitivity
        
        # Change categorization rules
        self.critical_keywords = [
            'safety', 'interlock', 'ground', 'protection', 'relief', 'emergency',
            'shutdown', 'alarm', 'critical', 'hazard'
        ]
        
        self.high_impact_keywords = [
            'rating', 'capacity', 'voltage', 'pressure', 'temperature', 'load',
            'size', 'gauge', 'ampacity', 'flow'
        ]
        
        logger.info(f"📊 Revision Analyzer initialized (sensitivity: {sensitivity})")
    
    async def analyze_revisions(
        self,
        revision_a: Any,  # Path or image
        revision_b: Any,  # Path or image
        revision_a_label: str = "Rev A",
        revision_b_label: str = "Rev B",
        domain: Optional[str] = None
    ) -> RevisionAnalysisResult:
        """
        Compare two diagram revisions and identify changes
        
        Args:
            revision_a: First revision (earlier)
            revision_b: Second revision (later)
            revision_a_label: Label for first revision
            revision_b_label: Label for second revision
            domain: Engineering domain
        
        Returns:
            RevisionAnalysisResult with detected changes
        """
        logger.info(f"📊 Analyzing revisions: {revision_a_label} vs {revision_b_label}")
        
        # Step 1: Visual diff detection
        visual_changes = self._detect_visual_changes(revision_a, revision_b)
        
        # Step 2: Extract features from both revisions
        features_a = self.reality_anchor.extract_features(revision_a, domain=domain)
        features_b = self.reality_anchor.extract_features(revision_b, domain=domain)
        
        # Step 3: Component-level comparison
        component_changes = await self._compare_components(
            revision_a, revision_b, features_a, features_b, domain
        )
        
        # Step 4: Merge and categorize changes
        all_changes = self._merge_changes(visual_changes, component_changes)
        
        # Step 5: Assess engineering significance
        categorized_changes = await self._assess_significance(all_changes, domain)
        
        # Step 6: Generate summary
        summary = self._generate_summary(categorized_changes, revision_a_label, revision_b_label)
        
        # Step 7: Identify critical changes
        critical_changes = [
            f"{c.component_type}: {c.engineering_impact}"
            for c in categorized_changes
            if c.significance == 'critical'
        ]
        
        # Step 8: Categorize changes
        change_categories = self._categorize_changes(categorized_changes)
        
        # Step 9: Determine if review required
        requires_review = any(c.requires_reapproval for c in categorized_changes)
        
        result = RevisionAnalysisResult(
            revision_a=revision_a_label,
            revision_b=revision_b_label,
            total_changes=len(categorized_changes),
            changes=categorized_changes,
            summary=summary,
            critical_changes=critical_changes,
            requires_review=requires_review,
            change_categories=change_categories
        )
        
        logger.info(f"✅ Revision analysis complete: {len(categorized_changes)} changes detected")
        
        return result
    
    def _detect_visual_changes(
        self,
        image_a: Any,
        image_b: Any
    ) -> List[Dict[str, Any]]:
        """Detect visual differences using computer vision"""
        try:
            # Load images
            if isinstance(image_a, str):
                img_a = cv2.imread(image_a)
            else:
                img_a = np.array(image_a)
            
            if isinstance(image_b, str):
                img_b = cv2.imread(image_b)
            else:
                img_b = np.array(image_b)
            
            # Ensure same size
            if img_a.shape != img_b.shape:
                img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))
            
            # Convert to grayscale
            gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
            gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
            
            # Compute difference
            diff = cv2.absdiff(gray_a, gray_b)
            
            # Threshold to get changed regions
            _, thresh = cv2.threshold(diff, int(self.sensitivity * 255), 255, cv2.THRESH_BINARY)
            
            # Find contours of changes
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Extract change regions
            changes = []
            for i, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter small changes (noise)
                if w * h > 100:  # Minimum area
                    changes.append({
                        'id': f'visual_{i}',
                        'location': (x, y, w, h),
                        'area': w * h,
                        'type': 'visual_diff'
                    })
            
            logger.info(f"🔍 Detected {len(changes)} visual changes")
            return changes
        
        except Exception as e:
            logger.warning(f"Visual diff failed: {e}")
            return []
    
    async def _compare_components(
        self,
        revision_a: Any,
        revision_b: Any,
        features_a: np.ndarray,
        features_b: np.ndarray,
        domain: Optional[str]
    ) -> List[RevisionChange]:
        """Compare components using o3-pro reasoning"""
        
        # Use o3-pro to extract and compare components
        prompt = f"""Compare these two {domain or 'engineering'} diagram revisions and identify all changes.

For each change, specify:
1. Component type (e.g., "Circuit Breaker CB-301")
2. Change type (addition, deletion, modification, relocation)
3. Old value vs new value
4. Engineering significance (low, medium, high, critical)
5. Impact on design/safety/compliance

Focus on technically significant changes, not minor graphical differences."""

        try:
            # This would call o3-pro with both images
            response = await self.orchestrator.ask_question_pro(prompt)
            
            # Parse response to extract changes
            changes = self._parse_change_response(response)
            
            return changes
        
        except Exception as e:
            logger.warning(f"Component comparison failed: {e}")
            return []
    
    def _parse_change_response(self, response: Dict[str, Any]) -> List[RevisionChange]:
        """Parse o3-pro response into structured changes"""
        # This is a simplified parser - production would be more sophisticated
        
        changes = []
        answer = response.get('answer', '')
        
        # Example parsing (would use more robust NLP)
        lines = answer.split('\n')
        current_change = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_change:
                    changes.append(self._create_change_from_dict(current_change))
                    current_change = {}
                continue
            
            # Parse key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                current_change[key.strip().lower()] = value.strip()
        
        if current_change:
            changes.append(self._create_change_from_dict(current_change))
        
        return changes
    
    def _create_change_from_dict(self, data: Dict[str, str]) -> RevisionChange:
        """Create RevisionChange from parsed data"""
        
        change_type = data.get('change type', 'modification')
        component_type = data.get('component type', 'Unknown')
        old_value = data.get('old value')
        new_value = data.get('new value')
        significance = data.get('significance', 'medium')
        impact = data.get('impact')
        
        # Determine if reapproval needed
        requires_reapproval = (
            significance in ['high', 'critical'] or
            any(keyword in str(data).lower() for keyword in self.critical_keywords)
        )
        
        return RevisionChange(
            change_id=f"change_{len(self.critical_keywords)}",
            change_type=change_type,
            location=(0, 0, 0, 0),  # Would be populated from visual analysis
            component_type=component_type,
            old_value=old_value,
            new_value=new_value,
            significance=significance,
            engineering_impact=impact,
            requires_reapproval=requires_reapproval,
            confidence=0.85
        )
    
    def _merge_changes(
        self,
        visual_changes: List[Dict[str, Any]],
        component_changes: List[RevisionChange]
    ) -> List[RevisionChange]:
        """Merge visual and component-level changes"""
        
        # Start with component changes (higher level)
        merged = component_changes.copy()
        
        # Add visual changes that don't have component matches
        for visual in visual_changes:
            # Check if this visual change corresponds to a component change
            # (in production, would use spatial matching)
            merged.append(RevisionChange(
                change_id=visual['id'],
                change_type='visual_modification',
                location=visual['location'],
                significance='low',
                confidence=0.6
            ))
        
        return merged
    
    async def _assess_significance(
        self,
        changes: List[RevisionChange],
        domain: Optional[str]
    ) -> List[RevisionChange]:
        """Assess engineering significance of each change"""
        
        for change in changes:
            # Check against critical keywords
            change_text = f"{change.component_type} {change.old_value} {change.new_value}".lower()
            
            if any(keyword in change_text for keyword in self.critical_keywords):
                change.significance = 'critical'
                change.requires_reapproval = True
            elif any(keyword in change_text for keyword in self.high_impact_keywords):
                change.significance = 'high'
                change.requires_reapproval = True
            
            # Generate impact statement
            if change.component_type and change.new_value:
                change.engineering_impact = f"Modified {change.component_type} from {change.old_value} to {change.new_value}"
        
        return changes
    
    def _generate_summary(
        self,
        changes: List[RevisionChange],
        rev_a: str,
        rev_b: str
    ) -> str:
        """Generate human-readable summary"""
        
        if not changes:
            return f"No significant changes detected between {rev_a} and {rev_b}"
        
        # Count by type
        additions = sum(1 for c in changes if c.change_type == 'addition')
        deletions = sum(1 for c in changes if c.change_type == 'deletion')
        modifications = sum(1 for c in changes if c.change_type == 'modification')
        
        # Count by significance
        critical = sum(1 for c in changes if c.significance == 'critical')
        high = sum(1 for c in changes if c.significance == 'high')
        
        summary = f"Revision Comparison: {rev_a} → {rev_b}\n\n"
        summary += f"Total Changes: {len(changes)}\n"
        summary += f"  • Additions: {additions}\n"
        summary += f"  • Deletions: {deletions}\n"
        summary += f"  • Modifications: {modifications}\n\n"
        
        if critical > 0:
            summary += f"🚨 CRITICAL: {critical} safety/compliance changes require immediate review\n"
        if high > 0:
            summary += f"⚠️  HIGH IMPACT: {high} significant technical changes detected\n"
        
        # List top changes
        top_changes = sorted(changes, key=lambda c: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[c.significance], reverse=True)[:5]
        
        if top_changes:
            summary += f"\nKey Changes:\n"
            for i, change in enumerate(top_changes, 1):
                summary += f"{i}. [{change.significance.upper()}] {change.engineering_impact or change.change_type}\n"
        
        return summary
    
    def _categorize_changes(self, changes: List[RevisionChange]) -> Dict[str, int]:
        """Categorize changes for reporting"""
        categories = {
            'additions': 0,
            'deletions': 0,
            'modifications': 0,
            'relocations': 0,
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }
        
        for change in changes:
            categories[change.change_type] = categories.get(change.change_type, 0) + 1
            categories[change.significance] = categories.get(change.significance, 0) + 1
        
        return categories


def create_revision_analyzer(
    reality_anchor,
    orchestrator,
    **kwargs
) -> RevisionAnalyzerAgent:
    """Factory function to create revision analyzer"""
    return RevisionAnalyzerAgent(
        reality_anchor=reality_anchor,
        orchestrator=orchestrator,
        **kwargs
    )
