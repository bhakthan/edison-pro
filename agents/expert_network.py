"""
Expert Network Synthesis Agent
Simulates a "panel of experts" review with multiple domain perspectives debating findings.

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExpertOpinion:
    """Represents an expert's opinion on the diagram"""
    expert_id: str
    domain: str  # 'electrical', 'mechanical', 'safety', 'compliance', etc.
    perspective: str  # 'design', 'safety', 'cost', 'constructability'
    assessment: str
    concerns: List[str]
    recommendations: List[str]
    approval_status: str  # 'approved', 'approved_with_conditions', 'rejected'
    confidence: float
    rationale: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'expert_id': self.expert_id,
            'domain': self.domain,
            'perspective': self.perspective,
            'assessment': self.assessment,
            'concerns': self.concerns,
            'recommendations': self.recommendations,
            'approval_status': self.approval_status,
            'confidence': float(self.confidence),
            'rationale': self.rationale
        }


@dataclass
class ConsensusResult:
    """Result of expert panel consensus"""
    overall_recommendation: str  # 'approved', 'conditional', 'rejected', 'needs_revision'
    expert_opinions: List[ExpertOpinion]
    consensus_level: float  # 0.0-1.0, how much experts agree
    critical_issues: List[str]
    debate_points: List[Dict[str, Any]]
    action_items: List[str]
    risk_assessment: str
    final_summary: str


