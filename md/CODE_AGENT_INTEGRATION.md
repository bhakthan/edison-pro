# Code Agent Integration for EDISON PRO

## 🎯 Overview

EDISON PRO now integrates **Azure AI Agents with GPT-4.1 and Code Interpreter** to transform extracted engineering diagram data into actionable formats: tables, charts, calculations, and downloadable files.

## 🚀 Key Capabilities

### What the Code Agent Can Do

1. **📊 Tabular Data Extraction**
   - "Show me all transformers as a table"
   - "List all components with their specifications"
   - "Create a table of all electrical equipment"

2. **📥 Data Export**
   - "Download the component list as CSV"
   - "Export to Excel with formulas"
   - "Save as JSON for further processing"

3. **📈 Data Analysis & Calculations**
   - "What's the total power load?"
   - "Calculate average voltage ratings"
   - "How many motors are rated above 50HP?"

4. **📉 Visualizations**
   - "Plot voltage distribution across components"
   - "Create a bar chart of component types"
   - "Show power ratings as a histogram"

5. **🔧 Bill of Materials Generation**
   - "Generate a BOM with quantities"
   - "Create parts list with specifications"
   - "Export equipment schedule"

6. **🔍 Filtering & Sorting**
   - "Show only high-voltage equipment"
   - "List components by criticality"
   - "Filter transformers above 1000kVA"

## 🏗️ Architecture

### Hybrid Agent System

```
User Question
    ↓
Question Classifier
    ↓
    ├─→ [Data Transformation?] → Code Agent (GPT-4.1 + Code Interpreter)
    │                              ↓
    │                          • Parse JSON data
    │                          • Execute Python code
    │                          • Generate tables/charts
    │                          • Create files
    │                              ↓
    │                          Formatted Response + Downloads
    │
    └─→ [Understanding?] → o3-pro (Reasoning + Evidence)
                              ↓
                          Text Answer + Citations
```

### When Each Agent is Used

| Question Type | Agent | Reason |
|--------------|-------|--------|
| "What is the voltage of T-101?" | o3-pro | Understanding question, requires reasoning |
| "Show all transformers as a table" | Code Agent | Data transformation |
| "Explain the control philosophy" | o3-pro | Requires deep reasoning about system |
| "Calculate total power load" | Code Agent | Requires computation |
| "Why is breaker B-202 important?" | o3-pro | Requires engineering judgment |
| "Export components to CSV" | Code Agent | File generation |

## 💻 Implementation

### 1. Code Agent Handler (`code_agent_handler.py`)

**Core Class:** `CodeAgentHandler`

**Key Methods:**
- `should_use_code_agent(question)` - Detects if question requires code execution
- `process_data_query(question, context_data)` - Executes query with code interpreter
- `download_file(file_id, output_path)` - Downloads generated files

**Detection Logic:**
```python
# Keywords that trigger code agent
DATA_TRANSFORMATION_KEYWORDS = {
    'table', 'csv', 'excel', 'chart', 'plot', 
    'calculate', 'sum', 'average', 'filter', 'sort',
    'export', 'download', 'bom', 'list all'
}

# Patterns that suggest data transformation
patterns = [
    r'show .* as (a )?table',
    r'create (a )?(table|chart)',
    r'calculate .* load',
    r'how many .*'
]
```

### 2. UI Integration (`edisonpro_ui.py`)

**Hybrid Query Function:**
```python
async def ask_question_hybrid(question, ...):
    # Step 1: Classify question
    if code_agent.should_use_code_agent(question):
        # Step 2: Get structured data
        context = get_interpretations_and_metadata()
        
        # Step 3: Use code agent
        result = code_agent.process_data_query(question, context)
        
        # Step 4: Format response with downloads
        return format_code_agent_response(result)
    else:
        # Use o3-pro for understanding (existing flow)
        return await ask_question_pro(question, ...)
```

**UI Components:**
- **Download Buttons**: Appear when files are generated
- **Inline Tables**: Display dataframes directly in UI
- **Chart Images**: Show visualizations inline
- **Follow-up Suggestions**: "Download as CSV", "Create chart", etc.

### 3. Data Pipeline

