# Code Agent Detailed Instruction Prompt

## Overview

The Code Agent uses GPT-5.4 with Code Interpreter to transform engineering diagram data into tables, charts, calculations, and exports. For explicitly agentic requests, EDISON can fall through to the Copilot-backed dynamic meta-agent runtime.

---

## Complete Prompt Structure

When you ask a data transformation question like **"Create a line chart of voltage levels"**, the system sends this structured prompt to the Code Agent:

### 1. Context Introduction

```
You are analyzing engineering diagram data. The following structured data has been extracted:

**Available Data:**
```

### 2. Component Interpretations (JSON Format)

```json
**Component Interpretations (JSON format):**
```json
[
  {
    "component_id": "T-101",
    "type": "transformer",
    "function": "Step-down transformer for building distribution",
    "specifications": {
      "voltage_primary": "13.8kV",
      "voltage_secondary": "480V",
      "capacity": "1000kVA",
      "phases": 3,
      "connection": "delta-wye"
    },
    "location": "Zone A3, Page 1",
    "criticality": "high",
    "subsystem": "power_distribution"
  },
  {
    "component_id": "CB-201",
    "type": "circuit_breaker",
    "function": "Main distribution protection",
    "specifications": {
      "voltage": "480V",
      "amperage": "800A",
      "interrupting_capacity": "65kA",
      "type": "molded_case"
    },
    "location": "Zone B2, Page 1",
    "criticality": "high",
    "subsystem": "power_distribution"
  },
  {
    "component_id": "M-301",
    "type": "motor",
    "function": "Centrifugal pump drive",
    "specifications": {
      "voltage": "480V",
      "power": "50HP",
      "rpm": "1750",
      "type": "3-phase induction"
    },
    "location": "Zone C1, Page 2",
    "criticality": "medium",
    "subsystem": "pumping_system"
  }
  // ... up to 50 components
]
... (X more components)
```
```

**Note:** The system includes up to 50 components to avoid token overflow. If there are more, it shows a count: `... (125 more components)`.

### 3. Visual Elements Summary

```
**Visual Elements Summary:**
Total elements: 156

Sample:
[
  {
    "type": "symbol",
    "symbol_type": "transformer",
    "id": "T-101",
    "location": {"page": 1, "zone": "A3"},
    "properties": {"orientation": "horizontal"}
  },
  {
    "type": "line",
    "line_type": "power",
    "connects": ["T-101", "CB-201"],
    "properties": {"voltage": "480V", "phases": 3}
  },
  {
    "type": "annotation",
    "text": "Main Distribution",
    "location": {"page": 1, "zone": "B2"}
  }
  // ... 5 samples shown
]
```

### 4. Metadata

```
**Metadata:**
{
  "total_pages": 12,
  "total_chunks": 8,
  "diagram_types": ["electrical_single_line", "connection_detail"],
  "disciplines": ["electrical"],
  "total_components": 175,
  "analysis_date": "2025-10-09T14:30:00Z",
  "reasoning_effort": "high"
}
```

### 5. **Core Instructions** (The Key Part!)

```
**Instructions:**
- Use Python with pandas, plotly, or other libraries as needed
- Generate tables, charts, or files based on the user's request
- For tables: format as pandas DataFrame and show clearly
- For exports: create CSV/Excel files with descriptive names
- For charts: use plotly.express or plotly.graph_objects for interactive visualizations
  * Use .to_html() method to output Plotly charts as HTML with full interactivity
  * Include clear labels, titles, and hover tooltips for engineering data
  * Recommend: bar charts for component counts, line charts for trends, pie charts for distributions
- Include engineering context (component IDs, specifications, ratings)
```

### 6. Conversation History (Optional)

If there's conversation history, it includes the last 3 messages:

```
**Previous Conversation:**
user: Show all transformers as a table
assistant: Here's a table of all transformers found in the drawings...
user: Now filter by voltage over 10kV
```

### 7. User Question

```
**User Question:** Create a line chart of voltage levels across circuits
```

---

## Complete Example Prompt

Here's what the full prompt looks like for your question:

