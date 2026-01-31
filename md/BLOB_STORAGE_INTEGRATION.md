# Azure Blob Storage Integration Guide

## Overview

EDISON PRO now supports reading engineering diagrams from Azure Blob Storage and writing analysis results back to blob containers. This enables cloud-native workflows, team collaboration, and scalable document processing.

## Benefits

### Input from Blob Storage
- ✅ No need to download files locally first
- ✅ Process entire folders/containers at once
- ✅ Team access to shared document libraries
- ✅ Version control and audit trails
- ✅ Cost-effective storage at scale

### Output to Blob Storage
- ✅ Persistent analysis results
- ✅ Shareable via SAS URLs
- ✅ Integration-ready (Power BI, Logic Apps, etc.)
- ✅ Automatic organization by timestamp
- ✅ Geo-redundant storage options

## Setup

### 1. Install Dependencies

```bash
pip install azure-storage-blob azure-identity
```

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Connection String Method (Recommended for Development)
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=your-account;AccountKey=your-key;EndpointSuffix=core.windows.net"

# OR Managed Identity Method (Recommended for Production)
# AZURE_STORAGE_ACCOUNT_URL=https://your-account.blob.core.windows.net
# AZURE_STORAGE_USE_MANAGED_IDENTITY=true

# Default Containers
AZURE_STORAGE_INPUT_CONTAINER=engineering-diagrams
AZURE_STORAGE_OUTPUT_CONTAINER=edison-analysis-results
```

### 3. Create Blob Containers

Using Azure CLI:
```bash
az storage container create --name engineering-diagrams --account-name your-account
az storage container create --name edison-analysis-results --account-name your-account
```

Or using Azure Portal:
1. Navigate to your Storage Account
2. Go to "Containers"
3. Click "+ Container"
4. Name: `engineering-diagrams`, Access level: Private

## Usage

### Command Line Interface

#### Basic Blob Analysis
```bash
# Analyze all files in a container
python edisonpro.py --blob-container engineering-diagrams --interactive

# Analyze specific folder/prefix
python edisonpro.py \
  --blob-container engineering-diagrams \
  --blob-prefix "projects/2024/electrical/" \
  --interactive

# With output to blob
python edisonpro.py \
  --blob-container engineering-diagrams \
  --blob-prefix "drawings/" \
  --output-blob-container edison-results \
  --output-blob-prefix "analysis-project-x/" \
  --interactive
```

#### Advanced Options
```bash
# Filter by file extensions
python edisonpro.py \
  --blob-container diagrams \
  --blob-extensions ".pdf,.png" \
  --interactive

# Keep temporary files for debugging
python edisonpro.py \
  --blob-container diagrams \
  --keep-temp-files \
  --interactive

# Specify domain and reasoning effort
python edisonpro.py \
  --blob-container engineering-diagrams \
  --blob-prefix "electrical/" \
  --domain electrical \
  --reasoning-effort high \
  --interactive
```

### Web UI (Gradio)

1. **Start the UI**:
   ```bash
   python edisonpro_ui.py
   ```

2. **Navigate to Blob Storage Tab**:
   - Click the "📦 Blob Storage" tab
   - Enter container name and prefix
   - Click "📋 List Files" to browse
   - Configure analysis parameters
   - Click "🚀 Start Analysis"

3. **View Results**:
   - Analysis results automatically uploaded to output container
   - Switch to "💬 Q&A Chat" tab to ask questions
   - System automatically reloads with new documents

## Architecture

### Input Flow
```
Azure Blob Container
    ↓
Download to Temp Directory (parallel, 4 workers)
    ↓
EDISON PRO Analysis (o3-pro)
    ↓
Upload Results to Output Blob (parallel, 4 workers)
    ↓
Cleanup Temp Files
```

### File Organization

Input Container Structure:
```
engineering-diagrams/
├── 2024/
│   ├── electrical/
│   │   ├── plan-001.pdf
│   │   └── schematic-002.png
│   └── mechanical/
│       └── assembly-003.pdf
└── 2023/
    └── archived/
