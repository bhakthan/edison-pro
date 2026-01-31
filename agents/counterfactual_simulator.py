"""
Counterfactual Scenario Simulator
"What-if" analysis - simulate design changes and predict outcomes.

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
class DesignParameter:
    """Represents a design parameter that can be varied"""
    parameter_id: str
    name: str
    current_value: Any
    parameter_type: str  # 'continuous', 'discrete', 'categorical'
    valid_range: Optional[Tuple[Any, Any]] = None
    valid_options: Optional[List[Any]] = None
    unit: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'parameter_id': self.parameter_id,
            'name': self.name,
            'current_value': self.current_value,
            'parameter_type': self.parameter_type,
            'valid_range': self.valid_range,
            'valid_options': self.valid_options,
            'unit': self.unit
        }


@dataclass
class ScenarioOutcome:
    """Predicted outcome of a scenario"""
    scenario_id: str
    description: str
    modified_parameters: Dict[str, Any]
    predicted_impact: Dict[str, Any]
    performance_metrics: Dict[str, float]
    cost_delta: Optional[float] = None
    risk_delta: Optional[float] = None
    feasibility_score: float = 0.5
    confidence: float = 0.5
    rationale: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self.scenario_id,
            'description': self.description,
            'modified_parameters': self.modified_parameters,
            'predicted_impact': self.predicted_impact,
            'performance_metrics': self.performance_metrics,
            'cost_delta': self.cost_delta,
            'risk_delta': self.risk_delta,
            'feasibility_score': float(self.feasibility_score),
            'confidence': float(self.confidence),
            'rationale': self.rationale
        }


@dataclass
class SimulationResult:
    """Result of counterfactual simulation"""
    baseline_scenario: Dict[str, Any]
    alternative_scenarios: List[ScenarioOutcome]
    recommended_scenario: Optional[ScenarioOutcome]
    comparison_matrix: Dict[str, List[float]]
    optimization_insights: List[str]
    tradeoff_analysis: str


class CounterfactualSimulator:
    """
    Simulates "what-if" scenarios for engineering design optimization.
    
    Key Innovation: Design optimization through AI-driven exploration
    
    Capabilities:
    1. Identify tunable design parameters
    2. Generate alternative scenarios
    3. Predict outcomes using o3-pro reasoning
    4. Compare scenarios across multiple dimensions
    5. Recommend optimal design with tradeoff analysis
    
    Integration Points:
    - Anticipatory Simulation: Generate alternative configurations
    - o3-pro: Reason about consequences of changes
    - Memory Atlas: Learn from past what-if analyses
    - Reality Anchor: Baseline feature extraction
    """
    
    def __init__(
        self,
        orchestrator,
        anticipatory_agent=None,
        memory_atlas=None,
        max_scenarios: int = 10
    ):
        """
        Initialize Counterfactual Simulator
        
        Args:
            orchestrator: o3-pro orchestrator for outcome prediction
            anticipatory_agent: Optional anticipatory simulation agent
            memory_atlas: Optional memory for learning
            max_scenarios: Maximum scenarios to generate
        """
        self.orchestrator = orchestrator
        self.anticipatory_agent = anticipatory_agent
        self.memory_atlas = memory_atlas
        self.max_scenarios = max_scenarios
        
        # Domain-specific parameter libraries
        self.parameter_libraries = {
            'electrical': self._init_electrical_parameters(),
            'mechanical': self._init_mechanical_parameters(),
            'pid': self._init_pid_parameters(),
            'civil': self._init_civil_parameters()
        }
        
        logger.info(f"🔮 Counterfactual Simulator initialized (max {max_scenarios} scenarios)")
    
    def _init_electrical_parameters(self) -> List[DesignParameter]:
        """Initialize electrical design parameters"""
        return [
            DesignParameter(
                parameter_id='wire_gauge',
                name='Wire Gauge',
                current_value=12,
                parameter_type='discrete',
                valid_options=[14, 12, 10, 8, 6, 4, 2, 1, '1/0', '2/0', '3/0', '4/0'],
                unit='AWG'
            ),
            DesignParameter(
                parameter_id='breaker_rating',
                name='Circuit Breaker Rating',
                current_value=20,
                parameter_type='discrete',
                valid_options=[15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 125, 150, 175, 200],
                unit='A'
            ),
            DesignParameter(
                parameter_id='transformer_size',
                name='Transformer Size',
                current_value=75,
                parameter_type='discrete',
                valid_options=[15, 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000],
                unit='kVA'
            ),
            DesignParameter(
                parameter_id='conduit_size',
                name='Conduit Size',
                current_value=1.0,
                parameter_type='discrete',
                valid_options=[0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
                unit='inch'
            ),
            DesignParameter(
                parameter_id='voltage_level',
                name='System Voltage',
                current_value=480,
                parameter_type='discrete',
                valid_options=[120, 208, 240, 277, 480, 600],
                unit='V'
            )
        ]
    
    def _init_mechanical_parameters(self) -> List[DesignParameter]:
        """Initialize mechanical design parameters"""
        return [
            DesignParameter(
                parameter_id='pipe_diameter',
                name='Pipe Diameter',
                current_value=4,
                parameter_type='discrete',
                valid_options=[2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24],
                unit='inch'
            ),
            DesignParameter(
                parameter_id='pump_size',
                name='Pump Horsepower',
                current_value=10,
                parameter_type='discrete',
                valid_options=[1, 1.5, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50],
                unit='HP'
            ),
            DesignParameter(
                parameter_id='fan_cfm',
                name='Fan Airflow',
                current_value=5000,
                parameter_type='continuous',
                valid_range=(1000, 50000),
                unit='CFM'
            ),
            DesignParameter(
                parameter_id='insulation_thickness',
                name='Insulation Thickness',
                current_value=2,
                parameter_type='discrete',
                valid_options=[1, 1.5, 2, 2.5, 3, 4],
                unit='inch'
            )
        ]
    
    def _init_pid_parameters(self) -> List[DesignParameter]:
        """Initialize P&ID design parameters"""
        return [
            DesignParameter(
                parameter_id='pressure_rating',
                name='Pressure Rating',
                current_value=150,
                parameter_type='discrete',
                valid_options=[150, 300, 400, 600, 900, 1500, 2500],
                unit='psi'
            ),
            DesignParameter(
                parameter_id='valve_size',
                name='Control Valve Size',
                current_value=4,
                parameter_type='discrete',
                valid_options=[1, 1.5, 2, 3, 4, 6, 8, 10, 12],
                unit='inch'
            ),
            DesignParameter(
                parameter_id='relief_setpoint',
                name='Relief Valve Setpoint',
                current_value=100,
                parameter_type='continuous',
                valid_range=(50, 500),
                unit='psi'
            )
        ]
    
    def _init_civil_parameters(self) -> List[DesignParameter]:
        """Initialize civil design parameters"""
        return [
            DesignParameter(
                parameter_id='grade_slope',
                name='Grading Slope',
                current_value=2.0,
                parameter_type='continuous',
                valid_range=(0.5, 10.0),
                unit='%'
            ),
            DesignParameter(
                parameter_id='pavement_thickness',
                name='Pavement Thickness',
                current_value=4,
                parameter_type='continuous',
                valid_range=(3, 12),
                unit='inch'
            )
        ]
    
    async def simulate_scenarios(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]] = None,
        parameters_to_vary: Optional[List[str]] = None,
        optimization_goal: str = 'balanced'  # 'cost', 'performance', 'safety', 'balanced'
    ) -> SimulationResult:
        """
        Simulate what-if scenarios for design optimization
        
        Args:
            diagram: Diagram image or path
            domain: Engineering domain
            context: Current design context
            parameters_to_vary: Specific parameters to modify (None = auto-select)
            optimization_goal: What to optimize for
        
        Returns:
            SimulationResult with alternative scenarios and recommendations
        """
        logger.info(f"🔮 Starting counterfactual simulation (goal: {optimization_goal})")
        
        # Step 1: Establish baseline
        baseline = self._establish_baseline(diagram, domain, context)
        
        # Step 2: Identify tunable parameters
        tunable_params = self._identify_tunable_parameters(
            domain, context, parameters_to_vary
        )
        logger.info(f"   Identified {len(tunable_params)} tunable parameters")
        
        # Step 3: Generate alternative scenarios
        scenarios = await self._generate_scenarios(
            baseline, tunable_params, domain, optimization_goal
        )
        logger.info(f"   Generated {len(scenarios)} alternative scenarios")
        
        # Step 4: Predict outcomes for each scenario
        evaluated_scenarios = await self._evaluate_scenarios(
            scenarios, baseline, domain, context
        )
        
        # Step 5: Compare and rank scenarios
        comparison = self._build_comparison_matrix(baseline, evaluated_scenarios)
        
        # Step 6: Identify recommended scenario
        recommended = self._select_best_scenario(
            evaluated_scenarios, optimization_goal
        )
        
        # Step 7: Generate insights
        insights = self._generate_optimization_insights(
            baseline, evaluated_scenarios, recommended
        )
        
        # Step 8: Tradeoff analysis
        tradeoffs = self._analyze_tradeoffs(evaluated_scenarios, optimization_goal)
        
        result = SimulationResult(
            baseline_scenario=baseline,
            alternative_scenarios=evaluated_scenarios,
            recommended_scenario=recommended,
            comparison_matrix=comparison,
            optimization_insights=insights,
            tradeoff_analysis=tradeoffs
        )
        
        logger.info(f"✅ Simulation complete: {len(evaluated_scenarios)} scenarios evaluated")
        if recommended:
            logger.info(f"   🎯 Recommended: {recommended.description}")
        
        return result
    
    def _establish_baseline(
        self,
        diagram: Any,
        domain: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Establish baseline scenario from current design"""
        
        return {
            'scenario_id': 'baseline',
            'description': 'Current Design',
            'parameters': context.get('parameters', {}) if context else {},
            'metrics': {
                'cost': 1.0,  # Baseline = 1.0
                'performance': 1.0,
                'safety': 1.0,
                'efficiency': 1.0
            }
        }
    
    def _identify_tunable_parameters(
        self,
        domain: str,
        context: Optional[Dict[str, Any]],
        explicit_params: Optional[List[str]]
    ) -> List[DesignParameter]:
        """Identify which parameters can be varied"""
        
        if explicit_params:
            # Use explicit list
            library = self.parameter_libraries.get(domain, [])
            return [p for p in library if p.parameter_id in explicit_params]
        
        # Auto-select based on context
        library = self.parameter_libraries.get(domain, [])
        
        # In production, would analyze context to determine relevant parameters
        # For now, return all domain parameters
        return library[:5]  # Limit to prevent explosion
    
    async def _generate_scenarios(
        self,
        baseline: Dict[str, Any],
        parameters: List[DesignParameter],
        domain: str,
        goal: str
    ) -> List[Dict[str, Any]]:
        """Generate alternative scenarios by varying parameters"""
        
        scenarios = []
        
        # Strategy 1: Single parameter variations
        for param in parameters[:3]:  # Limit to top 3 parameters
            # Increase
            if param.parameter_type == 'discrete' and param.valid_options:
                current_idx = param.valid_options.index(param.current_value)
                if current_idx < len(param.valid_options) - 1:
                    new_value = param.valid_options[current_idx + 1]
                    scenarios.append({
                        'type': 'single_increase',
                        'parameter': param.parameter_id,
                        'parameter_name': param.name,
                        'old_value': param.current_value,
                        'new_value': new_value,
                        'description': f"Increase {param.name} from {param.current_value} to {new_value} {param.unit or ''}"
                    })
            
            # Decrease
            if param.parameter_type == 'discrete' and param.valid_options:
                current_idx = param.valid_options.index(param.current_value)
                if current_idx > 0:
                    new_value = param.valid_options[current_idx - 1]
                    scenarios.append({
                        'type': 'single_decrease',
                        'parameter': param.parameter_id,
                        'parameter_name': param.name,
                        'old_value': param.current_value,
                        'new_value': new_value,
                        'description': f"Decrease {param.name} from {param.current_value} to {new_value} {param.unit or ''}"
                    })
        
        # Strategy 2: Coordinated changes (if using anticipatory agent)
        if self.anticipatory_agent and len(parameters) >= 2:
            # Simulate coordinated optimization
            scenarios.append({
                'type': 'coordinated',
                'parameters': [p.parameter_id for p in parameters[:2]],
                'description': f"Optimize {parameters[0].name} and {parameters[1].name} together"
            })
        
        return scenarios[:self.max_scenarios]
    
    async def _evaluate_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        baseline: Dict[str, Any],
        domain: str,
        context: Optional[Dict[str, Any]]
    ) -> List[ScenarioOutcome]:
        """Evaluate outcomes of each scenario using o3-pro"""
        
        # Parallel evaluation
        tasks = []
        for i, scenario in enumerate(scenarios):
            task = self._evaluate_single_scenario(
                i, scenario, baseline, domain, context
            )
            tasks.append(task)
        
        outcomes = await asyncio.gather(*tasks)
        
        return outcomes
    
    async def _evaluate_single_scenario(
        self,
        scenario_id: int,
        scenario: Dict[str, Any],
        baseline: Dict[str, Any],
        domain: str,
        context: Optional[Dict[str, Any]]
    ) -> ScenarioOutcome:
        """Evaluate a single scenario"""
        
        # Build evaluation prompt
        prompt = f"""Analyze this design change scenario for a {domain} engineering system:

BASELINE: {baseline.get('description', 'Current design')}
Baseline Metrics: {baseline.get('metrics', {})}

PROPOSED CHANGE: {scenario['description']}

Predict the outcomes of this change across multiple dimensions:

1. PERFORMANCE IMPACT
   - How will this affect system performance?
   - Capacity/capability changes?
   
2. COST IMPACT
   - Material cost change (% increase/decrease)?
   - Installation cost impact?
   - Lifecycle cost considerations?
   
3. SAFETY/RISK IMPACT
   - Safety improvements or concerns?
   - New risks introduced?
   - Compliance implications?
   
4. FEASIBILITY
   - Is this change practical to implement?
   - Any constructability issues?
   - Standard/available equipment?
   
5. OVERALL ASSESSMENT
   - Recommend this change? (Yes/No/Maybe)
   - Key advantages?
   - Key disadvantages?
   - Confidence in prediction (0-100%)?

Provide quantitative estimates where possible."""

        try:
            response = await self.orchestrator.ask_question_pro(
                prompt,
                reasoning_effort='high'  # Need deep analysis for predictions
            )
            
            # Parse response
            outcome = self._parse_scenario_evaluation(
                scenario_id, scenario, response.get('answer', '')
            )
            
            return outcome
            
        except Exception as e:
            logger.warning(f"Scenario {scenario_id} evaluation failed: {e}")
            
            return ScenarioOutcome(
                scenario_id=f"scenario_{scenario_id}",
                description=scenario['description'],
                modified_parameters=scenario,
                predicted_impact={'error': str(e)},
                performance_metrics={'feasibility': 0.0},
                feasibility_score=0.0,
                confidence=0.0,
                rationale=f"Evaluation failed: {str(e)}"
            )
    
    def _parse_scenario_evaluation(
        self,
        scenario_id: int,
        scenario: Dict[str, Any],
        response: str
    ) -> ScenarioOutcome:
        """Parse o3-pro evaluation into structured outcome"""
        
        import re
        
        response_lower = response.lower()
        
        # Extract cost delta (look for percentages)
        cost_matches = re.findall(r'cost.*?(\+|-)?(\d+)%', response_lower)
        if cost_matches:
            sign = -1 if cost_matches[0][0] == '-' else 1
            cost_delta = sign * float(cost_matches[0][1]) / 100
        else:
            cost_delta = 0.0
        
        # Extract recommendation
        if 'yes' in response_lower and 'recommend' in response_lower:
            recommendation = 'recommended'
            feasibility = 0.8
        elif 'no' in response_lower and 'not recommend' in response_lower:
            recommendation = 'not_recommended'
            feasibility = 0.3
        else:
            recommendation = 'maybe'
            feasibility = 0.5
        
        # Extract confidence
        confidence_match = re.search(r'confidence.*?(\d+)%', response_lower)
        confidence = float(confidence_match.group(1)) / 100 if confidence_match else 0.7
        
        # Performance metrics (simplified extraction)
        metrics = {
            'cost_multiplier': 1.0 + cost_delta,
            'performance_score': 0.8 if 'improve' in response_lower else 0.5,
            'safety_score': 0.9 if 'safe' in response_lower or 'safer' in response_lower else 0.7,
            'feasibility': feasibility
        }
        
        # Extract key impacts
        impact = {
            'recommendation': recommendation,
            'cost_change': f"{cost_delta:+.1%}",
            'advantages': self._extract_list(response, ['advantage', 'benefit', 'pro']),
            'disadvantages': self._extract_list(response, ['disadvantage', 'drawback', 'con'])
        }
        
        return ScenarioOutcome(
            scenario_id=f"scenario_{scenario_id}",
            description=scenario['description'],
            modified_parameters=scenario,
            predicted_impact=impact,
            performance_metrics=metrics,
            cost_delta=cost_delta,
            feasibility_score=feasibility,
            confidence=confidence,
            rationale=response[:500]  # First 500 chars
        )
    
    def _extract_list(self, text: str, keywords: List[str]) -> List[str]:
        """Extract bulleted/numbered lists related to keywords"""
        items = []
        lines = text.split('\n')
        
        in_relevant_section = False
        for line in lines:
            line = line.strip()
            
            # Check if we're in a relevant section
            if any(keyword in line.lower() for keyword in keywords):
                in_relevant_section = True
                continue
            
            # Extract list items
            if in_relevant_section and (line.startswith('-') or line.startswith('•') or re.match(r'^\d+\.', line)):
                items.append(line.lstrip('-•0123456789. '))
            elif in_relevant_section and not line:
                in_relevant_section = False
        
        return items[:3]  # Top 3
    
    def _build_comparison_matrix(
        self,
        baseline: Dict[str, Any],
        scenarios: List[ScenarioOutcome]
    ) -> Dict[str, List[float]]:
        """Build comparison matrix across all scenarios"""
        
        matrix = {
            'scenario_names': [s.description for s in scenarios],
            'cost': [s.performance_metrics.get('cost_multiplier', 1.0) for s in scenarios],
            'performance': [s.performance_metrics.get('performance_score', 0.5) for s in scenarios],
            'safety': [s.performance_metrics.get('safety_score', 0.5) for s in scenarios],
            'feasibility': [s.feasibility_score for s in scenarios],
            'confidence': [s.confidence for s in scenarios]
        }
        
        return matrix
    
    def _select_best_scenario(
        self,
        scenarios: List[ScenarioOutcome],
        goal: str
    ) -> Optional[ScenarioOutcome]:
        """Select best scenario based on optimization goal"""
        
        if not scenarios:
            return None
        
        # Weight factors based on goal
        weights = {
            'cost': {'cost_multiplier': -1.0, 'performance_score': 0.3, 'safety_score': 0.5, 'feasibility': 0.5},
            'performance': {'cost_multiplier': -0.3, 'performance_score': 1.0, 'safety_score': 0.5, 'feasibility': 0.5},
            'safety': {'cost_multiplier': -0.2, 'performance_score': 0.3, 'safety_score': 1.0, 'feasibility': 0.5},
            'balanced': {'cost_multiplier': -0.4, 'performance_score': 0.6, 'safety_score': 0.8, 'feasibility': 0.7}
        }
        
        goal_weights = weights.get(goal, weights['balanced'])
        
        # Score each scenario
        scored = []
        for scenario in scenarios:
            score = 0.0
            for metric, weight in goal_weights.items():
                value = scenario.performance_metrics.get(metric, 0.5)
                score += value * weight * scenario.confidence  # Weight by confidence
            
            scored.append((score, scenario))
        
        # Return highest scored
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored[0][1] if scored else None
    
    def _generate_optimization_insights(
        self,
        baseline: Dict[str, Any],
        scenarios: List[ScenarioOutcome],
        recommended: Optional[ScenarioOutcome]
    ) -> List[str]:
        """Generate optimization insights"""
        
        insights = []
        
        if recommended:
            insights.append(f"🎯 Recommended: {recommended.description}")
            
            if recommended.cost_delta:
                if recommended.cost_delta < 0:
                    insights.append(f"💰 Cost savings: {-recommended.cost_delta:.1%}")
                else:
                    insights.append(f"💰 Cost increase: {recommended.cost_delta:.1%}")
            
            if recommended.predicted_impact.get('advantages'):
                insights.append(f"✅ Key advantage: {recommended.predicted_impact['advantages'][0]}")
        
        # Find best cost scenario
        cost_optimal = min(scenarios, key=lambda s: s.performance_metrics.get('cost_multiplier', 1.0))
        if cost_optimal != recommended:
            insights.append(f"💵 Most economical: {cost_optimal.description} (saves {(1.0 - cost_optimal.performance_metrics.get('cost_multiplier', 1.0)):.1%})")
        
        # Find best performance scenario
        perf_optimal = max(scenarios, key=lambda s: s.performance_metrics.get('performance_score', 0.0))
        if perf_optimal != recommended:
            insights.append(f"🚀 Highest performance: {perf_optimal.description}")
        
        return insights
    
    def _analyze_tradeoffs(
        self,
        scenarios: List[ScenarioOutcome],
        goal: str
    ) -> str:
        """Analyze tradeoffs between scenarios"""
        
        analysis = f"TRADEOFF ANALYSIS (Optimization Goal: {goal.upper()})\n"
        analysis += "="*60 + "\n\n"
        
        for scenario in scenarios[:5]:  # Top 5
            analysis += f"{scenario.description}\n"
            analysis += f"  Cost: {scenario.performance_metrics.get('cost_multiplier', 1.0):.2f}x baseline\n"
            analysis += f"  Performance: {scenario.performance_metrics.get('performance_score', 0.5):.0%}\n"
            analysis += f"  Safety: {scenario.performance_metrics.get('safety_score', 0.5):.0%}\n"
            analysis += f"  Feasibility: {scenario.feasibility_score:.0%}\n"
            analysis += f"  Confidence: {scenario.confidence:.0%}\n\n"
        
        return analysis


def create_counterfactual_simulator(
    orchestrator,
    **kwargs
) -> CounterfactualSimulator:
    """Factory function to create counterfactual simulator"""
    return CounterfactualSimulator(
        orchestrator=orchestrator,
        **kwargs
    )
