# Planning Agent - Intelligent Analysis Orchestration

## Overview

The **PlanningAgentPro** is a Phase 0 reconnaissance agent that performs quick analysis of engineering drawings to create an intelligent, optimized analysis plan. It uses o3-pro with low reasoning effort to rapidly assess drawings and guide all subsequent analysis phases.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: Images/PDF                                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 0: PLANNING AGENT (o3-pro, low reasoning)           │
│  • Quick scan of first 1-3 pages/images                     │
│  • Detect disciplines (electrical, mechanical, civil, etc.) │
│  • Identify drawing types (P&ID, plan-and-profile, etc.)    │
│  • Assess complexity (simple, medium, complex)              │
│  • Recommend reasoning effort & strategy                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  ANALYSIS PLAN                                              │
│  {                                                          │
│    detected_disciplines: ["civil", "electrical"]            │
│    drawing_types: ["plan-and-profile", "utility"]          │
│    complexity: "medium"                                     │
│    key_features: ["transformers", "trenches", "services"]   │
│    recommended_reasoning: "high"                            │
│    focus_areas: ["equipment locations", "routing"]          │
│  }                                                          │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  GUIDED ANALYSIS (Stages 1-3)                               │
│  • Preprocessor uses detected disciplines                   │
│  • Visual extraction prioritizes key features               │
│  • Context building focuses on identified areas             │
│  • Reasoning effort optimized based on complexity           │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### 1. **Auto-Discipline Detection** 🔍
- **Before**: User must specify `--domain electrical`
- **After**: System analyzes and detects "This is a civil+electrical utility drawing"
- **Result**: More accurate discipline assignment, handles hybrid documents

### 2. **Intelligent Optimization** ⚡
- Adjusts reasoning effort based on complexity
  - Simple drawings → `medium` reasoning (faster, cheaper)
  - Complex drawings → `high` or `maximum` reasoning
- Adjusts concurrent processing based on document density
- Optimizes chunking strategy based on layout

### 3. **Guided Focus** 🎯
- Identifies specific components: "3 transformers, 12 service laterals, 5 crossings"
- Subsequent agents know exactly what to prioritize
- Reduces hallucination by providing a "shopping list"
- Improves extraction accuracy

### 4. **Better User Experience** 🚀
- **Simple command**: `python edisonpro.py --images ./input --interactive`
- System handles all the complexity automatically
- Transparent: Shows planning results before deep analysis
- Optional override: Can still force manual domain if needed

### 5. **Cost & Performance** 💰
- Planning phase: ~15-30 seconds, low reasoning (cheap)
- Benefit: Avoids wasted effort on wrong domains/strategies
- Net result: Often faster + cheaper + more accurate

## Usage

### Auto-Planning Mode (Default)
```bash
# System automatically detects everything
python edisonpro.py --images ./utility_plans --interactive
```

**Output**:
```
🔍 PLANNING PHASE: Quick reconnaissance with o3-pro...
   Analyzing 2 image(s) for characteristics...

====================================================================
📋 ANALYSIS PLAN CREATED
====================================================================
🎯 Detected Disciplines: CIVIL + ELECTRICAL
📐 Drawing Type(s): plan-and-profile, underground distribution
🟡 Complexity: MEDIUM
🧠 Recommended Reasoning: HIGH
⏱️  Estimated Duration: 6 minutes

🔍 Key Features Identified:
   1. 480V service laterals
   2. Underground trenching
   3. Transformer pads (3 locations)
   4. Utility crossings (water/gas)
   5. Elevation markers

🎯 Analysis Focus:
   • Equipment identification and locations
   • Routing paths and trench depths
   • Elevation data and grades

📊 Confidence: 92.5%
====================================================================

📋 Domain: CIVIL + ELECTRICAL
🧠 Reasoning Effort: HIGH

🖼️  Stage 1: Enhanced image processing with o3-pro reasoning...
```

### Manual Override (Disable Auto-Planning)
```bash
# Force specific domain, skip planning
python edisonpro.py --images ./plans --domain electrical --no-auto-plan --interactive
```

### With User Hint (Planning Validates)
```bash
# User suggests domain, planning validates and may refine
python edisonpro.py --images ./plans --domain utility --interactive
```

## Planning Prompt Structure

The planning agent asks o3-pro to analyze drawings and respond in structured JSON format:

```json
{
  "detected_disciplines": ["civil", "electrical"],
  "drawing_types": ["plan-and-profile", "underground utility"],
  "complexity": "medium",
  "key_features": [
    "480V service laterals (12 locations)",
    "Transformer pads (3 locations)",
    "Underground trenching (8-10 ft depth)",
    "Utility crossings (water/gas/telecom)",
    "Station points with elevations"
  ],
  "recommended_reasoning": "high",
  "estimated_duration_minutes": 6,
  "focus_areas": [
    "electrical equipment identification",
    "trenching and routing paths",
    "elevation data and grades"
  ],
  "special_considerations": [
    "multiple utility crossings require careful analysis",
    "handwritten notes on transformer specs"
  ],
  "confidence": 0.925
}
```

