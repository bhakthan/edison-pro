# Code Agent Quick Setup Guide

## ⚠️ Authentication Issue: API Key Not Supported

**Important:** Azure AI Projects SDK does **NOT** support direct API key authentication. It requires **token-based authentication** (OAuth/TokenCredential).

---

## 🚀 Quick Fix (5 minutes)

### Option 1: Azure CLI Login (Recommended for Development)

1. **Install Azure CLI** (if not already installed):
   ```bash
   # Download from: https://aka.ms/installazurecliwindows
   # Or use winget
   winget install Microsoft.AzureCLI
   ```

2. **Login to Azure**:
   ```bash
   az login
   ```
   This opens a browser window for authentication.

3. **Set subscription** (if you have multiple):
   ```bash
   az account set --subscription "your-subscription-name"
   ```

4. **Verify**:
   ```bash
   az account show
   ```

5. **Update your `.env`**:
   ```env
   # Code Agent Configuration
   AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
   AZURE_OPENAI_AGENT_NAME=edison-code-agent
   AZURE_OPENAI_AGENT_MODEL=gpt-5.4
   
   # No API key needed! DefaultAzureCredential uses your az login
   ```

6. **Restart the UI**:
   ```bash
   python edisonpro_ui.py
   ```

7. **Look for success message**:
   ```
   ✅ Code Agent initialized: your-agent-name
   ```

### Option 2: VS Code Azure Extension

1. **Install Azure Extension**:
   - Press `Ctrl+Shift+X`
   - Search for "Azure Account"
   - Install the extension

2. **Sign in to Azure**:
   - Press `Ctrl+Shift+P`
   - Type "Azure: Sign In"
   - Complete authentication

3. **Update `.env`** (same as Option 1)

4. **Restart the UI**

### Option 3: Service Principal (CI/CD / Production)

1. **Create Service Principal**:
   ```bash
   az ad sp create-for-rbac --name "edison-code-agent" \
     --role Contributor \
     --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group}
   ```
   
   This outputs:
   ```json
   {
     "appId": "xxxx",
     "displayName": "edison-code-agent",
     "password": "xxxx",
     "tenant": "xxxx"
   }
   ```

2. **Set environment variables in `.env`**:
   ```env
   # Service Principal Authentication
   AZURE_TENANT_ID=xxxx
   AZURE_CLIENT_ID=xxxx
   AZURE_CLIENT_SECRET=xxxx
   
   # Code Agent Configuration
   AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
   AZURE_OPENAI_AGENT_NAME=edison-code-agent
   AZURE_OPENAI_AGENT_MODEL=gpt-5.4
   ```

3. **Restart the UI**

---

## ✅ Verification Steps

After setup, verify Code Agent is working:

### Step 1: Check Startup Logs

Run `python edisonpro_ui.py` and look for:

**✅ Success:**
```
Initializing Code Agent with DefaultAzureCredential...
Trying: Environment → Managed Identity → Azure CLI → VS Code → Browser
✅ Code Agent initialized: your-agent-name
```

**❌ Failure:**
```
Failed to initialize Code Agent: <error>
⚠️ Code Agent not configured (set AZURE_OPENAI_AGENT_* in .env)

💡 CODE AGENT AUTHENTICATION HELP:
   Azure AI Projects requires token-based authentication (NOT API key)
   
   Quick Fix Options:
   1️⃣  Azure CLI:  Run 'az login' in terminal
   2️⃣  VS Code:   Sign in to Azure (Ctrl+Shift+P → 'Azure: Sign In')
   3️⃣  Env Vars:  Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
```

### Step 2: Test Detection

In the UI, ask a chart question and watch console output:

**Question:** `"Give pad P5810284 component distribution as a pie chart"`

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

Ask: `"Plot voltage distribution as a pie chart"`

**✅ Success:**
- See interactive Plotly pie chart in "Interactive Charts (Phase 3)" section
- Chart has hover tooltips
- Can zoom/pan/click legend

**❌ Failure:**
- Only see text response with percentages
- No actual chart displayed
- Response from o3-pro with explanation

---

## 🔍 Troubleshooting

### Error: "No subscription found"

```bash
# List available subscriptions
az account list --output table

# Set the correct subscription
az account set --subscription "Subscription Name"
```

### Error: "Please run 'az login'"

