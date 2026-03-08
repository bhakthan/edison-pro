# Code Agent Troubleshooting Guide

## Issue: Questions Go to o3-pro Instead of Code Agent

### Symptoms
- Ask "create a line chart" → o3-pro responds with explanation/code snippet instead of actual chart
- Ask "show as table" → o3-pro provides reasoning instead of HTML table
- Console shows: `⚠️ Code Agent not configured`
- Console shows: `Code Agent decision: NO` (should be YES for chart/table questions)

### Root Cause
Code Agent initialization failed, so `self.code_agent.available = False`. This causes ALL questions to route to o3-pro regardless of keywords.

---

## Common Initialization Failures

### 1. Tenant Mismatch Error

**Error Message:**
```
Failed to initialize Code Agent: (Tenant provided in token does not match resource token)
Token tenant 72f988bf-86f1-41af-91ab-2d7cd011db47 does not match resource tenant.
```

**Cause:** Using `DefaultAzureCredential()` (Managed Identity) but the Azure AI Projects resource is in a different tenant.

**Solutions:**

#### Option A: Switch to API Key Authentication (Recommended)
Add to `.env`:
```env
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
AZURE_OPENAI_AGENT_NAME=edison-code-agent
AZURE_OPENAI_AGENT_MODEL=gpt-5.4

# Optional
CODE_AGENT_ENABLE_DYNAMIC_FALLBACK=true
```

#### Option B: Use Correct Tenant for Managed Identity
Add tenant ID to `.env`:
```env
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
AZURE_OPENAI_AGENT_NAME=edison-code-agent
AZURE_OPENAI_AGENT_MODEL=gpt-5.4
AZURE_TENANT_ID=your-correct-tenant-id
```

Update `code_agent_handler.py` to use tenant:
```python
credential = DefaultAzureCredential(tenant_id=os.getenv("AZURE_TENANT_ID"))
```

---

### 2. Missing Environment Variables

**Error Message:**
```
⚠️ Code Agent not configured (set AZURE_OPENAI_AGENT_* in .env)
```

**Cause:** Required environment variables not set.

**Solution:** Add to `.env`:
```env
# Minimum required
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
AZURE_OPENAI_AGENT_NAME=edison-code-agent

# Choose one authentication method:
# Option 1: API Key (simpler)
AZURE_OPENAI_AGENT_API_KEY=your-api-key

# Option 2: Managed Identity (production)
AZURE_OPENAI_AGENT_USE_MANAGED_IDENTITY=true
```

---

### 3. Invalid API Key

**Error Message:**
```
Failed to initialize Code Agent: 401 Unauthorized
```

**Cause:** API key is incorrect or expired.

**Solution:** 
1. Go to Azure Portal → Your AI Project
2. Navigate to "Keys and Endpoint"
3. Copy a valid key
4. Update `.env` with new key

---

### 4. Agent Not Found

**Error Message:**
```
Failed to initialize Code Agent: Agent 'xxx' not found
```

**Cause:** `AZURE_OPENAI_AGENT_NAME` points at the wrong managed agent name, or the agent no longer exists.

**Solution:**
1. Go to Azure Portal → Your AI Project → Agents
2. Copy the correct Agent ID
3. Update `.env`:
```env
AZURE_OPENAI_AGENT_NAME=edison-code-agent
```

---

## Verification Steps

### Step 1: Check Initialization
Run the UI and look for this in console output:

**✅ Success:**
```
✅ Code Agent initialized: your-agent-name
```

**❌ Failure:**
```
Failed to initialize Code Agent: <error>
⚠️ Code Agent not configured
```

### Step 2: Test Detection
Ask a chart question and check console:

**✅ Success:**
```
Code Agent decision: YES
🤖 Using Code Agent (GPT-5.4 + Code Interpreter + Meta-Agent fallback)
```

**❌ Failure:**
```
Code Agent decision: NO
🧠 Using o3-pro (Deep Reasoning)
```