```

Output Container Structure:
```
edison-analysis-results/
├── analysis-20241008_143022/
│   ├── 00_analysis_log.txt
│   ├── page_001_structure_analysis.json
│   ├── page_001_image1_original.png
│   ├── chunk_001_pro_chunk_0.txt
│   └── ...
└── analysis-20241008_150315/
    └── ...
```

## Features

### Phase 1: Basic Blob Input ✅
- [x] Download files from blob container
- [x] Support for prefix/folder filtering
- [x] File extension filtering
- [x] Parallel downloads (4 workers)
- [x] Temporary directory management
- [x] CLI argument support

### Phase 2: Blob Output ✅
- [x] Upload results to blob container
- [x] Automatic timestamp-based organization
- [x] Parallel uploads (4 workers)
- [x] Intermediate file preservation
- [x] Optional temp file cleanup

### Phase 3: Optimization ✅
- [x] Streaming downloads/uploads
- [x] Progress tracking
- [x] Async operations
- [x] Memory-efficient processing
- [x] Error handling and retry logic

### Blob Storage Manager API

```python
from blob_storage import BlobStorageManager, create_blob_manager_from_env

# Initialize from environment variables
blob_manager = create_blob_manager_from_env(container_name="engineering-diagrams")

# List files
blobs = blob_manager.list_blobs(
    prefix="drawings/2024/",
    file_extensions=[".pdf", ".png"]
)

# Download files
local_files = blob_manager.download_blobs_to_temp(
    prefix="drawings/",
    max_workers=4
)

# Upload results
blob_urls = blob_manager.upload_folder_to_blob(
    local_folder="./intermediate_files",
    blob_prefix="analysis-results/",
    max_workers=4
)

# Generate SAS URL (7-day expiry)
sas_url = blob_manager.generate_sas_url("analysis.pdf", expiry_hours=168)

# Cleanup
blob_manager.cleanup_temp_files()
```

### Context Manager Support

```python
from blob_storage import BlobStorageManager

with BlobStorageManager(connection_string, "my-container") as blob_mgr:
    files = blob_mgr.download_blobs_to_temp(prefix="drawings/")
    # Process files...
    blob_mgr.upload_folder_to_blob("./results", "output/")
    # Automatic cleanup on exit
```

## Security

### Authentication Methods

1. **Connection String** (Development):
   - Simple setup
   - Full access to storage account
   - Store in .env file (never commit!)

2. **Managed Identity** (Production):
   - No credentials in code
   - Azure-managed authentication
   - Automatic rotation
   - Works in Azure VM, App Service, AKS

### Permissions

Minimum required permissions:
- **Input Container**: `Storage Blob Data Reader`
- **Output Container**: `Storage Blob Data Contributor`

### Network Security

- Use Private Endpoints for sensitive data
- Enable Firewall rules to restrict access
- Encryption at rest enabled by default
- HTTPS-only transfers enforced

## Cost Optimization

### Storage Costs
- **Hot Tier**: ~$0.018/GB/month (active processing)
- **Cool Tier**: ~$0.010/GB/month (archives, 30-day minimum)
- **Archive Tier**: ~$0.002/GB/month (long-term storage)

### Transaction Costs
- Read/Write: ~$0.004 per 10,000 operations
- List: ~$0.05 per 10,000 operations
- Very cost-effective for typical usage

### Best Practices
1. Use Cool tier for analysis archives (>30 days old)
2. Lifecycle policies to auto-archive old results
3. Batch operations to minimize transactions
4. Use prefix/folder structure for efficient filtering
5. Clean up temporary files promptly

### Example Monthly Costs
Analyzing 1000 PDFs/month:
- Storage (10GB input + 5GB output): $0.27
- Transactions (20K read + 20K write): $0.01
- **Total: ~$0.28/month** 💰

## Troubleshooting

### Connection Issues

**Error**: "Could not connect to blob storage"
- Check `AZURE_STORAGE_CONNECTION_STRING` in .env
- Verify storage account name and key
- Test with Azure Storage Explorer

**Error**: "Container not found"
- Create container: `az storage container create --name my-container`
- Check container name spelling
- Verify account has access

### Upload/Download Failures

**Error**: "Permission denied"
- Verify storage account key
- Check RBAC roles (Managed Identity)
- Ensure container exists

**Slow Performance**
- Increase `max_workers` (default: 4)
- Check network connectivity
- Use Azure region close to compute

### Authentication Issues

**Managed Identity not working**:
```bash
# Verify identity assignment
az vm identity show --resource-group myRG --name myVM