```
You are analyzing engineering diagram data. The following structured data has been extracted:

**Available Data:**

**Component Interpretations (JSON format):**
```json
[
  {
    "component_id": "T-101",
    "type": "transformer",
    "specifications": {
      "voltage_primary": "13.8kV",
      "voltage_secondary": "480V",
      "capacity": "1000kVA"
    }
  },
  {
    "component_id": "CB-201",
    "type": "circuit_breaker",
    "specifications": {
      "voltage": "480V",
      "amperage": "800A"
    }
  },
  {
    "component_id": "C-301",
    "type": "circuit",
    "specifications": {
      "voltage": "240V",
      "amperage": "100A",
      "purpose": "lighting"
    }
  },
  {
    "component_id": "C-302",
    "type": "circuit",
    "specifications": {
      "voltage": "120V",
      "amperage": "20A",
      "purpose": "receptacles"
    }
  }
]
```

**Visual Elements Summary:**
Total elements: 47
Sample: [...]

**Metadata:**
{
  "total_pages": 2,
  "total_components": 42,
  "diagram_types": ["electrical_single_line"]
}

**Instructions:**
- Use Python with pandas, plotly, or other libraries as needed
- Generate tables, charts, or files based on the user's request
- For tables: format as pandas DataFrame and show clearly
- For exports: create CSV/Excel files with descriptive names
- For charts: use plotly.express or plotly.graph_objects for interactive visualizations
  * Use .to_html() method to output Plotly charts as HTML with full interactivity
  * Include clear labels, titles, and hover tooltips for engineering data
  * Recommend: bar charts for component counts, line charts for trends, pie charts for distributions
- Include engineering context (component IDs, specifications, ratings)

**User Question:** Create a line chart of voltage levels across circuits
```

---

## Expected Code Agent Response

Based on this prompt, the Code Agent should:

1. **Parse the JSON data** to extract voltage information
2. **Write Python code** using Plotly:

```python
import plotly.graph_objects as go
import pandas as pd

# Extract voltage data from components
data = [
    {"component": "T-101 Primary", "voltage": 13800, "type": "Transformer"},
    {"component": "T-101 Secondary", "voltage": 480, "type": "Transformer"},
    {"component": "CB-201", "voltage": 480, "type": "Circuit Breaker"},
    {"component": "C-301", "voltage": 240, "type": "Lighting Circuit"},
    {"component": "C-302", "voltage": 120, "type": "Receptacle Circuit"}
]

df = pd.DataFrame(data)

# Sort by voltage (descending) for clear visualization
df = df.sort_values('voltage', ascending=False)

# Create interactive Plotly line chart
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df['component'],
    y=df['voltage'],
    mode='lines+markers',
    marker=dict(size=10, color='blue'),
    line=dict(width=2, color='blue'),
    text=df['type'],
    hovertemplate='<b>%{x}</b><br>Voltage: %{y:,.0f}V<br>Type: %{text}<extra></extra>'
))

fig.update_layout(
    title='Voltage Levels Across Circuits',
    xaxis_title='Component',
    yaxis_title='Voltage (V)',
    yaxis_type='log',  # Log scale for wide voltage range
    height=500,
    hovermode='closest'
)

# Output as HTML for interactive display
html_output = fig.to_html()
print(html_output)
```

3. **Return HTML output** that contains the interactive Plotly chart

4. **Provide explanation:**
```
I've created an interactive line chart showing voltage levels across all circuits 
and components found in the electrical drawings. The chart uses a logarithmic scale 
to accommodate the wide voltage range (120V to 13.8kV). 

Key features:
- Hover over any point to see component details
- Click and drag to zoom into specific voltage ranges
- Double-click to reset zoom
- The data flows from highest voltage (13.8kV primary) down to lowest (120V receptacles)

Components plotted:
- T-101 Primary: 13,800V
- T-101 Secondary: 480V
- CB-201: 480V
- C-301 (Lighting): 240V
- C-302 (Receptacles): 120V
```

---

## Key Instruction Details

### Charts Instruction (Lines 318-322)

This is the **critical part** that tells the agent to use Plotly:

```python
"- For charts: use plotly.express or plotly.graph_objects for interactive visualizations"
"  * Use .to_html() method to output Plotly charts as HTML with full interactivity"
"  * Include clear labels, titles, and hover tooltips for engineering data"
"  * Recommend: bar charts for component counts, line charts for trends, pie charts for distributions"
```

**Why this matters:**
- Without `.to_html()` instruction → Agent might just show the chart object
- Without "interactive visualizations" → Agent might use matplotlib instead
- Without hover tooltip guidance → Charts might lack engineering detail

### Tables Instruction (Line 315)

```python
"- For tables: format as pandas DataFrame and show clearly"
```

This ensures tables are properly formatted with pandas, not just printed lists.

### Exports Instruction (Line 316)

```python
"- For exports: create CSV/Excel files with descriptive names"
```

This guides the agent to create actual downloadable files, not just print data.

### Engineering Context Instruction (Line 323)

```python
"- Include engineering context (component IDs, specifications, ratings)"
```

