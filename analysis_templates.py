"""
Analysis Templates for EDISON PRO
Author: Srikanth Bhakthan - Microsoft

Predefined analysis templates for common engineering diagram analysis scenarios.
Each template includes:
- Description and use case
- Recommended domain and reasoning effort
- Pre-configured questions sequence
- Expected output formats
- Quality metrics to check
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json


class TemplateCategory(Enum):
    """Categories of analysis templates"""
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    PID = "pid"
    CIVIL = "civil"
    STRUCTURAL = "structural"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    GENERAL = "general"


@dataclass
class AnalysisQuestion:
    """Single question in an analysis template"""
    question: str
    purpose: str  # Why this question is asked
    expected_format: str  # table, text, chart, export
    requires_code_agent: bool = False
    priority: int = 1  # 1=critical, 2=important, 3=optional


@dataclass
class AnalysisTemplate:
    """Complete analysis template"""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    use_case: str
    recommended_domain: str
    recommended_reasoning: str  # low, medium, high, maximum
    questions: List[AnalysisQuestion]
    output_formats: List[str]  # PDF, Excel, CSV, HTML, etc.
    quality_checks: List[str]  # What to verify
    estimated_time_minutes: int
    tags: List[str]


class TemplateLibrary:
    """Library of predefined analysis templates"""
    
    def __init__(self):
        self.templates: Dict[str, AnalysisTemplate] = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize all predefined templates"""
        
        # 1. Electrical Load Study Template
        self.templates['electrical_load_study'] = AnalysisTemplate(
            template_id='electrical_load_study',
            name='Electrical Load Study',
            description='Complete electrical load analysis with power calculations and distribution assessment',
            category=TemplateCategory.ELECTRICAL,
            use_case='Analyzing electrical distribution systems, calculating loads, and verifying capacity',
            recommended_domain='electrical',
            recommended_reasoning='high',
            questions=[
                AnalysisQuestion(
                    question="What is the overall system voltage and frequency?",
                    purpose="Establish baseline electrical parameters",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Show all transformers as a table with their primary voltage, secondary voltage, and kVA ratings",
                    purpose="Catalog all transformation points",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="List all circuit breakers with their amperage ratings, trip settings, and protected circuits",
                    purpose="Document protection devices",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Calculate the total connected load in kW across all circuits",
                    purpose="Determine total system demand",
                    expected_format="text",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Create a bar chart showing load distribution by circuit or panel",
                    purpose="Visualize load distribution",
                    expected_format="chart",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="What is the estimated demand factor and diversity factor for the system?",
                    purpose="Assess realistic operating conditions",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Export all electrical equipment data to CSV with specifications",
                    purpose="Create exportable equipment schedule",
                    expected_format="export",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="What potential overload conditions or capacity issues exist?",
                    purpose="Identify design concerns",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
            ],
            output_formats=['PDF Report', 'Excel Tables', 'CSV Export', 'Interactive Charts'],
            quality_checks=[
                'All transformers properly rated for load',
                'Circuit breakers sized correctly',
                'Voltage drop within acceptable limits',
                'Adequate spare capacity (20%+ recommended)',
                'Proper grounding and bonding shown',
            ],
            estimated_time_minutes=15,
            tags=['electrical', 'load-study', 'power-systems', 'capacity-planning']
        )
        
        # 2. P&ID Safety Review Template
        self.templates['pid_safety_review'] = AnalysisTemplate(
            template_id='pid_safety_review',
            name='P&ID Safety System Review',
            description='Comprehensive safety system analysis for process diagrams',
            category=TemplateCategory.SAFETY,
            use_case='Reviewing process safety systems, interlocks, and emergency shutdown procedures',
            recommended_domain='pid',
            recommended_reasoning='high',
            questions=[
                AnalysisQuestion(
                    question="Identify all safety instrumented systems (SIS) and their safety integrity levels (SIL)",
                    purpose="Document safety-critical systems",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="List all pressure relief devices with their set pressures and discharge locations",
                    purpose="Catalog overpressure protection",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What emergency shutdown (ESD) sequences are shown and what triggers them?",
                    purpose="Understand emergency response",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Show all high-high and low-low alarms as a table with their setpoints",
                    purpose="Document critical alarm points",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Identify all interlock conditions and the equipment they protect",
                    purpose="Map safety interlock logic",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What fire protection and detection systems are integrated into the P&ID?",
                    purpose="Assess fire safety provisions",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Create a table of all instruments involved in safety functions with their tag numbers and functions",
                    purpose="Create safety instrument schedule",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="What potential single points of failure exist in the safety systems?",
                    purpose="Identify vulnerability points",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
            ],
            output_formats=['Safety Report PDF', 'Excel Safety Matrix', 'Interlock Schedule'],
            quality_checks=[
                'All relief devices properly sized and located',
                'Redundancy for critical safety functions',
                'ESD logic clearly documented',
                'Alarms have appropriate setpoints',
                'Compliance with IEC 61511 or ISA 84',
            ],
            estimated_time_minutes=20,
            tags=['pid', 'safety', 'interlocks', 'relief-devices', 'sis']
        )
        
        # 3. Civil Site Plan Analysis Template
        self.templates['civil_site_analysis'] = AnalysisTemplate(
            template_id='civil_site_analysis',
            name='Civil Site Plan Analysis',
            description='Site layout analysis including grading, drainage, and utilities',
            category=TemplateCategory.CIVIL,
            use_case='Analyzing site plans for grading, drainage, access, and utility coordination',
            recommended_domain='civil',
            recommended_reasoning='medium',
            questions=[
                AnalysisQuestion(
                    question="What are the existing and proposed grades at key locations?",
                    purpose="Understand site topography changes",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Describe the drainage system including catch basins, storm sewers, and discharge points",
                    purpose="Map stormwater management",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="List all underground utilities shown (water, sewer, electric, gas, telecom) with their depths",
                    purpose="Document utility coordination",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What are the pavement types, thicknesses, and design specifications?",
                    purpose="Catalog pavement construction",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Calculate the total site area and disturbed area in acres or square feet",
                    purpose="Quantify site impacts",
                    expected_format="text",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="What access points, driveways, and circulation patterns are shown?",
                    purpose="Assess site access",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Are there any utility conflicts or crossing issues that need resolution?",
                    purpose="Identify coordination problems",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Export site data to CSV including elevations, areas, and utility information",
                    purpose="Create site data export",
                    expected_format="export",
                    requires_code_agent=True,
                    priority=3
                ),
            ],
            output_formats=['Site Analysis Report', 'Utility Schedule', 'Grading Summary'],
            quality_checks=[
                'Adequate drainage slope (min 2%)',
                'Utility clearances maintained',
                'ADA-compliant slopes and access',
                'Proper erosion control provisions',
                'Fire access lanes adequate',
            ],
            estimated_time_minutes=12,
            tags=['civil', 'site-plan', 'grading', 'utilities', 'drainage']
        )
        
        # 4. Mechanical Equipment Schedule Template
        self.templates['mechanical_equipment_schedule'] = AnalysisTemplate(
            template_id='mechanical_equipment_schedule',
            name='Mechanical Equipment Schedule',
            description='Generate comprehensive equipment schedules for mechanical systems',
            category=TemplateCategory.MECHANICAL,
            use_case='Creating equipment lists, schedules, and specifications for mechanical systems',
            recommended_domain='mechanical',
            recommended_reasoning='medium',
            questions=[
                AnalysisQuestion(
                    question="List all HVAC equipment (AHUs, fans, exhaust units) with model numbers and capacities",
                    purpose="Catalog HVAC equipment",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Show all pumps with their flow rates (GPM), head (feet), and motor horsepower",
                    purpose="Create pump schedule",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="List all motors with their horsepower, voltage, and service factor",
                    purpose="Document motor specifications",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What piping systems are shown and what are their design pressures and temperatures?",
                    purpose="Identify piping system parameters",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Create a bar chart showing equipment power consumption by type",
                    purpose="Visualize energy distribution",
                    expected_format="chart",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Calculate the total cooling capacity in tons and heating capacity in BTU/hr",
                    purpose="Sum system capacities",
                    expected_format="text",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Export complete equipment schedule to Excel with all specifications",
                    purpose="Generate equipment list",
                    expected_format="export",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What equipment requires special maintenance access or clearances?",
                    purpose="Identify maintenance requirements",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=3
                ),
            ],
            output_formats=['Equipment Schedule Excel', 'Power Summary', 'Capacity Analysis'],
            quality_checks=[
                'All equipment properly tagged',
                'Specifications complete',
                'Adequate capacity for load',
                'Motor voltages match available power',
                'Proper redundancy for critical equipment',
            ],
            estimated_time_minutes=10,
            tags=['mechanical', 'equipment-schedule', 'hvac', 'pumps', 'bom']
        )
        
        # 5. Quick Compliance Check Template
        self.templates['compliance_check'] = AnalysisTemplate(
            template_id='compliance_check',
            name='Quick Compliance Check',
            description='Fast review of drawing compliance with standards and code requirements',
            category=TemplateCategory.COMPLIANCE,
            use_case='Verifying drawings meet applicable codes, standards, and best practices',
            recommended_domain='general',
            recommended_reasoning='medium',
            questions=[
                AnalysisQuestion(
                    question="What engineering standards and codes are referenced in the title block or notes?",
                    purpose="Identify applicable standards",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Is the drawing title block complete with project name, sheet number, revision, date, and approvals?",
                    purpose="Verify title block completeness",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Are all symbols and abbreviations consistent with referenced standards (IEEE, ANSI, ISO, etc.)?",
                    purpose="Check symbol compliance",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What general notes or specifications are provided, and are they complete?",
                    purpose="Review specification notes",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Are all components properly labeled with tag numbers or equipment IDs?",
                    purpose="Verify labeling consistency",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="What quality or ambiguity issues exist in the drawing clarity or completeness?",
                    purpose="Identify quality concerns",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Are there any missing details, callouts, or references to other sheets?",
                    purpose="Check for completeness",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Does the drawing meet the requirements for construction/fabrication release?",
                    purpose="Assess release readiness",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
            ],
            output_formats=['Compliance Report', 'Checklist'],
            quality_checks=[
                'Title block fully populated',
                'Symbols per referenced standards',
                'All equipment tagged',
                'Notes clear and complete',
                'Revisions properly tracked',
            ],
            estimated_time_minutes=8,
            tags=['compliance', 'standards', 'quality-check', 'title-block']
        )
        
        # 6. Bill of Materials Generation Template
        self.templates['bom_generation'] = AnalysisTemplate(
            template_id='bom_generation',
            name='Bill of Materials (BOM) Generation',
            description='Extract and organize all components into a structured BOM',
            category=TemplateCategory.GENERAL,
            use_case='Creating procurement-ready bill of materials from any diagram type',
            recommended_domain='general',
            recommended_reasoning='medium',
            questions=[
                AnalysisQuestion(
                    question="List all major equipment and components with their tag numbers and descriptions",
                    purpose="Identify all line items",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Show all components grouped by type (transformers, breakers, motors, valves, etc.)",
                    purpose="Organize by category",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="For each component, list the key specifications (voltage, capacity, size, material, rating)",
                    purpose="Extract specifications",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Calculate the total count of each component type",
                    purpose="Quantify materials",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What manufacturer part numbers or model numbers are specified?",
                    purpose="Identify specific products",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Create a pie chart showing component distribution by type",
                    purpose="Visualize BOM composition",
                    expected_format="chart",
                    requires_code_agent=True,
                    priority=3
                ),
                AnalysisQuestion(
                    question="Export complete BOM to Excel with item numbers, descriptions, quantities, and specifications",
                    purpose="Generate procurement BOM",
                    expected_format="export",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Are there any unspecified or ambiguous components that need clarification?",
                    purpose="Identify missing data",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
            ],
            output_formats=['Excel BOM', 'CSV Export', 'Procurement Report'],
            quality_checks=[
                'All components counted',
                'Specifications complete',
                'No duplicate entries',
                'Quantities verified',
                'Part numbers where applicable',
            ],
            estimated_time_minutes=10,
            tags=['bom', 'materials', 'procurement', 'quantity-takeoff']
        )
        
        # 7. Structural Design Review Template
        self.templates['structural_design_review'] = AnalysisTemplate(
            template_id='structural_design_review',
            name='Structural Design Review',
            description='Review structural drawings for member sizes, connections, and load paths',
            category=TemplateCategory.STRUCTURAL,
            use_case='Analyzing structural framing, foundations, and connections',
            recommended_domain='structural',
            recommended_reasoning='high',
            questions=[
                AnalysisQuestion(
                    question="What structural system type is used (steel frame, concrete, timber, composite)?",
                    purpose="Identify structural system",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="List all structural member sizes (beams, columns, joists) with their designations",
                    purpose="Create member schedule",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What are the design loads specified (dead load, live load, wind, seismic)?",
                    purpose="Document load criteria",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Describe the foundation system including footing sizes and depths",
                    purpose="Review foundation design",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="What connection types are specified and are details provided?",
                    purpose="Assess connection design",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
                AnalysisQuestion(
                    question="Create a table of columns with their size, height, and base condition",
                    purpose="Generate column schedule",
                    expected_format="table",
                    requires_code_agent=True,
                    priority=2
                ),
                AnalysisQuestion(
                    question="What structural materials and grades are specified (steel grade, concrete strength)?",
                    purpose="Document material specs",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=1
                ),
                AnalysisQuestion(
                    question="Are there any unusual loading conditions or special structural considerations?",
                    purpose="Identify design challenges",
                    expected_format="text",
                    requires_code_agent=False,
                    priority=2
                ),
            ],
            output_formats=['Structural Summary', 'Member Schedule', 'Load Analysis'],
            quality_checks=[
                'Load paths clearly defined',
                'Member sizes appear adequate',
                'Connections properly detailed',
                'Foundation design appropriate',
                'Compliance with building code',
            ],
            estimated_time_minutes=15,
            tags=['structural', 'steel', 'concrete', 'foundations', 'loads']
        )
    
    def get_template(self, template_id: str) -> Optional[AnalysisTemplate]:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[TemplateCategory] = None) -> List[AnalysisTemplate]:
        """List all templates, optionally filtered by category"""
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates
    
    def search_templates(self, keywords: List[str]) -> List[AnalysisTemplate]:
        """Search templates by keywords"""
        results = []
        for template in self.templates.values():
            # Search in name, description, use_case, and tags
            searchable_text = ' '.join([
                template.name.lower(),
                template.description.lower(),
                template.use_case.lower(),
                ' '.join(template.tags)
            ])
            
            if any(keyword.lower() in searchable_text for keyword in keywords):
                results.append(template)
        
        return results
    
    def get_template_summary(self, template: AnalysisTemplate) -> str:
        """Get a formatted summary of a template"""
        return f"""
### {template.name}

**Category:** {template.category.value.title()}  
**Domain:** {template.recommended_domain} | **Reasoning:** {template.recommended_reasoning}  
**Estimated Time:** {template.estimated_time_minutes} minutes

**Description:** {template.description}

**Use Case:** {template.use_case}

**Questions:** {len(template.questions)} ({len([q for q in template.questions if q.priority == 1])} critical)  
**Outputs:** {', '.join(template.output_formats)}

**Tags:** {', '.join(template.tags)}
"""
    
    def export_template(self, template_id: str, filepath: str):
        """Export a template to JSON file"""
        template = self.get_template(template_id)
        if template:
            with open(filepath, 'w') as f:
                json.dump(asdict(template), f, indent=2, default=str)
    
    def import_template(self, filepath: str) -> Optional[AnalysisTemplate]:
        """Import a template from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Reconstruct the template (simplified - would need proper deserialization)
                return data
        except Exception as e:
            print(f"Error importing template: {e}")
            return None


# Singleton instance
_template_library = None


def get_template_library() -> TemplateLibrary:
    """Get the global template library instance"""
    global _template_library
    if _template_library is None:
        _template_library = TemplateLibrary()
    return _template_library


if __name__ == "__main__":
    # Demo usage
    library = get_template_library()
    
    print("=" * 70)
    print("EDISON PRO ANALYSIS TEMPLATES")
    print("=" * 70)
    
    # List all templates
    print("\n📚 Available Templates:\n")
    for template in library.list_templates():
        print(f"• {template.name} ({template.category.value})")
        print(f"  {template.description}")
        print(f"  Questions: {len(template.questions)} | Time: {template.estimated_time_minutes} min")
        print()
    
    # Show detailed view of one template
    print("\n" + "=" * 70)
    print("DETAILED TEMPLATE EXAMPLE")
    print("=" * 70)
    
    template = library.get_template('electrical_load_study')
    if template:
        print(library.get_template_summary(template))
        print("\n**Analysis Questions:**\n")
        for i, q in enumerate(template.questions, 1):
            agent = "🤖 Code Agent" if q.requires_code_agent else "🧠 o3-pro"
            priority = "⭐" * q.priority
            print(f"{i}. {priority} [{agent}] {q.question}")
            print(f"   Purpose: {q.purpose}")
            print(f"   Format: {q.expected_format}")
            print()