```bash
# Login
az login

# If behind a proxy or firewall
az login --use-device-code
```

### Error: "Tenant not found"

Make sure your Azure account has access to the subscription where the Azure AI Project is deployed.

### Error: "Agent 'xxx' not found"

1. Go to Azure Portal → Your AI Project
2. Navigate to "Agents" section
3. Copy the correct Agent ID
4. Update `.env`:
   ```env
   AZURE_OPENAI_AGENT_NAME=edison-code-agent
   ```

### Error: "Authentication failed"

Try refreshing your Azure CLI login:
```bash
az logout
az login
```

---

## 📋 Required `.env` Variables

**Minimum for Code Agent:**
```env
# Azure AI Projects Endpoint
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}

# Agent ID (from Azure Portal → AI Project → Agents)
AZURE_OPENAI_AGENT_NAME=edison-code-agent
AZURE_OPENAI_AGENT_MODEL=gpt-5.4

# Authentication: Use one of these methods
# Method 1: Azure CLI (run 'az login')
# Method 2: VS Code (sign in to Azure)
# Method 3: Service Principal (set these three):
#   AZURE_TENANT_ID=xxx
#   AZURE_CLIENT_ID=xxx
#   AZURE_CLIENT_SECRET=xxx
```

**Complete `.env` example:**
```env
# o3-pro Configuration (for understanding questions)
AZURE_OPENAI_PRO_ENDPOINT=https://your-resource.openai.azure.com/openai/v1/
AZURE_OPENAI_API_KEY=your-o3-key
AZURE_OPENAI_PRO_DEPLOYMENT_NAME=o3-pro

# Embeddings Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_OPENAI_API_VERSION=2024-02-01

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=edison-engineering-diagrams

# Code Agent Configuration (Phase 3)
AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}
AZURE_OPENAI_AGENT_NAME=edison-code-agent
AZURE_OPENAI_AGENT_MODEL=gpt-5.4

# Optional: Service Principal (if not using az login)
# AZURE_TENANT_ID=xxx
# AZURE_CLIENT_ID=xxx
# AZURE_CLIENT_SECRET=xxx
```

---

## 🎯 Why Your Pie Chart Question Failed

Your question: **"Give pad P5810284 component distribution as a pie chart"**

### What Should Have Happened

1. ✅ Question contains **"pie chart"** keyword
2. ✅ Detection logic triggers Code Agent
3. ✅ Code Agent generates Plotly pie chart
4. ✅ Interactive chart displayed in UI

### What Actually Happened

1. ✅ Question contains "pie chart" keyword
2. ❌ **Code Agent initialization failed** (AzureKeyCredential not supported)
3. ❌ `self.code_agent.available = False`
4. ❌ Routed to o3-pro instead
5. ❌ o3-pro gave text explanation with percentages, not actual chart

### The Fix

Run `az login` and restart the UI. Then ask again:

```
"Give pad P5810284 component distribution as a pie chart"
```

You should now see an **interactive Plotly pie chart** with:
- 72% Excavation (SS Tax items)
- 18% JJ LBE terminations
- 9% Poly pad
- Hover tooltips showing exact counts
- Click legend to show/hide slices

---

## 📚 Documentation

- **CODE_AGENT_TROUBLESHOOTING.md** - Common errors and solutions
- **CODE_AGENT_PROMPT.md** - Detailed instruction prompt structure
- **PHASE_3_COMPLETE.md** - Complete Phase 3 technical guide
- **README.md** - Main documentation with Code Agent section

---

## 🆘 Still Not Working?

1. **Check Azure CLI is installed**:
   ```bash
   az --version
   ```

2. **Check you're logged in**:
   ```bash
   az account show
   ```

3. **Check your subscription has access to the AI Project**:
   ```bash
   az resource list --resource-type Microsoft.MachineLearningServices/workspaces
   ```

4. **Verify endpoint and agent ID**:
   - Endpoint should end with `.openai.azure.com`
   - Agent ID should be a GUID or string identifier

5. **Check Python version**:
   ```bash
   python --version  # Should be 3.8+
   ```

6. **Reinstall dependencies**:
   ```bash
   pip install -r requirements.txt --force-reinstall
   ```

---

**Summary:** Azure AI Projects SDK requires OAuth token authentication, not API keys. Run `az login` and you're good to go! 🚀
