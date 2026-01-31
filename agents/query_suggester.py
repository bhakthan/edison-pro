"""
Intelligent Query Suggestion Engine
Proactively suggests critical verification questions based on diagram analysis.

Author: Srikanth Bhakthan - Microsoft
Date: October 28, 2025
"""

import numpy as np
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SuggestedQuestion:
    """Represents a suggested verification question"""
    question_id: str
    question: str
    priority: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'safety', 'compliance', 'design', 'verification'
    rationale: str
    context: Optional[Dict[str, Any]] = None
    estimated_importance: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'question_id': self.question_id,
            'question': self.question,
            'priority': self.priority,
            'category': self.category,
            'rationale': self.rationale,
            'context': self.context,
            'estimated_importance': float(self.estimated_importance)
        }


@dataclass
class QuestionSuggestionResult:
    """Result of question suggestion analysis"""
    suggested_questions: List[SuggestedQuestion]
    categories: Dict[str, int]
    critical_count: int
    reasoning: str


class QuerySuggestionAgent:
    """
    Proactively suggests questions engineers should ask but might not think of.
    
    Key Innovation: AI teaches engineers what to look for (mentorship role)
    
    Capabilities:
    1. Analyze diagram complexity and identify blind spots
    2. Suggest domain-specific verification questions
    3. Prioritize questions by criticality
    4. Learn from user interactions to improve suggestions
    5. Adapt to engineering domain and standards
    
    Integration Points:
    - Reality Anchor: Analyze diagram features
    - Memory Atlas: Learn common question patterns
    - o3-pro: Generate contextual questions
    - Confidence Evaluator: Identify low-confidence areas
    """
    
    def __init__(
        self,
        reality_anchor,
        memory_atlas,
        orchestrator,
        confidence_evaluator=None
    ):
        """
        Initialize Query Suggestion Agent
        
        Args:
            reality_anchor: RealityAnchorAgent for feature extraction
            memory_atlas: MemoryAtlasAgent for pattern learning
            orchestrator: o3-pro orchestrator for question generation
            confidence_evaluator: Optional confidence evaluator
        """
        self.reality_anchor = reality_anchor
        self.memory_atlas = memory_atlas
        self.orchestrator = orchestrator
        self.confidence_evaluator = confidence_evaluator
        
        # Domain-specific question libraries
        self.question_libraries = {
            'electrical': self._init_electrical_questions(),
            'mechanical': self._init_mechanical_questions(),
            'pid': self._init_pid_questions(),
            'civil': self._init_civil_questions(),
            'structural': self._init_structural_questions()
        }
        
        # User feedback tracking
        self.question_effectiveness: Dict[str, float] = {}
        
        logger.info("💡 Query Suggestion Agent initialized")
    
    def _init_electrical_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize electrical engineering question library"""
        return {
            'safety': [
                {
                    'template': 'Is the grounding system compliant with NEC Article 250?',
                    'triggers': ['transformer', 'panel', 'service entrance'],
                    'priority': 'critical',
                    'rationale': 'Grounding violations are life-safety issues'
                },
                {
                    'template': 'Has arc flash analysis been performed per NFPA 70E?',
                    'triggers': ['switchgear', 'MCC', 'high voltage'],
                    'priority': 'critical',
                    'rationale': 'Arc flash hazards require assessment and labeling'
                },
                {
                    'template': 'Are GFCI/AFCI protection requirements met?',
                    'triggers': ['receptacle', 'kitchen', 'bathroom', 'garage'],
                    'priority': 'high',
                    'rationale': 'NEC requires GFCI/AFCI in specific locations'
                }
            ],
            'design': [
                {
                    'template': 'What is the voltage drop on circuit {circuit_id}?',
                    'triggers': ['long run', 'feeder', 'branch circuit'],
                    'priority': 'high',
                    'rationale': 'Voltage drop should not exceed 3% (NEC recommendation)'
                },
                {
                    'template': 'Is wire gauge {gauge} adequate for {ampacity}A load?',
                    'triggers': ['conductor', 'wire', 'cable'],
                    'priority': 'high',
                    'rationale': 'Undersized conductors cause overheating'
                },
                {
                    'template': 'Does breaker rating match conductor ampacity?',
                    'triggers': ['breaker', 'circuit', 'protection'],
                    'priority': 'critical',
                    'rationale': 'Breaker must protect conductor per NEC 240'
                }
            ],
            'verification': [
                {
                    'template': 'Are all circuits properly labeled per NEC 110.22?',
                    'triggers': ['panel', 'directory'],
                    'priority': 'medium',
                    'rationale': 'Circuit identification required for safety and maintenance'
                },
                {
                    'template': 'Has short circuit current been calculated?',
                    'triggers': ['panel', 'transformer', 'bus'],
                    'priority': 'high',
                    'rationale': 'Equipment must be rated for available fault current'
                }
            ]
        }
    
    def _init_mechanical_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize mechanical engineering question library"""
        return {
            'safety': [
                {
                    'template': 'Are mechanical guards provided for rotating equipment?',
                    'triggers': ['motor', 'pump', 'fan', 'coupling'],
                    'priority': 'critical',
                    'rationale': 'OSHA requires guarding of rotating parts'
                },
                {
                    'template': 'Is emergency shutdown accessible and clearly marked?',
                    'triggers': ['equipment', 'system', 'process'],
                    'priority': 'critical',
                    'rationale': 'Emergency stops required within 10 feet per OSHA'
                }
            ],
            'design': [
                {
                    'template': 'What is the NPSH margin for pump {pump_id}?',
                    'triggers': ['pump', 'suction'],
                    'priority': 'high',
                    'rationale': 'Insufficient NPSH causes cavitation and failure'
                },
                {
                    'template': 'Are bearing lubrication intervals specified?',
                    'triggers': ['bearing', 'motor', 'rotating'],
                    'priority': 'medium',
                    'rationale': 'Proper lubrication critical for equipment life'
                },
                {
                    'template': 'Is thermal expansion accounted for in piping design?',
                    'triggers': ['piping', 'hot', 'steam'],
                    'priority': 'high',
                    'rationale': 'Thermal stress causes pipe failure'
                }
            ]
        }
    
    def _init_pid_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize P&ID question library"""
        return {
            'safety': [
                {
                    'template': 'Is pressure relief provided for all blocked-in scenarios?',
                    'triggers': ['valve', 'isolation', 'vessel'],
                    'priority': 'critical',
                    'rationale': 'Blocked outlets require overpressure protection per ASME'
                },
                {
                    'template': 'Are safety interlocks provided to prevent unsafe valve positions?',
                    'triggers': ['valve', 'control', 'actuator'],
                    'priority': 'critical',
                    'rationale': 'Interlocks prevent hazardous operating conditions'
                },
                {
                    'template': 'Is high level alarm provided for vessel {vessel_id}?',
                    'triggers': ['tank', 'vessel', 'drum'],
                    'priority': 'high',
                    'rationale': 'Overfill protection prevents spills and ruptures'
                }
            ],
            'design': [
                {
                    'template': 'Are control valve failure positions (FC/FO) specified?',
                    'triggers': ['control valve', 'FCV', 'PCV'],
                    'priority': 'high',
                    'rationale': 'Valve failure mode must ensure safe state'
                },
                {
                    'template': 'Is instrument air backup provided?',
                    'triggers': ['pneumatic', 'instrument air', 'actuator'],
                    'priority': 'medium',
                    'rationale': 'Loss of instrument air requires failsafe design'
                }
            ]
        }
    
    def _init_civil_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize civil engineering question library"""
        return {
            'design': [
                {
                    'template': 'Does site grading provide positive drainage (min 2%)?',
                    'triggers': ['grading', 'slope', 'drainage'],
                    'priority': 'high',
                    'rationale': 'Inadequate drainage causes ponding and foundation issues'
                },
                {
                    'template': 'Are utilities located and marked per One Call requirements?',
                    'triggers': ['excavation', 'underground', 'utilities'],
                    'priority': 'critical',
                    'rationale': 'Utility strikes are life-safety hazards'
                }
            ]
        }
    
    def _init_structural_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize structural engineering question library"""
        return {
            'design': [
                {
                    'template': 'Does beam deflection meet L/360 criteria for live load?',
                    'triggers': ['beam', 'joist', 'span'],
                    'priority': 'high',
                    'rationale': 'Excessive deflection causes serviceability issues'
                },
                {
                    'template': 'Are connections designed for required strength?',
                    'triggers': ['connection', 'bolt', 'weld'],
                    'priority': 'critical',
                    'rationale': 'Connection failure is catastrophic'
                }
            ]
        }
    
    async def suggest_questions(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
        user_questions_asked: Optional[List[str]] = None
    ) -> QuestionSuggestionResult:
        """
        Generate suggested verification questions
        
        Args:
            diagram: Diagram image or path
            domain: Engineering domain
            context: Additional context from diagram analysis
            user_questions_asked: Questions user has already asked
        
        Returns:
            QuestionSuggestionResult with prioritized suggestions
        """
        logger.info(f"💡 Generating question suggestions for {domain} diagram")
        
        # Step 1: Extract features and identify components
        features = self.reality_anchor.extract_features(diagram, domain=domain)
        
        # Step 2: Get domain-specific question library
        domain_library = self.question_libraries.get(domain, {})
        
        # Step 3: Match questions to detected components
        matched_questions = self._match_questions_to_context(
            domain_library,
            context,
            user_questions_asked
        )
        
        # Step 4: Use o3-pro to generate custom questions
        custom_questions = await self._generate_custom_questions(
            diagram,
            domain,
            context,
            features
        )
        
        # Step 5: Merge and prioritize
        all_questions = matched_questions + custom_questions
        prioritized = self._prioritize_questions(all_questions)
        
        # Step 6: Identify low-confidence areas if evaluator available
        if self.confidence_evaluator and context:
            uncertainty_questions = self._generate_uncertainty_questions(context)
            prioritized.extend(uncertainty_questions)
        
        # Step 7: Remove duplicates and already-asked questions
        final_questions = self._deduplicate_questions(
            prioritized,
            user_questions_asked
        )
        
        # Step 8: Categorize and count
        categories = self._categorize_questions(final_questions)
        critical_count = sum(1 for q in final_questions if q.priority == 'critical')
        
        # Step 9: Generate reasoning
        reasoning = self._generate_reasoning(final_questions, domain, critical_count)
        
        result = QuestionSuggestionResult(
            suggested_questions=final_questions,
            categories=categories,
            critical_count=critical_count,
            reasoning=reasoning
        )
        
        logger.info(f"✅ Generated {len(final_questions)} question suggestions ({critical_count} critical)")
        
        return result
    
    def _match_questions_to_context(
        self,
        domain_library: Dict[str, List[Dict[str, Any]]],
        context: Optional[Dict[str, Any]],
        user_questions: Optional[List[str]]
    ) -> List[SuggestedQuestion]:
        """Match template questions to detected components"""
        
        matched = []
        context_str = str(context).lower() if context else ""
        user_str = " ".join(user_questions or []).lower()
        
        question_id = 0
        for category, questions in domain_library.items():
            for q_template in questions:
                # Check if triggers are present in context
                triggers = q_template.get('triggers', [])
                if any(trigger in context_str for trigger in triggers):
                    # Check if similar question already asked
                    template_keywords = set(q_template['template'].lower().split())
                    if not any(
                        len(template_keywords & set(uq.lower().split())) > 3
                        for uq in (user_questions or [])
                    ):
                        question = SuggestedQuestion(
                            question_id=f"q_{question_id}",
                            question=q_template['template'],
                            priority=q_template['priority'],
                            category=category,
                            rationale=q_template['rationale'],
                            estimated_importance=self._calculate_importance(q_template)
                        )
                        matched.append(question)
                        question_id += 1
        
        return matched
    
    async def _generate_custom_questions(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]],
        features: np.ndarray
    ) -> List[SuggestedQuestion]:
        """Use o3-pro to generate context-specific questions"""
        
        # Build prompt for o3-pro
        prompt = f"""Based on this {domain} diagram analysis, suggest 3-5 critical verification questions that an engineer should ask but might overlook.