**Context Data Structure:**
```json
{
  "interpretations": [
    {
      "component_id": "T-101",
      "type": "transformer",
      "specifications": {
        "voltage_primary": "13.8kV",
        "voltage_secondary": "480V",
        "capacity": "1000kVA"
      },
      "page": 1,
      "confidence": 0.92
    }
  ],
  "visual_elements": [...],
  "metadata": {
    "document_name": "electrical_schematic.pdf",
    "total_pages": 12,
    "analysis_date": "2025-01-15"
  }
}
```

**Code Agent receives:**
- Structured JSON data (interpretations, visual elements)
- User question
- Conversation history (for follow-ups)

**Code Agent returns:**
```python
{
  'answer': 'Generated 15 rows showing all transformers...',
  'code_executed': True,
  'tables': [
    {'type': 'dataframe', 'content': <pandas.DataFrame>}
  ],
  'files': ['transformers_list.csv', 'bom.xlsx'],
  'charts': ['voltage_distribution.png'],
  'error': None
}
```

## 📋 Example Use Cases

### Use Case 1: Generate Component Table

**User:** "Show me all transformers as a table"

**Code Agent Response:**
```
| ID    | Type        | Primary | Secondary | Capacity | Page |
|-------|-------------|---------|-----------|----------|------|
| T-101 | Transformer | 13.8kV  | 480V      | 1000kVA  | 1    |
| T-102 | Transformer | 480V    | 120V      | 50kVA    | 2    |
| T-201 | Transformer | 13.8kV  | 4160V     | 2500kVA  | 5    |

Generated 3 rows. Would you like to download as CSV?
```

### Use Case 2: Calculate Total Load

**User:** "What's the total power load from all motors?"

**Code Agent Response:**
```python
# Code executed:
import pandas as pd
data = {...}  # From context
motors = [c for c in data if c['type'] == 'motor']
total_hp = sum(float(m['specs']['power'].replace('HP','')) for m in motors)
print(f"Total: {total_hp} HP")
```

**Answer:**
```
Total motor load: 850 HP (634 kW)

Breakdown:
- MOT-101: 50 HP
- MOT-102: 100 HP
- MOT-201: 200 HP
- MOT-202: 500 HP

Would you like a detailed breakdown table or chart?
```

### Use Case 3: Export to CSV

**User:** "Download the component list as CSV"

**Code Agent Response:**
```
Created file: engineering_components_2025-01-15.csv

Contains 47 components with the following columns:
- Component ID
- Type
- Specifications
- Page Number
- Confidence Score

[Download CSV] button appears in UI
```

### Use Case 4: Create Visualization

**User:** "Plot the voltage distribution"

**Code Agent Response:**
```python
import matplotlib.pyplot as plt
voltages = [extract voltages from data]
plt.hist(voltages, bins=10)
plt.xlabel('Voltage (kV)')
plt.ylabel('Component Count')
plt.title('Voltage Distribution in Electrical System')
plt.savefig('voltage_dist.png')
```