## Agent Configuration

The planning agent automatically configures downstream agents:

```python
agent_config = {
    "domain": "civil,electrical",           # Detected disciplines
    "reasoning_effort": "high",             # Based on complexity
    "enable_smart_chunking": True,          # Always enabled
    "max_concurrent_pages": 5,              # Adjusted for complexity
    "focus_keywords": [                     # Key features to prioritize
        "transformers",
        "service laterals", 
        "trenching",
        "elevations"
    ]
}
```

## Implementation Details

### Class: `PlanningAgentPro`

**Key Methods**:
- `create_analysis_plan()`: Main entry point, orchestrates planning phase
- `_build_planning_prompt()`: Constructs structured prompt for o3-pro
- `_parse_planning_response()`: Parses JSON response into `AnalysisPlan` object
- `_display_plan_summary()`: Shows plan to user before deep analysis
- `_create_fallback_plan()`: Safe defaults if planning fails

### Dataclass: `AnalysisPlan`

```python
@dataclass
class AnalysisPlan:
    detected_disciplines: List[str]          # ["civil", "electrical"]
    drawing_types: List[str]                 # ["plan-and-profile"]
    complexity: str                          # "simple"|"medium"|"complex"
    key_features: List[str]                  # Specific components detected
    recommended_reasoning: str               # "low"|"medium"|"high"|"maximum"
    estimated_duration_minutes: int          # Time estimate
    focus_areas: List[str]                   # What to prioritize
    special_considerations: List[str]        # Quality issues, etc.
    agent_config: Dict[str, Any]            # Config for downstream agents
    confidence: float                        # Planning confidence (0-1)
```

## Integration with Orchestrator

### `DiagramAnalysisOrchestratorPro`

**Initialization**:
```python
self.planner = PlanningAgentPro(self.client, self.deployment_name)
self.analysis_plan = None  # Set during analysis
```

**Analysis Flow**:
```python
async def analyze_images_from_folder(self, input_folder, domain, auto_plan=True):
    # PHASE 0: Planning
    if auto_plan:
        self.analysis_plan = await self.planner.create_analysis_plan(...)
        domain = self.analysis_plan.agent_config["domain"]
        self.reasoning_effort = self.analysis_plan.agent_config["reasoning_effort"]
    
    # Use optimized settings from plan
    self.preprocessor = DocumentPreprocessorPro(..., domain=domain)
    
    # Continue with guided analysis...
```

## Performance Characteristics

| Phase | Time | Reasoning | Cost | Purpose |
|-------|------|-----------|------|---------|
| Phase 0 (Planning) | 15-30s | Low | ~$0.02 | Quick scan, strategy |
| Phase 1 (Preprocessing) | 2-5 min | High | ~$0.20 | Deep analysis |
| Phase 2 (Visual) | 1-3 min | High | ~$0.15 | Element extraction |
| Phase 3 (Context) | 30s-1m | - | ~$0.03 | Index building |

**Total with Planning**: ~5-10 minutes, ~$0.40 per analysis  
**Benefit**: More accurate results, optimized strategy, better user experience

## Hybrid Domain Examples

### Utility Drawing (Civil + Electrical)
```bash
python edisonpro.py --images ./utility_plans --interactive
# Detects: civil,electrical
# Focus: Underground routing, transformers, service laterals, elevations
```

### MEP Building Systems (Mechanical + Electrical + P&ID)
```bash
python edisonpro.py --images ./building_plans --interactive
# Detects: mechanical,electrical,pid
# Focus: HVAC systems, power distribution, control loops
```

### Process Plant (Mechanical + P&ID)
```bash
python edisonpro.py --pdf process_diagrams.pdf --interactive
# Detects: mechanical,pid
# Focus: Piping, instrumentation, process flow, control valves
```

## Fallback Behavior

If planning fails (network error, parsing error, etc.):
- Falls back to user-specified domain or "general"
- Uses safe defaults: `high` reasoning, standard concurrency
- Logs warning and continues analysis
- Confidence set to 0.5 to indicate planning didn't run

## Future Enhancements

1. **Multi-stage Planning**: Re-plan between phases if initial assessment was wrong
2. **Learning from History**: Track which plans led to best results
3. **Cost Optimization**: More aggressive reasoning reduction for simple drawings
4. **Sheet Correlation**: For multi-sheet documents, plan coordination strategy
5. **Quality Assessment**: Detect poor scan quality and recommend preprocessing

## Conclusion

The Planning Agent transforms EDISON PRO from a user-directed tool to an **intelligent, self-guiding analysis engine**. It embodies the principle of "work smarter, not harder" by investing 30 seconds upfront to optimize 5-10 minutes of downstream analysis.

**Key Innovation**: Using o3-pro's reasoning capabilities not just for deep analysis, but also for strategic planning - creating a truly autonomous engineering document analysis system.