### Step 3: Test Chart Generation
Ask: `"Plot voltage distribution as a bar chart"`

**✅ Success:**
- See interactive Plotly chart in "Interactive Charts (Phase 3)" section
- Can zoom, pan, hover over data points

**❌ Failure:**
- Only see text response with matplotlib code snippet
- No interactive chart displayed

---

## Quick Fix for Current Session

If you need Code Agent working immediately:

1. **Get your API key** from Azure Portal
2. **Add to `.env`:**
```env
AZURE_OPENAI_AGENT_NAME=edison-code-agent
AZURE_OPENAI_AGENT_MODEL=gpt-5.4
CODE_AGENT_ENABLE_DYNAMIC_FALLBACK=true
```
3. **Restart the UI:**
```bash
python edisonpro_ui.py
```
4. **Verify initialization:**
Look for `✅ Code Agent initialized` in startup logs

---

## Example Questions That Should Use Code Agent

Once configured correctly, these questions automatically route to Code Agent:

### Tables (Phase 1 & 2)
- "Show all transformers as a table"
- "List circuit breakers with ratings"
- "Create a BOM for zone A"

### Charts (Phase 3 - Plotly)
- "Plot voltage distribution" ← Your question!
- "Create a bar chart of component counts"
- "Show load as pie chart"
- "Generate scatter plot of power vs efficiency"

### Calculations
- "Calculate total power load"
- "What is the sum of transformer capacities?"
- "Compute average voltage"

### Exports
- "Export to CSV"
- "Download as Excel"
- "Save as JSON file"

---

## Detection Keywords Reference

Code Agent triggers on these 45 keywords:
```python
'table', 'csv', 'excel', 'spreadsheet', 'dataframe',
'chart', 'plot', 'graph', 'visualize', 'visualization', 'diagram',
'calculate', 'computation', 'sum', 'average', 'mean', 'total',
'filter', 'sort', 'group', 'aggregate', 'count',
'export', 'download', 'save', 'file',
'bom', 'bill of materials', 'list all', 'show all',
'statistics', 'analysis', 'distribution', 'histogram',
'bar chart', 'pie chart', 'line chart', 'scatter plot', 'heatmap'
```

Plus these regex patterns:
```python
r'show .* (as|in) (a |an )?table'
r'create (a |an )?(table|chart|graph|plot)'
r'list all .*'
r'give me .* in .* format'
r'export .* to'
r'calculate (the |total )?.*'
r'how many .*'
r'what (is|are) the (average|total|sum|count)'
```

Your question "create a line chart" matches:
- ✅ Keyword: `'line chart'`
- ✅ Pattern: `r'create (a |an )?(table|chart|graph|plot)'`

---

## Cost Comparison

| Scenario | Agent Used | Cost per Query |
|----------|-----------|---------------|
| Code Agent working | Code Agent | $0.01-0.02 |
| Code Agent broken | o3-pro | $0.001 |

**Note:** While o3-pro is cheaper, it won't generate actual interactive charts or tables - only explanations and code snippets.

---

## Still Having Issues?

1. **Check logs:** Look at full console output during startup
2. **Verify credentials:** Test API key in Azure Portal
3. **Check agent exists:** Verify agent in Azure AI Studio
4. **Try minimal .env:**
```env
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
AZURE_OPENAI_AGENT_NAME=edison-code-agent
AZURE_OPENAI_AGENT_MODEL=gpt-5.4
```
5. **Restart clean:**
```bash
# Close all terminals
# Delete .env, recreate with minimal config
# Restart: python edisonpro_ui.py
```

---

## Documentation References

- **Phase 3 Complete Guide:** `PHASE_3_COMPLETE.md`
- **Code Agent Quick Start:** `CODE_AGENT_QUICKSTART.md`
- **Code Agent Integration:** `CODE_AGENT_INTEGRATION.md`
- **Main README:** `README.md` (see "Code Agent Integration" section)