**UI displays chart inline with download option**

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Azure AI Agent Configuration (GPT-4.1 with Code Interpreter)
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
AZURE_OPENAI_AGENT_ID=asst_Hn66VpWA6euz7IsV5GFnOa4P
AZURE_OPENAI_AGENT_API_KEY=your-api-key
```

### Setup Steps

1. **Create Azure AI Agent** (already created with ID: `asst_Hn66VpWA6euz7IsV5GFnOa4P`)
   - Model: GPT-4.1
   - Tools: Code Interpreter enabled
   - Name: "EDISON Code Agent"

2. **Configure Environment**
   - Add agent credentials to `.env`
   - Install required packages: `azure-ai-projects`, `azure-identity`

3. **Test Integration**
   ```python
   from code_agent_handler import get_code_agent
   
   agent = get_code_agent()
   if agent.available:
       print("✅ Code Agent ready!")
   ```

## 💰 Cost & Performance

### Cost Comparison

| Task | Agent | Cost per Query | Typical Time |
|------|-------|---------------|--------------|
| "What is voltage of T-101?" | o3-pro LOW | ~$0.001 | 15-30s |
| "Show all transformers as table" | Code Agent | ~$0.01-0.02 | 10-20s |
| "Export to CSV" | Code Agent | ~$0.01-0.02 | 10-20s |
| "Calculate total load" | Code Agent | ~$0.01 | 10-15s |

**Strategy:** Use Code Agent selectively for data transformation only. o3-pro remains primary for understanding engineering systems.

### Performance Characteristics

**Code Agent Advantages:**
- ✅ Excellent at data manipulation
- ✅ Generates formatted tables automatically
- ✅ Creates downloadable files
- ✅ Performs calculations accurately
- ✅ ~10-20 second response time

**o3-pro Advantages:**
- ✅ Deep engineering reasoning
- ✅ System-level understanding
- ✅ Evidence-based answers
- ✅ Higher confidence scoring
- ✅ Better for "why" questions

## 🔒 Security Considerations

### Sandboxed Execution
- Code runs in Azure's secure sandbox
- No access to filesystem outside sandbox
- No network access
- Automatic cleanup after execution

### Data Privacy
- Context data sent to agent is diagram analysis output only
- No raw PDFs or images sent
- All processing in Azure cloud
- Credentials managed via Azure Identity

### Error Handling
- Graceful fallback if code execution fails
- Detailed error messages for debugging
- Automatic retry on transient failures
- Timeout protection (60 second max)

## 📊 Metrics & Monitoring

### Track Usage
- Code agent invocations per session
- Success/failure rate
- Average execution time
- File generation frequency

### Quality Metrics
- User satisfaction (implicit: follow-up questions)
- Export usage (downloads per session)
- Error rate by question type

## 🎯 Future Enhancements

### Phase 2: Advanced Features
1. **Multi-step Analysis**
   - Agent chains multiple code executions
   - "First show table, then calculate average, then plot"

2. **Interactive Charts**
   - Plotly for interactive visualizations
   - Zoom, pan, hover tooltips

3. **Advanced Exports**
   - Excel with formulas and formatting
   - PDF reports with charts
   - PowerPoint slides

4. **Persistent Data Store**
   - Cache intermediate results
   - Enable complex multi-turn analysis

### Phase 3: Specialized Agents
1. **BOM Generation Agent**
   - Specialized for bill of materials
   - Vendor lookup, pricing

2. **Compliance Checker Agent**
   - Verify against standards (ANSI, ISO)
   - Generate compliance reports

3. **Cost Estimation Agent**
   - Calculate project costs
   - Material takeoff

## 📚 Documentation

### For Users

**Quick Start:**
1. Ask natural language questions with keywords: "table", "calculate", "export"
2. Download generated files via UI buttons
3. Ask follow-up questions: "Now plot this as a chart"

**Sample Questions:**
- "Show me all transformers as a table"
- "Calculate the total power load"
- "Export components to CSV"
- "Plot voltage distribution"
- "Create a BOM with quantities"

### For Developers

**Adding New Capabilities:**
1. Update `DATA_TRANSFORMATION_KEYWORDS` in `code_agent_handler.py`
2. Add new response formatters in UI code
3. Test with sample engineering data

**Debugging:**
- Check logs: `logger.info()` statements throughout
- Inspect `result['raw_messages']` for agent output
- Test detection: `should_use_code_agent(question)`

## ✅ Testing Checklist

- [ ] Code agent initialization (with/without credentials)
- [ ] Question detection (transformation vs understanding)
- [ ] Table generation from component data
- [ ] CSV export with proper formatting
- [ ] Calculation accuracy (totals, averages)
- [ ] Chart generation and display
- [ ] Error handling (code failures, timeout)
- [ ] Follow-up questions in same thread
- [ ] File download functionality
- [ ] UI integration (buttons, inline display)
- [ ] Cost tracking and logging
- [ ] Security (no unsafe code execution)

## 🎉 Benefits Summary

### For Engineering Teams
- 📊 **Instant Tables**: No manual data entry
- 📥 **Quick Exports**: CSV/Excel for further analysis
- 📈 **Visual Insights**: Charts and graphs automatically
- 🔢 **Accurate Calculations**: No manual math errors
- 🔄 **Iterative Analysis**: Follow-up questions build on previous

### For EDISON PRO
- 🚀 **Enhanced Capabilities**: Beyond text Q&A
- 💡 **Better UX**: Visual data > text descriptions
- 🎯 **Practical Value**: Actionable outputs, not just information
- 🔧 **Extensible**: Easy to add new transformations
- 💰 **Cost-Effective**: Right tool for right job

---

**Status:** Implementation ready for Phase 1 (basic table generation, CSV export, calculations)

**Next Steps:**
1. Test with sample engineering diagram data
2. Refine detection keywords based on user feedback
3. Add more export formats (Excel, JSON)
4. Implement chart generation
5. Deploy to production with monitoring
