# Bing Search Connection ID Setup Guide

## ⚠️ Important: Connection ID Format

The `BING_CONNECTION_ID` is **NOT** just the simple connection name. It's a **full Azure resource path** with multiple slashes.

### Correct Format

```bash
BING_CONNECTION_ID="/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{ai_service}/projects/{project_name}/connections/{connection_name}"
```

### Real Example

```bash
BING_CONNECTION_ID="/subscriptions/12345678-abcd-1234-abcd-123456789abc/resourceGroups/my-resource-group/providers/Microsoft.CognitiveServices/accounts/my-ai-service/projects/edison-pro-project/connections/bing-search-connection"
```

## Step-by-Step Instructions

### 1. Create Grounding with Bing Search Resource

First, create the Bing Search resource in Azure Portal:

1. Go to [Azure Portal](https://portal.azure.com/#create/Microsoft.BingGroundingSearch)
2. Select your subscription and resource group
3. Choose a name for the resource (e.g., "my-bing-search")
4. Select a region
5. Accept the terms and create

**Important**: Create this resource in the **same resource group** as your Azure AI Project.

### 2. Connect to Azure AI Studio Project

1. Go to [Azure AI Studio](https://ai.azure.com)
2. Open your AI Project (the one used for Code Agent)
3. Click **"Connected resources"** in the left sidebar
4. Click **"Add connection"** button
5. Select **"Grounding with Bing Search"**
6. Select the Bing Search resource you created in step 1
7. Give it a connection name (e.g., "bing-connection")
8. Click **"Add connection"**

### 3. Get the Connection ID

After connecting, you need to get the **full connection ID**:

#### Method 1: From Azure AI Studio (Recommended)

1. In Azure AI Studio, go to your project
2. Click **"Connected resources"**
3. Find your Bing Search connection in the list
4. Click on the connection to view details
5. Look for the **"Connection ID"** field
6. Copy the **entire path** (starts with `/subscriptions/...`)

#### Method 2: From Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Azure AI Project resource
3. Click **"Connections"** under Settings
4. Find your Bing Search connection
5. Click to view properties
6. Copy the **Resource ID** or **Connection ID**

### 4. Add to .env File

Add the connection ID to your `.env` file with **quotes** (important for paths with slashes):

```bash
# Use quotes for the full path
BING_CONNECTION_ID="/subscriptions/12345678-abcd-1234-abcd-123456789abc/resourceGroups/my-rg/providers/Microsoft.CognitiveServices/accounts/my-ai-service/projects/my-project/connections/bing-connection"
```

### 5. Verify Configuration

Test your configuration:

```bash
# Check if environment variable is loaded
python -c "import os; print(os.getenv('BING_CONNECTION_ID'))"
```

Expected output should show the full path with slashes:
```
/subscriptions/12345678-.../connections/bing-connection
```

## Common Mistakes

### ❌ Wrong: Just the connection name
```bash
BING_CONNECTION_ID=bing-connection
```

### ❌ Wrong: Missing quotes
```bash
BING_CONNECTION_ID=/subscriptions/12345678-.../connections/bing-connection
```

### ✅ Correct: Full path with quotes
```bash
BING_CONNECTION_ID="/subscriptions/12345678-abcd-1234-abcd-123456789abc/resourceGroups/my-rg/providers/Microsoft.CognitiveServices/accounts/my-ai-service/projects/my-project/connections/bing-connection"
```

## Troubleshooting

### Error: "Invalid connection ID format"

**Cause**: Connection ID is not in the correct format.

**Solution**: Ensure you copied the **full resource path** from Azure AI Studio, not just the connection name.

### Error: "Connection not found"

**Cause**: Connection ID doesn't exist or has wrong subscription/resource group.

**Solution**: Verify the connection exists in Azure AI Studio under "Connected resources".

### Error: "Access denied"

**Cause**: The Code Agent doesn't have permission to use the Bing Search connection.

**Solution**: Ensure the Code Agent's managed identity or API key has access to the connection.

## Cost Information

Bing Search API usage incurs costs:

- **Free tier**: Limited number of queries per month
- **Paid tier**: Charged per 1000 queries
- **Typical cost**: ~$0.001-0.005 per query (very low)

See [Bing Grounding Pricing](https://www.microsoft.com/en-us/bing/apis/grounding-pricing) for current rates.

## Security Best Practices

1. **Use Managed Identity in Production**: Set `AZURE_OPENAI_AGENT_USE_MANAGED_IDENTITY=true` instead of API keys
2. **Don't commit .env**: Keep `.env` in `.gitignore`
3. **Rotate keys regularly**: If using API keys, rotate them every 90 days
4. **Restrict access**: Only grant permissions to necessary resources

## Testing Web Search

Once configured, test the feature in the UI:

1. Run `python edisonpro_ui.py`
2. Navigate to Q&A tab
3. Check the **"🌐 Enable Web Search (Bing)"** checkbox
4. Ask a question: "What are the latest IEEE standards for electrical distribution?"
5. Verify the answer includes web-sourced information

## Documentation References

- [Grounding with Bing Search Overview](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-grounding)
- [Bing Search Code Samples](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/bing-code-samples)
- [Azure AI Projects SDK](https://learn.microsoft.com/en-us/python/api/azure-ai-agents/)

---

**Last Updated**: October 2025  
**EDISON PRO Version**: 2.0 with GPT-5 + Bing Search
