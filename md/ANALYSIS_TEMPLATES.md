# Analysis Templates Feature

**Author:** Srikanth Bhakthan - Microsoft  
**Date:** October 11, 2025  
**Feature:** Predefined Analysis Templates for Common Engineering Scenarios

## Overview

EDISON PRO now includes **Analysis Templates** - predefined workflows for common engineering diagram analysis scenarios. Templates provide structured question sequences, recommended settings, and quality checklists to ensure comprehensive and consistent analysis.

## Benefits

### 🎯 **Standardization**
- Consistent analysis methodology across projects
- Best practices built into workflows
- Repeatable results for similar diagram types

### ⚡ **Efficiency**
- Pre-configured question sequences save time
- No need to think about what to ask
- Guided workflow from start to finish

### ✅ **Completeness**
- Comprehensive coverage of critical aspects
- Built-in quality checklists
- Nothing important gets missed

### 📊 **Professional Outputs**
- Structured deliverables (tables, charts, exports)
- Ready for reporting and documentation
- Meets industry standards

## Available Templates

### 1. ⚡ Electrical Load Study
**Time:** ~15 minutes | **Domain:** electrical | **Reasoning:** high

Complete electrical load analysis with power calculations and distribution assessment.

**Questions (8):**
- System voltage and frequency identification
- Transformer schedule with ratings
- Circuit breaker inventory with settings
- Total connected load calculation
- Load distribution visualization (chart)
- Demand and diversity factor analysis
- Equipment data export (CSV)
- Overload condition assessment

**Outputs:** PDF Report, Excel Tables, CSV Export, Interactive Charts

**Quality Checks:**
- All transformers properly rated for load
- Circuit breakers sized correctly
- Voltage drop within acceptable limits
- Adequate spare capacity (20%+ recommended)
- Proper grounding and bonding shown

---

### 2. 🛡️ P&ID Safety System Review
**Time:** ~20 minutes | **Domain:** pid | **Reasoning:** high

Comprehensive safety system analysis for process diagrams.

**Questions (8):**
- Safety instrumented systems (SIS) identification
- Pressure relief device inventory
- Emergency shutdown (ESD) sequence documentation
- High-high and low-low alarm schedule
- Interlock condition mapping
- Fire protection system integration
- Safety instrument schedule
- Single point of failure analysis

**Outputs:** Safety Report PDF, Excel Safety Matrix, Interlock Schedule

**Quality Checks:**
- All relief devices properly sized and located
- Redundancy for critical safety functions
- ESD logic clearly documented
- Alarms have appropriate setpoints
- Compliance with IEC 61511 or ISA 84

---

### 3. 🏗️ Civil Site Plan Analysis
**Time:** ~12 minutes | **Domain:** civil | **Reasoning:** medium

Site layout analysis including grading, drainage, and utilities.

**Questions (8):**
- Existing and proposed grade identification
- Drainage system mapping
- Underground utility coordination
- Pavement specifications
- Site area calculations
- Access and circulation assessment
- Utility conflict identification
- Site data export

**Outputs:** Site Analysis Report, Utility Schedule, Grading Summary

**Quality Checks:**
- Adequate drainage slope (min 2%)
- Utility clearances maintained
- ADA-compliant slopes and access
- Proper erosion control provisions
- Fire access lanes adequate

---

### 4. ⚙️ Mechanical Equipment Schedule
**Time:** ~10 minutes | **Domain:** mechanical | **Reasoning:** medium

Generate comprehensive equipment schedules for mechanical systems.

**Questions (8):**
- HVAC equipment catalog
- Pump schedule with specifications
- Motor inventory
- Piping system parameters
- Equipment power distribution (chart)
- System capacity calculations
- Equipment schedule export (Excel)
- Maintenance access requirements

**Outputs:** Equipment Schedule Excel, Power Summary, Capacity Analysis

**Quality Checks:**
- All equipment properly tagged
- Specifications complete
- Adequate capacity for load
- Motor voltages match available power
- Proper redundancy for critical equipment

---

### 5. ✅ Quick Compliance Check
**Time:** ~8 minutes | **Domain:** general | **Reasoning:** medium

Fast review of drawing compliance with standards and code requirements.

**Questions (8):**
- Referenced standards identification
- Title block completeness check
- Symbol and abbreviation compliance
- General notes review
- Component labeling verification
- Quality and ambiguity assessment
- Completeness check (missing details)
- Construction release readiness

**Outputs:** Compliance Report, Checklist

**Quality Checks:**
- Title block fully populated
- Symbols per referenced standards
- All equipment tagged
- Notes clear and complete
- Revisions properly tracked

---

### 6. 📋 Bill of Materials (BOM) Generation
**Time:** ~10 minutes | **Domain:** general | **Reasoning:** medium

Extract and organize all components into a structured BOM.

**Questions (8):**
- Major equipment identification
- Component grouping by type
- Specification extraction
- Component count calculation
- Manufacturer part number identification
- Component distribution visualization (pie chart)
- Complete BOM export (Excel)
- Unspecified component identification

**Outputs:** Excel BOM, CSV Export, Procurement Report