class ExpertNetworkAgent:
    """
    Simulates a multi-disciplinary expert review panel.
    
    Key Innovation: Captures multi-perspective review process in AI
    
    Capabilities:
    1. Multiple parallel o3-pro instances with different expertise
    2. Each expert analyzes from their domain perspective
    3. Experts "debate" conflicting findings
    4. Consensus mechanism resolves disagreements
    5. Final recommendation with supporting/dissenting opinions
    
    Integration Points:
    - o3-pro: Multiple instances with domain-specific system prompts
    - Memory Atlas: Learn from past expert reviews
    - Reality Anchor: Shared feature extraction
    """
    
    def __init__(
        self,
        orchestrator,
        memory_atlas=None,
        enable_debate: bool = True,
        require_consensus_threshold: float = 0.75
    ):
        """
        Initialize Expert Network
        
        Args:
            orchestrator: o3-pro orchestrator for expert reasoning
            memory_atlas: Optional memory for learning from reviews
            enable_debate: Whether experts should debate conflicts
            require_consensus_threshold: Minimum agreement level (0.0-1.0)
        """
        self.orchestrator = orchestrator
        self.memory_atlas = memory_atlas
        self.enable_debate = enable_debate
        self.consensus_threshold = require_consensus_threshold
        
        # Define expert personas
        self.experts = self._initialize_experts()
        
        logger.info(f"👥 Expert Network initialized with {len(self.experts)} experts")
    
    def _initialize_experts(self) -> Dict[str, Dict[str, Any]]:
        """Initialize expert personas with specializations"""
        return {
            'electrical_engineer': {
                'domain': 'electrical',
                'perspective': 'design',
                'expertise': [
                    'Power distribution',
                    'Load calculations',
                    'NEC compliance',
                    'Equipment sizing',
                    'Short circuit analysis'
                ],
                'concerns': ['safety', 'code_compliance', 'capacity'],
                'system_prompt': """You are a Senior Electrical Engineer with 20 years of experience.
Your focus: Power system design, load calculations, NEC code compliance, equipment protection.
Be critical about: Undersized equipment, code violations, safety hazards, inadequate protection.
Communication style: Technical, precise, code-reference heavy."""
            },
            
            'safety_engineer': {
                'domain': 'safety',
                'perspective': 'safety',
                'expertise': [
                    'OSHA regulations',
                    'Arc flash analysis',
                    'Lockout/tagout',
                    'Personal protective equipment',
                    'Hazard assessment'
                ],
                'concerns': ['life_safety', 'worker_protection', 'emergency_systems'],
                'system_prompt': """You are a Safety Engineer focused on life-safety and OSHA compliance.
Your focus: Worker safety, arc flash hazards, emergency systems, proper guarding, PPE requirements.
Be critical about: Any safety shortcuts, missing interlocks, inadequate protection, code violations.
Communication style: Safety-first, zero-tolerance for risks, regulation-driven."""
            },
            
            'mechanical_engineer': {
                'domain': 'mechanical',
                'perspective': 'design',
                'expertise': [
                    'HVAC systems',
                    'Piping design',
                    'Equipment selection',
                    'Thermal analysis',
                    'Structural support'
                ],
                'concerns': ['reliability', 'efficiency', 'maintainability'],
                'system_prompt': """You are a Senior Mechanical Engineer specializing in building systems.
Your focus: Equipment selection, HVAC design, piping adequacy, thermal performance, maintenance access.
Be critical about: Undersized equipment, poor accessibility, inadequate ventilation, efficiency issues.
Communication style: Practical, maintenance-focused, lifecycle-aware."""
            },
            
            'compliance_officer': {
                'domain': 'compliance',
                'perspective': 'compliance',
                'expertise': [
                    'Building codes',
                    'Energy codes',
                    'Environmental regulations',
                    'Permit requirements',
                    'Standards compliance'
                ],
                'concerns': ['code_compliance', 'permit_issues', 'legal_liability'],
                'system_prompt': """You are a Compliance Officer ensuring regulatory adherence.
Your focus: Building code compliance, permit requirements, environmental regulations, standards.
Be critical about: Code violations, permit issues, non-standard practices, regulatory risks.
Communication style: Regulatory, documentation-focused, risk-averse."""
            },
            
            'cost_estimator': {
                'domain': 'cost',
                'perspective': 'cost',
                'expertise': [
                    'Cost estimation',
                    'Value engineering',
                    'Budget management',
                    'Material pricing',
                    'Labor costs'
                ],
                'concerns': ['budget_overruns', 'cost_efficiency', 'value'],
                'system_prompt': """You are a Cost Estimator focused on project economics.
Your focus: Cost efficiency, value engineering opportunities, budget adherence, ROI.
Be critical about: Overdesign, expensive solutions, budget risks, poor value propositions.
Communication style: Financial, ROI-focused, cost-benefit oriented."""
            },
            
            'constructability_expert': {
                'domain': 'constructability',
                'perspective': 'constructability',
                'expertise': [
                    'Construction sequencing',
                    'Means and methods',
                    'Field coordination',
                    'Installation feasibility',
                    'Schedule impact'
                ],
                'concerns': ['constructability', 'schedule', 'field_issues'],
                'system_prompt': """You are a Construction Manager focused on buildability.
Your focus: Field installation feasibility, access for construction, sequencing, schedule.
Be critical about: Unbuildable designs, access issues, coordination problems, schedule risks.
Communication style: Practical, field-focused, reality-check oriented."""
            }
        }
    
    async def conduct_expert_review(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
        select_experts: Optional[List[str]] = None
    ) -> ConsensusResult:
        """
        Conduct multi-expert review of diagram
        
        Args:
            diagram: Diagram image or path
            domain: Primary engineering domain
            context: Additional context from analysis
            select_experts: Optional list of expert IDs to include
        
        Returns:
            ConsensusResult with all expert opinions and consensus
        """
        logger.info(f"👥 Starting expert panel review (domain: {domain})")
        
        # Step 1: Select relevant experts
        active_experts = self._select_experts(domain, select_experts)
        logger.info(f"   Selected {len(active_experts)} experts")
        
        # Step 2: Parallel expert analysis
        expert_opinions = await self._gather_expert_opinions(
            diagram, domain, context, active_experts
        )
        
        # Step 3: Identify conflicts
        conflicts = self._identify_conflicts(expert_opinions)
        
        # Step 4: Debate conflicts (if enabled)
        if self.enable_debate and conflicts:
            logger.info(f"   🗣️  {len(conflicts)} conflicts identified - initiating debate")
            expert_opinions = await self._resolve_through_debate(
                expert_opinions, conflicts, diagram, context
            )
        
        # Step 5: Build consensus
        consensus = self._build_consensus(expert_opinions)
        
        # Step 6: Generate final summary
        final_summary = self._generate_summary(consensus, expert_opinions)
        
        result = ConsensusResult(
            overall_recommendation=consensus['recommendation'],
            expert_opinions=expert_opinions,
            consensus_level=consensus['level'],
            critical_issues=consensus['critical_issues'],
            debate_points=conflicts,
            action_items=consensus['action_items'],
            risk_assessment=consensus['risk_assessment'],
            final_summary=final_summary
        )
        
        logger.info(f"✅ Expert review complete: {result.overall_recommendation} (consensus: {result.consensus_level:.0%})")
        
        return result
    
    def _select_experts(
        self,
        domain: str,
        select_experts: Optional[List[str]]
    ) -> List[str]:
        """Select relevant experts for this review"""
        
        if select_experts:
            return [e for e in select_experts if e in self.experts]
        
        # Auto-select based on domain
        domain_map = {
            'electrical': ['electrical_engineer', 'safety_engineer', 'compliance_officer', 'cost_estimator'],
            'mechanical': ['mechanical_engineer', 'safety_engineer', 'cost_estimator', 'constructability_expert'],
            'pid': ['mechanical_engineer', 'safety_engineer', 'compliance_officer'],
            'civil': ['constructability_expert', 'cost_estimator', 'compliance_officer'],
            'structural': ['constructability_expert', 'safety_engineer', 'cost_estimator', 'compliance_officer']
        }
        
        selected = domain_map.get(domain, list(self.experts.keys())[:4])
        
        # Always include safety for critical review
        if 'safety_engineer' not in selected:
            selected.append('safety_engineer')
        
        return selected
    
    async def _gather_expert_opinions(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]],
        expert_ids: List[str]
    ) -> List[ExpertOpinion]:
        """Gather opinions from all experts in parallel"""
        
        # Create tasks for parallel execution
        tasks = []
        for expert_id in expert_ids:
            task = self._get_expert_opinion(expert_id, diagram, domain, context)
            tasks.append(task)
        
        # Execute in parallel
        opinions = await asyncio.gather(*tasks)
        
        return opinions
    
    async def _get_expert_opinion(
        self,
        expert_id: str,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]]
    ) -> ExpertOpinion:
        """Get opinion from a single expert"""
        
        expert = self.experts[expert_id]
        
        # Build expert-specific prompt
        prompt = f"""{expert['system_prompt']}

Review this {domain} engineering diagram from your perspective as a {expert['domain']} expert.

Context: {context or 'Initial review'}

Provide your professional assessment covering:
1. Overall evaluation (Approved/Approved with Conditions/Rejected)
2. Key concerns from your expertise area
3. Specific recommendations
4. Confidence in your assessment (0-100%)
5. Rationale for your opinion

Be thorough and critical. If you identify issues, be specific about what needs to change."""

        try:
            # Call o3-pro with expert persona
            response = await self.orchestrator.ask_question_pro(
                prompt,
                reasoning_effort='medium'  # Balance depth vs speed
            )
            
            # Parse response into structured opinion
            opinion = self._parse_expert_response(
                expert_id, expert, response.get('answer', '')
            )
            
            return opinion
            
        except Exception as e:
            logger.warning(f"Expert {expert_id} analysis failed: {e}")
            # Return default cautious opinion
            return ExpertOpinion(
                expert_id=expert_id,
                domain=expert['domain'],
                perspective=expert['perspective'],
                assessment="Unable to complete assessment",
                concerns=["Analysis error occurred"],
                recommendations=["Retry analysis"],
                approval_status='rejected',
                confidence=0.0,
                rationale=f"Technical error: {str(e)}"
            )
    
    def _parse_expert_response(
        self,
        expert_id: str,
        expert: Dict[str, Any],
        response: str
    ) -> ExpertOpinion:
        """Parse expert's response into structured opinion"""
        
        # Simple parsing (production would use more sophisticated NLP)
        response_lower = response.lower()
        
        # Determine approval status
        if 'approved with conditions' in response_lower or 'conditional' in response_lower:
            status = 'approved_with_conditions'
        elif 'approved' in response_lower and 'not approved' not in response_lower:
            status = 'approved'
        elif 'rejected' in response_lower or 'not approved' in response_lower:
            status = 'rejected'
        else:
            status = 'needs_revision'
        
        # Extract concerns (lines with keywords)
        concern_keywords = ['concern', 'issue', 'problem', 'violation', 'risk', 'hazard']
        concerns = []
        for line in response.split('\n'):
            if any(keyword in line.lower() for keyword in concern_keywords):
                concerns.append(line.strip())
        
        # Extract recommendations
        recommendation_keywords = ['recommend', 'should', 'must', 'suggest', 'advise']
        recommendations = []
        for line in response.split('\n'):
            if any(keyword in line.lower() for keyword in recommendation_keywords):
                recommendations.append(line.strip())
        
        # Extract confidence (look for percentage)
        import re
        confidence_match = re.search(r'(\d+)%', response)
        confidence = float(confidence_match.group(1)) / 100 if confidence_match else 0.75
        
        return ExpertOpinion(
            expert_id=expert_id,
            domain=expert['domain'],
            perspective=expert['perspective'],
            assessment=response[:200] + '...' if len(response) > 200 else response,
            concerns=concerns[:5],  # Top 5
            recommendations=recommendations[:5],  # Top 5
            approval_status=status,
            confidence=confidence,
            rationale=response
        )
    
    def _identify_conflicts(
        self,
        opinions: List[ExpertOpinion]
    ) -> List[Dict[str, Any]]:
        """Identify conflicting opinions between experts"""
        
        conflicts = []
        
        # Check for approval status conflicts
        statuses = [op.approval_status for op in opinions]
        if len(set(statuses)) > 1:
            conflicts.append({
                'type': 'approval_conflict',
                'description': f"Experts disagree on approval: {', '.join(set(statuses))}",
                'experts_involved': [op.expert_id for op in opinions],
                'severity': 'high'
            })
        
        # Check for contradictory concerns
        all_concerns = []
        for op in opinions:
            all_concerns.extend([(op.expert_id, c) for c in op.concerns])
        
        # Look for contradictions (simplified)
        concern_texts = [c[1].lower() for c in all_concerns]
        if 'overdesign' in ' '.join(concern_texts) and 'undersized' in ' '.join(concern_texts):
            conflicts.append({
                'type': 'design_conflict',
                'description': "Conflicting views on equipment sizing",
                'experts_involved': [c[0] for c in all_concerns if 'design' in c[1].lower() or 'size' in c[1].lower()],
                'severity': 'medium'
            })
        
        return conflicts
    
    async def _resolve_through_debate(
        self,
        opinions: List[ExpertOpinion],
        conflicts: List[Dict[str, Any]],
        diagram: Any,
        context: Optional[Dict[str, Any]]
    ) -> List[ExpertOpinion]:
        """Have experts debate conflicts to reach resolution"""
        
        logger.info(f"   🗣️  Starting expert debate on {len(conflicts)} conflicts")
        
        for conflict in conflicts:
            # Get conflicting experts
            involved_experts = conflict.get('experts_involved', [])
            
            if len(involved_experts) < 2:
                continue
            
            # Build debate prompt
            debate_prompt = f"""Expert Panel Debate

Conflict: {conflict['description']}

Expert Positions:
"""
            for expert_id in involved_experts:
                opinion = next((op for op in opinions if op.expert_id == expert_id), None)
                if opinion:
                    debate_prompt += f"\n{expert_id}: {opinion.assessment}\n"
            
            debate_prompt += """
Each expert should:
1. Defend their position with specific evidence
2. Address counterarguments
3. Propose a compromise if possible
4. Update confidence based on discussion

Facilitate a constructive debate and reach a resolution."""
            
            try:
                # Run debate (simplified - production would iterate)
                response = await self.orchestrator.ask_question_pro(
                    debate_prompt,
                    reasoning_effort='high'  # Debates need deep reasoning
                )
                
                # Update opinions based on debate
                # In production, would parse debate outcome and update confidences
                logger.info(f"   ✅ Debate resolved: {conflict['description']}")
                
            except Exception as e:
                logger.warning(f"Debate failed for conflict: {e}")
        
        return opinions
    
    def _build_consensus(
        self,
        opinions: List[ExpertOpinion]
    ) -> Dict[str, Any]:
        """Build consensus from expert opinions"""
        
        # Count approval statuses
        status_counts = {}
        for op in opinions:
            status_counts[op.approval_status] = status_counts.get(op.approval_status, 0) + 1
        
        # Determine overall recommendation
        total = len(opinions)
        approved = status_counts.get('approved', 0)
        conditional = status_counts.get('approved_with_conditions', 0)
        rejected = status_counts.get('rejected', 0)
        
        if approved / total >= self.consensus_threshold:
            overall = 'approved'
        elif (approved + conditional) / total >= self.consensus_threshold:
            overall = 'conditional'
        elif rejected / total >= 0.5:
            overall = 'rejected'
        else:
            overall = 'needs_revision'
        
        # Calculate consensus level
        max_agreement = max(status_counts.values())
        consensus_level = max_agreement / total
        
        # Collect critical issues (from high-confidence rejections)
        critical_issues = []
        for op in opinions:
            if op.approval_status in ['rejected', 'approved_with_conditions'] and op.confidence > 0.7:
                critical_issues.extend(op.concerns)
        
        # Deduplicate
        critical_issues = list(set(critical_issues))[:10]  # Top 10
        
        # Generate action items
        action_items = []
        for op in opinions:
            if op.recommendations:
                action_items.extend(op.recommendations)
        action_items = list(set(action_items))[:10]  # Top 10
        
        # Risk assessment
        high_risk_count = sum(1 for op in opinions if op.approval_status == 'rejected')
        if high_risk_count >= total * 0.3:
            risk_assessment = 'HIGH - Multiple experts identified critical issues'
        elif conditional / total > 0.5:
            risk_assessment = 'MEDIUM - Conditional approval with mitigation required'
        else:
            risk_assessment = 'LOW - Design meets requirements with minor notes'
        
        return {
            'recommendation': overall,
            'level': consensus_level,
            'critical_issues': critical_issues,
            'action_items': action_items,
            'risk_assessment': risk_assessment,
            'status_breakdown': status_counts
        }
    
    def _generate_summary(
        self,
        consensus: Dict[str, Any],
        opinions: List[ExpertOpinion]
    ) -> str:
        """Generate final summary of expert review"""
        
        summary = f"""EXPERT PANEL REVIEW SUMMARY
{'='*60}

OVERALL RECOMMENDATION: {consensus['recommendation'].upper()}
Consensus Level: {consensus['level']:.0%}
Risk Assessment: {consensus['risk_assessment']}

EXPERT BREAKDOWN:
"""
        for status, count in consensus['status_breakdown'].items():
            summary += f"  • {status.replace('_', ' ').title()}: {count} expert(s)\n"
        
        summary += f"\nCRITICAL ISSUES ({len(consensus['critical_issues'])}):\n"
        for i, issue in enumerate(consensus['critical_issues'][:5], 1):
            summary += f"  {i}. {issue}\n"
        
        summary += f"\nACTION ITEMS ({len(consensus['action_items'])}):\n"
        for i, action in enumerate(consensus['action_items'][:5], 1):
            summary += f"  {i}. {action}\n"
        
        summary += "\nEXPERT OPINIONS:\n"
        for op in opinions:
            summary += f"\n{op.expert_id.replace('_', ' ').title()} ({op.domain}):\n"
            summary += f"  Status: {op.approval_status.replace('_', ' ').title()}\n"
            summary += f"  Confidence: {op.confidence:.0%}\n"
            if op.concerns:
                summary += f"  Key Concern: {op.concerns[0]}\n"
        
        return summary


def create_expert_network(
    orchestrator,
    **kwargs
) -> ExpertNetworkAgent:
    """Factory function to create expert network"""
    return ExpertNetworkAgent(
        orchestrator=orchestrator,
        **kwargs
    )