Context: {context}

Focus on:
1. Safety-critical items
2. Code compliance (NEC, ASME, IBC, etc.)
3. Design adequacy
4. Potential failure modes

Format each question as:
- [PRIORITY] Question text
  Rationale: Why this is important

Example:
- [CRITICAL] Has arc flash analysis been performed per NFPA 70E?
  Rationale: Arc flash hazards require assessment and labeling for worker safety.
"""
        
        try:
            # Would call o3-pro here
            response = await self.orchestrator.ask_question_pro(prompt)
            
            # Parse response into structured questions
            custom_questions = self._parse_generated_questions(response)
            
            return custom_questions
        
        except Exception as e:
            logger.warning(f"Custom question generation failed: {e}")
            return []
    
    def _parse_generated_questions(self, response: Dict[str, Any]) -> List[SuggestedQuestion]:
        """Parse o3-pro response into structured questions"""
        questions = []
        answer = response.get('answer', '')
        
        lines = answer.split('\n')
        current_question = None
        current_rationale = None
        question_id = 1000  # High number to avoid conflicts
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for priority markers
            if '[CRITICAL]' in line or '[HIGH]' in line or '[MEDIUM]' in line:
                if current_question and current_rationale:
                    # Save previous question
                    priority = 'critical' if '[CRITICAL]' in current_question else 'high'
                    questions.append(SuggestedQuestion(
                        question_id=f"custom_{question_id}",
                        question=current_question.split(']', 1)[1].strip(),
                        priority=priority,
                        category='custom',
                        rationale=current_rationale,
                        estimated_importance=0.8
                    ))
                    question_id += 1
                
                current_question = line
                current_rationale = None
            
            elif 'Rationale:' in line:
                current_rationale = line.split('Rationale:', 1)[1].strip()
        
        # Don't forget last question
        if current_question and current_rationale:
            priority = 'critical' if '[CRITICAL]' in current_question else 'high'
            questions.append(SuggestedQuestion(
                question_id=f"custom_{question_id}",
                question=current_question.split(']', 1)[1].strip(),
                priority=priority,
                category='custom',
                rationale=current_rationale,
                estimated_importance=0.8
            ))
        
        return questions
    
    def _generate_uncertainty_questions(
        self,
        context: Dict[str, Any]
    ) -> List[SuggestedQuestion]:
        """Generate questions for areas with low confidence"""
        
        questions = []
        
        # Check if context has confidence scores
        if 'confidence' in context and context['confidence'] < 0.7:
            questions.append(SuggestedQuestion(
                question_id="uncertainty_1",
                question=f"Can you verify the interpretation of component {context.get('component', 'unknown')}?",
                priority='medium',
                category='verification',
                rationale=f"AI confidence is only {context['confidence']:.0%} for this component",
                estimated_importance=0.6
            ))
        
        return questions
    
    def _calculate_importance(self, question_template: Dict[str, Any]) -> float:
        """Calculate importance score for question"""
        priority_scores = {
            'critical': 1.0,
            'high': 0.75,
            'medium': 0.5,
            'low': 0.25
        }
        
        base_score = priority_scores.get(question_template.get('priority', 'medium'), 0.5)
        
        # Boost if historically effective
        template_text = question_template.get('template', '')
        effectiveness = self.question_effectiveness.get(template_text, 0.5)
        
        return (base_score + effectiveness) / 2
    
    def _prioritize_questions(
        self,
        questions: List[SuggestedQuestion]
    ) -> List[SuggestedQuestion]:
        """Sort questions by importance"""
        
        priority_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        
        return sorted(
            questions,
            key=lambda q: (
                priority_order.get(q.priority, 0),
                q.estimated_importance
            ),
            reverse=True
        )
    
    def _deduplicate_questions(
        self,
        questions: List[SuggestedQuestion],
        user_questions: Optional[List[str]]
    ) -> List[SuggestedQuestion]:
        """Remove duplicate and already-asked questions"""
        
        seen_texts = set()
        unique = []
        
        user_questions_lower = [q.lower() for q in (user_questions or [])]
        
        for question in questions:
            q_text = question.question.lower()
            
            # Check if similar to already-asked question
            is_duplicate = any(
                len(set(q_text.split()) & set(uq.split())) > 3
                for uq in user_questions_lower
            )
            
            if q_text not in seen_texts and not is_duplicate:
                seen_texts.add(q_text)
                unique.append(question)
        
        return unique
    
    def _categorize_questions(
        self,
        questions: List[SuggestedQuestion]
    ) -> Dict[str, int]:
        """Categorize questions for reporting"""
        categories = {}
        for question in questions:
            categories[question.category] = categories.get(question.category, 0) + 1
        return categories
    
    def _generate_reasoning(
        self,
        questions: List[SuggestedQuestion],
        domain: str,
        critical_count: int
    ) -> str:
        """Generate explanation for suggestions"""
        
        if not questions:
            return f"No additional questions recommended - {domain} design appears comprehensive"
        
        reasoning = f"Based on {domain} diagram analysis, I recommend {len(questions)} verification questions:\n\n"
        
        if critical_count > 0:
            reasoning += f"🚨 {critical_count} CRITICAL safety/compliance questions require immediate attention\n"
        
        # Summarize by category
        safety_count = sum(1 for q in questions if q.category == 'safety')
        design_count = sum(1 for q in questions if q.category == 'design')
        verification_count = sum(1 for q in questions if q.category == 'verification')
        
        if safety_count > 0:
            reasoning += f"🛡️  {safety_count} safety-related questions\n"
        if design_count > 0:
            reasoning += f"📐 {design_count} design adequacy questions\n"
        if verification_count > 0:
            reasoning += f"✓ {verification_count} verification questions\n"
        
        reasoning += "\nThese questions help ensure comprehensive review and identify potential issues early."
        
        return reasoning
    
    def record_feedback(
        self,
        question_id: str,
        was_helpful: bool,
        found_issue: bool = False
    ) -> None:
        """Record user feedback to improve future suggestions"""
        
        # Update effectiveness score
        if question_id in self.question_effectiveness:
            current = self.question_effectiveness[question_id]
            new_score = current * 0.8 + (1.0 if found_issue else 0.5 if was_helpful else 0.0) * 0.2
            self.question_effectiveness[question_id] = new_score
        else:
            self.question_effectiveness[question_id] = 0.7 if was_helpful else 0.3
        
        logger.info(f"📊 Recorded feedback for question {question_id}: helpful={was_helpful}, found_issue={found_issue}")


def create_query_suggestion_agent(
    reality_anchor,
    memory_atlas,
    orchestrator,
    **kwargs
) -> QuerySuggestionAgent:
    """Factory function to create query suggestion agent"""
    return QuerySuggestionAgent(
        reality_anchor=reality_anchor,
        memory_atlas=memory_atlas,
        orchestrator=orchestrator,
        **kwargs
    )