**Quality Checks:**
- All components counted
- Specifications complete
- No duplicate entries
- Quantities verified
- Part numbers where applicable

---

### 7. 🏢 Structural Design Review
**Time:** ~15 minutes | **Domain:** structural | **Reasoning:** high

Review structural drawings for member sizes, connections, and load paths.

**Questions (8):**
- Structural system type identification
- Member size schedule
- Design load documentation
- Foundation system review
- Connection type assessment
- Column schedule generation
- Material and grade specification
- Special loading condition identification

**Outputs:** Structural Summary, Member Schedule, Load Analysis

**Quality Checks:**
- Load paths clearly defined
- Member sizes appear adequate
- Connections properly detailed
- Foundation design appropriate
- Compliance with building code

---

## Using Templates in the UI

### Step 1: Navigate to Templates Tab
Click on the **📋 Analysis Templates** tab in the EDISON PRO UI.

### Step 2: Browse Templates
- Use the category filter to narrow down options:
  - All, Electrical, Mechanical, PID, Civil, Structural, Safety, Compliance, General
- Review template descriptions, estimated times, and output formats

### Step 3: Select and Load Template
1. Choose a template from the dropdown (e.g., "Electrical Load Study")
2. Review the detailed template information
3. Click **✅ Load This Template**

### Step 4: Start Guided Analysis
1. Click **▶️ Start Template Analysis**
2. Read the first question and its purpose
3. Options:
   - Click **✅ Answer Question** to use the template question as-is
   - OR type a custom variation in the text box
4. Review the answer, tables, charts, and downloads

### Step 5: Progress Through Questions
- Continue answering questions in sequence
- Skip optional questions (priority 3) if desired
- Monitor progress: "Question 3/8"

### Step 6: Complete and Review
- Template completion summary shows:
  - Questions answered
  - Outputs generated (tables, downloads, charts)
  - Quality checklist for manual verification
  - Recommended deliverables

### Step 7: Reset or Export
- Click **🔄 Reset Progress** to start over
- Export generated files from download links
- Create final report from analysis results

---

## Using Templates Programmatically

### Load Template Library

```python
from analysis_templates import get_template_library, TemplateCategory

# Get the singleton instance
library = get_template_library()

# List all templates
all_templates = library.list_templates()

# Filter by category
electrical_templates = library.list_templates(category=TemplateCategory.ELECTRICAL)

# Search by keywords
load_templates = library.search_templates(['load', 'power', 'electrical'])
```

### Get Template Details

```python
# Get specific template
template = library.get_template('electrical_load_study')

print(f"Name: {template.name}")
print(f"Domain: {template.recommended_domain}")
print(f"Reasoning: {template.recommended_reasoning}")
print(f"Questions: {len(template.questions)}")

# Iterate through questions
for i, question in enumerate(template.questions, 1):
    print(f"{i}. {question.question}")
    print(f"   Purpose: {question.purpose}")
    print(f"   Agent: {'Code Agent' if question.requires_code_agent else 'o3-pro'}")
    print(f"   Priority: {question.priority}")
```

### Execute Template Analysis

```python
from edisonpro_ui import EdisonProUI
import asyncio

# Initialize UI
ui = EdisonProUI()
ui.initialize()

# Load template
ui.current_template = library.get_template('electrical_load_study')
ui.template_progress = []

# Get first question
q_text, q_purpose, idx, total = ui.get_next_template_question()
print(f"Question {idx}/{total}: {q_text}")

# Process question
async def run_template():
    history = []
    answer, table, download, chart, next_q = await ui.process_template_question_async(
        "AUTO",  # Use template question
        history
    )
    print(f"Answer: {answer}")
    return answer

# Run
answer = asyncio.run(run_template())
```

---

## Template Structure

Each template includes:

### Metadata
- **template_id**: Unique identifier
- **name**: Display name
- **description**: Brief description
- **category**: TemplateCategory enum
- **use_case**: When to use this template
- **recommended_domain**: Best domain setting
- **recommended_reasoning**: Suggested reasoning effort
- **estimated_time_minutes**: Expected completion time
- **tags**: Keywords for searching

### Questions
Each question has:
- **question**: Text of the question
- **purpose**: Why this question is asked
- **expected_format**: Output type (text, table, chart, export)
- **requires_code_agent**: Boolean flag
- **priority**: 1=critical, 2=important, 3=optional

### Quality Checks
List of items to verify after analysis completion.

### Output Formats
List of recommended deliverable formats.

---

## Creating Custom Templates

### Option 1: Modify Existing Template

```python
from analysis_templates import AnalysisTemplate, AnalysisQuestion, TemplateCategory

# Get template library
library = get_template_library()

# Copy existing template
base_template = library.get_template('electrical_load_study')

# Modify for your needs
custom_template = AnalysisTemplate(
    template_id='custom_electrical_study',
    name='Custom Electrical Study',
    description='Modified electrical analysis for specific project',
    category=TemplateCategory.ELECTRICAL,
    use_case='Project XYZ electrical review',
    recommended_domain='electrical',
    recommended_reasoning='high',
    questions=[
        # Add your custom questions
        AnalysisQuestion(
            question="What is the main service voltage?",
            purpose="Document service characteristics",
            expected_format="text",
            requires_code_agent=False,
            priority=1
        ),
        # ... more questions
    ],
    output_formats=['Custom Report', 'Excel'],
    quality_checks=['Custom check 1', 'Custom check 2'],
    estimated_time_minutes=20,
    tags=['custom', 'electrical', 'project-xyz']
)

# Add to library
library.templates['custom_electrical_study'] = custom_template
```