This ensures the agent includes meaningful labels like "T-101: 13.8kV Primary" instead of just "13800".

---

## Prompt Engineering Notes

### ✅ What Works Well

1. **Structured JSON input** - Agent can easily parse component data
2. **Explicit tool recommendations** - "use plotly.express" is clear
3. **Method specification** - ".to_html() method" tells exactly what to do
4. **Use case examples** - "bar charts for counts, line charts for trends"
5. **Engineering domain** - Sets expectation for technical labels

### ⚠️ Potential Improvements

1. **Add example code snippet** - Show agent exactly what good Plotly code looks like
2. **Specify hover template format** - Guide exact hover tooltip structure
3. **Add color guidance** - Suggest color schemes for engineering data
4. **Specify axis formatting** - Guide log scale, unit formatting, etc.
5. **Add error handling** - Instruct on missing data scenarios

### 🎯 Alternative Instruction (More Detailed)

Here's an enhanced version you could use:

```python
context_parts.append("- For charts: create interactive Plotly visualizations")
context_parts.append("  * Import: plotly.express as px or plotly.graph_objects as go")
context_parts.append("  * Chart types:")
context_parts.append("    - Bar charts: component counts, equipment quantities by type")
context_parts.append("    - Line charts: voltage profiles, trends across circuits")
context_parts.append("    - Pie charts: load distribution, component type percentages")
context_parts.append("    - Scatter plots: correlation analysis (power vs efficiency)")
context_parts.append("  * Required features:")
context_parts.append("    - Title: Clear description of what's plotted")
context_parts.append("    - Axis labels: Include units (V, A, kW, HP, etc.)")
context_parts.append("    - Hover tooltips: Show component ID, specifications, and values")
context_parts.append("    - Color coding: Use consistent colors for component types")
context_parts.append("  * Output: Call fig.to_html() and print the HTML string")
context_parts.append("  * Example hover template: '<b>%{text}</b><br>Voltage: %{y:,.0f}V<br>Capacity: %{customdata[0]}<extra></extra>'")
```

---

## How to Customize the Prompt

The prompt is generated in `_prepare_context_message()` method (lines 273-325). To customize:

### Location in Code

```python
# File: code_agent_handler.py
# Method: _prepare_context_message()
# Lines: 312-323 (Instructions section)
```

### Example Customization

To add more specific chart guidance:

```python
# Add after line 322
context_parts.append("- Chart color scheme: Use blue for electrical, green for mechanical, orange for P&ID")
context_parts.append("- Chart size: Set height=500-600 for optimal visibility")
context_parts.append("- Axis scaling: Use log scale (yaxis_type='log') for wide voltage/power ranges")
```

### Testing Changes

After modifying the prompt:

1. **Restart the UI** - `python edisonpro_ui.py`
2. **Test with question** - "Plot voltage distribution"
3. **Check console output** - See if agent generates expected Plotly code
4. **Verify chart quality** - Check hover tooltips, labels, interactivity

---

## Comparison: o3-pro vs Code Agent

### o3-pro Prompt (Understanding)

When routed to o3-pro, the system uses a completely different prompt focused on **reasoning and explanation**:

```
You are an expert engineering analysis assistant specializing in diagram interpretation.

Context: [retrieved chunks from Azure AI Search]

Question: Create a line chart of voltage levels

Instructions:
- Provide detailed reasoning chain
- Extract evidence from drawings
- Assess confidence
- Identify technical specifications
```

**Result:** Text explanation + matplotlib code snippet (not executed)

### Code Agent Prompt (Transformation)

As shown above, focuses on **execution and output generation**:

```
Available Data: [JSON components]

Instructions:
- Generate charts using Plotly
- Output as interactive HTML
- Include hover tooltips
- Execute code and return results
```

**Result:** Actual interactive Plotly chart (executed, rendered)

---

## Summary

The Code Agent instruction prompt has **5 key components**:

1. **Context Introduction** - Sets the engineering analysis context
2. **Structured Data** - Provides JSON component data for parsing
3. **Visual Elements** - Adds spatial and relationship data
4. **Metadata** - Gives document-level context
5. **Instructions** - **Critical section** that guides tool choice and output format

**Most Important Instructions:**
- ✅ Use Plotly for charts
- ✅ Call .to_html() for HTML output
- ✅ Include hover tooltips
- ✅ Use engineering labels (IDs, specs, ratings)

**Location to Modify:**
- File: `code_agent_handler.py`
- Method: `_prepare_context_message()`
- Lines: 312-323

**Testing:**
Ask questions like "Plot voltage distribution" and verify the agent produces interactive Plotly charts with proper labels and hover functionality.