# Assign role
az role assignment create \
  --assignee <identity-principal-id> \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<account>
```

## Examples

### Complete Workflow

```bash
# 1. Upload drawings to blob
az storage blob upload-batch \
  --account-name myaccount \
  --destination engineering-diagrams/project-alpha \
  --source ./local-drawings

# 2. Analyze from blob
python edisonpro.py \
  --blob-container engineering-diagrams \
  --blob-prefix "project-alpha/" \
  --output-blob-container edison-results \
  --reasoning-effort high \
  --interactive

# 3. Query results
# (Interactive Q&A mode starts automatically)
Q: What electrical equipment is shown?
Q: List all clearance requirements

# 4. Download results
az storage blob download-batch \
  --account-name myaccount \
  --source edison-results/analysis-20241008_143022 \
  --destination ./local-results
```

### Automated Processing Script

```python
import asyncio
from blob_storage import create_blob_manager_from_env
from edisonpro import DiagramAnalysisOrchestratorPro

async def process_blob_folder(container, prefix):
    # Initialize
    blob_mgr = create_blob_manager_from_env(container_name=container)
    orchestrator = DiagramAnalysisOrchestratorPro()
    
    # Download
    local_files = blob_mgr.download_blobs_to_temp(prefix=prefix)
    
    # Analyze
    if local_files:
        result = await orchestrator.analyze_images_from_folder(
            blob_mgr.temp_dir, 
            domain="electrical"
        )
        
        # Upload results
        if orchestrator.preprocessor.intermediate_dir:
            output_mgr = create_blob_manager_from_env(container_name="results")
            output_mgr.upload_folder_to_blob(
                str(orchestrator.preprocessor.intermediate_dir),
                f"processed/{prefix}"
            )
    
    # Cleanup
    blob_mgr.cleanup_temp_files()

# Run
asyncio.run(process_blob_folder("diagrams", "2024/Q1/"))
```

## Phase 4: Advanced Features

For production enterprise deployments, see **PHASE4_ADVANCED_FEATURES.md**:

### ✅ Managed Identity (IMPLEMENTED)
- **Status**: Production Ready
- **Benefit**: Secure authentication without connection strings
- **Setup**: 10 minutes with Azure CLI
- **Cost**: Free (part of Azure AD)

### 📋 Blob Change Feed Integration (Guide Available)
- **Status**: Implementation Guide
- **Benefit**: Auto-process new uploads via Event Grid
- **Setup**: Azure Function + Event Grid subscription
- **Cost**: ~$0.20 per 1M executions

### 📋 Lifecycle Policies (Guide Available)
- **Status**: Configuration Guide
- **Benefit**: Auto-archive old results → 77% cost savings
- **Setup**: 5 minutes via Azure Portal
- **Cost**: Free (reduces storage costs)

### 📋 Azure Functions Integration (Guide Available)
- **Status**: Deployment Guide
- **Benefit**: Serverless, scalable processing
- **Setup**: Azure Function App deployment
- **Cost**: ~$4.80/month for 1000 analyses

**See PHASE4_ADVANCED_FEATURES.md for complete implementation guides.**

---

## References

- [Azure Blob Storage Documentation](https://learn.microsoft.com/azure/storage/blobs/)
- [azure-storage-blob PyPI](https://pypi.org/project/azure-storage-blob/)
- [Azure Storage Explorer](https://azure.microsoft.com/features/storage-explorer/)
- [Managed Identity](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)
- [Azure Functions Python](https://learn.microsoft.com/azure/azure-functions/functions-reference-python)
- [Event Grid](https://learn.microsoft.com/azure/event-grid/overview)
- [Lifecycle Management](https://learn.microsoft.com/azure/storage/blobs/lifecycle-management-overview)