### Option 2: Load from JSON

```python
import json

# Export template to JSON
library.export_template('electrical_load_study', 'my_template.json')

# Modify JSON file as needed

# Import modified template
custom_template = library.import_template('my_template.json')
```

---

## Best Practices

### When to Use Templates

✅ **Use templates when:**
- Analyzing standard engineering diagrams (electrical, P&ID, civil, etc.)
- Need comprehensive coverage of typical questions
- Want consistent results across multiple similar projects
- Training new team members on analysis methodology
- Creating deliverables for clients or stakeholders

❌ **Don't use templates when:**
- Diagram is highly unique or specialized
- Only need specific information (use direct Q&A instead)
- Template doesn't match your domain well

### Customizing Template Execution

**Modify Questions:**
- Type custom variations of template questions
- Add follow-up questions as needed
- Skip optional (priority 3) questions

**Adjust Settings:**
- Before starting template, ensure document is analyzed with recommended domain
- If template suggests `reasoning: high`, use that setting during analysis

**Combine with Direct Q&A:**
- Use templates for structured analysis
- Switch to Q&A tab for ad-hoc questions
- Return to template to complete workflow

### Quality Verification

After template completion:
1. ✅ Review quality checklist items
2. ✅ Verify all critical questions answered
3. ✅ Check data output quality (tables, charts)
4. ✅ Export and organize deliverables
5. ✅ Document any deviations or special findings

---

## Template Categories

| Category | Focus | Example Templates |
|----------|-------|-------------------|
| **Electrical** | Power systems, distribution, loads | Load Study, Protection Coordination |
| **Mechanical** | HVAC, equipment, piping | Equipment Schedule, System Analysis |
| **PID** | Process systems, instrumentation | Safety Review, Instrument Schedule |
| **Civil** | Site work, grading, utilities | Site Plan Analysis, Drainage Study |
| **Structural** | Framing, foundations, loads | Design Review, Member Schedule |
| **Safety** | Safety systems, interlocks | Safety System Review, Hazard Analysis |
| **Compliance** | Standards, codes, regulations | Compliance Check, Standards Review |
| **General** | Multi-discipline | BOM Generation, Cross-Reference Review |

---

## Performance Considerations

### Estimated Times
Template times are based on:
- Document already analyzed and indexed
- Average complexity diagrams
- Using recommended reasoning effort
- All questions answered (not skipped)

**Actual times may vary based on:**
- Diagram complexity
- Azure OpenAI response times
- Network latency
- Code Agent execution time (for data transformation)

### Cost Optimization

Templates automatically route questions optimally:
- 🧠 **o3-pro** for understanding questions (~$0.001 per query)
- 🤖 **Code Agent** for data transformation (~$0.01-0.02 per query)

**Typical template cost:**
- Electrical Load Study: ~$0.05 (5 Code Agent + 3 o3-pro questions)
- Compliance Check: ~$0.008 (all o3-pro questions)
- BOM Generation: ~$0.06 (6 Code Agent + 2 o3-pro questions)

---

## Troubleshooting

### Template Not Loading
**Issue:** "Templates not available" message  
**Solution:** Ensure `analysis_templates.py` is in the project directory

### Question Not Processing
**Issue:** Template question gets stuck or errors  
**Solution:** 
1. Check Azure OpenAI connectivity
2. Verify Code Agent configuration (if question requires it)
3. Try custom question variation

### Missing Outputs
**Issue:** Expected table/chart not generated  
**Solution:**
1. Verify Code Agent is properly configured
2. Check question detection (should show "🤖 Code Agent" indicator)
3. Review answer for error messages

### Template Progress Lost
**Issue:** Progress reset unexpectedly  
**Solution:** Template progress is session-based. Restarting UI will reset progress.

---

## Future Enhancements

Planned features for templates:
- [ ] Save/load template execution history
- [ ] Export template results as PDF report
- [ ] Share custom templates between users
- [ ] Template marketplace or community library
- [ ] Industry-specific template packs
- [ ] Multi-document templates (compare drawings)
- [ ] Automated template recommendations based on diagram type

---

## Conclusion

Analysis Templates bring structure, consistency, and efficiency to engineering diagram analysis. By codifying best practices into reusable workflows, templates ensure comprehensive coverage while reducing the mental overhead of figuring out what questions to ask.

**Get Started:**
1. Open EDISON PRO UI
2. Navigate to **📋 Analysis Templates** tab
3. Browse available templates
4. Load a template matching your diagram type
5. Follow the guided workflow to completion

For questions or suggestions about templates, contact the EDISON PRO team!
