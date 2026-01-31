# Azure AI Search Integration Guide

## Overview

EDISON and EDISON PRO now use **Azure AI Search** instead of ChromaDB for vector storage and retrieval. This provides:

✅ **Hybrid Search**: Vector similarity + BM25 keyword matching  
✅ **Production-Ready**: Managed service with 99.9% SLA  
✅ **Advanced Filtering**: Filter by diagram_type, page_numbers, components, etc.  
✅ **No Local Dependencies**: No ChromaDB installation or data files  
✅ **Better Scalability**: Handle millions of documents  
✅ **Semantic Ranking**: AI-powered result ranking  

---

## Quick Start

### 1. Create Azure Search Index

First, run the index creation script:

```bash
python create_azure_search_index.py
```

This creates the `edison-diagrams` index with:
- 11 fields including content, metadata, and 1536-dim vectors
- HNSW vector search configuration
- Semantic search capabilities

### 2. Update Environment Variables

Add to your `.env` file:

```bash
# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-api-key
AZURE_SEARCH_INDEX_NAME=edison-diagrams
```

### 3. Install Azure Search SDK

Update dependencies:

```bash
pip install azure-search-documents==11.6.0b4
```

You can now **remove ChromaDB**:

```bash
pip uninstall chromadb -y
```

---

## Code Changes

### Using the New Context Manager

**Option 1: Import from dedicated module (recommended)**

```python
from azure_search_context_manager import AzureSearchContextManager

context_manager = AzureSearchContextManager(max_working_tokens=100000)
```

**Option 2: Direct replacement in existing code**

The interface is **100% compatible** with the old ChromaDB version:

```python
# Same methods, same signatures
context_manager.add_chunk(chunk_id, content, metadata, embedding)
results = context_manager.retrieve_relevant_context(query, max_chunks=15)
```

### New Hybrid Search Features

**Basic search (vector + keyword):**
```python
results = context_manager.retrieve_relevant_context(
    query="motor control circuit",
    max_chunks=15,
    query_embedding=embedding  # Optional: pre-computed embedding
)
```

**Filtered search:**
```python
results = context_manager.retrieve_relevant_context(
    query="transformer specifications",
    max_chunks=10,
    filters={
        "diagram_type": "electrical",
        "page_numbers": [1, 2, 3]
    }
)
```

**Component-specific search:**
```python
results = context_manager.retrieve_relevant_context(
    query="wiring connections",
    filters={
        "components": ["M1", "T1", "SW1"]
    }
)
```

---

## Migration Strategies

### Strategy A: Clean Migration (Recommended)

1. **Backup existing data** (if needed)
2. **Create Azure Search index** (`python create_azure_search_index.py`)
3. **Update code** to use `AzureSearchContextManager`
4. **Reprocess documents** to populate Azure Search
5. **Remove ChromaDB** dependency

### Strategy B: Gradual Migration

1. Keep both systems temporarily
2. Write to both (ChromaDB + Azure Search)
3. Compare results during testing
4. Switch reads to Azure Search when validated
5. Remove ChromaDB after confidence

---

## Code Examples

### Example 1: Updating edisonpro.py

**Before (ChromaDB):**
```python
class DiagramAnalysisOrchestratorPro:
    def __init__(self, reasoning_effort: str = "high"):
        # ... other init code ...
        self.context_manager = ContextManagerPro(max_working_tokens=100000)
```

**After (Azure Search):**
```python
from azure_search_context_manager import AzureSearchContextManager

class DiagramAnalysisOrchestratorPro:
    def __init__(self, reasoning_effort: str = "high"):
        # ... other init code ...
        self.context_manager = AzureSearchContextManager(max_working_tokens=100000)
```

### Example 2: Adding Chunks

**No changes needed** - interface is identical:

```python
# Same code works with both ChromaDB and Azure Search
for chunk in chunks:
    embedding = await self._generate_embedding_pro(chunk['content'])
    
    self.context_manager.add_chunk(
        chunk['chunk_id'],
        chunk['content'],
        chunk['metadata'],
        embedding
    )
```

### Example 3: Retrieving Context

**Basic retrieval (same as before):**
```python
relevant_chunks = self.context_manager.retrieve_relevant_context(
    question, 
    max_chunks=15
)
```

**Advanced retrieval (new features):**
```python
relevant_chunks = self.context_manager.retrieve_relevant_context(
    question,
    max_chunks=15,
    query_embedding=query_embedding,  # Pre-computed for efficiency
    filters={
        "diagram_type": "electrical",
        "page_numbers": [1, 2, 3]
    }
)
```

---

## Testing

### Test Azure Search Connection

```bash
python azure_search_context_manager.py
```

Expected output:
```
🧪 Testing Azure Search configuration...
   Endpoint: https://your-service.search.windows.net
   Index: edison-diagrams
   ✅ Connection successful!
   📊 Index contains documents
```

### Test with Sample Document

```python
from azure_search_context_manager import AzureSearchContextManager
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChunkMetadata:
    chunk_id: str
    page_numbers: List[int]
    diagram_type: Optional[str] = None
    scale: Optional[str] = None
    reference_numbers: Optional[List[str]] = None
    components: Optional[List[str]] = None
    bounding_box: Optional[dict] = None
    dependencies: Optional[List[str]] = None

# Initialize
context_manager = AzureSearchContextManager()

# Add sample chunk
metadata = ChunkMetadata(
    chunk_id="test_1",
    page_numbers=[1],
    diagram_type="electrical",
    components=["M1", "T1"]
)

embedding = [0.1] * 1536  # Sample embedding

context_manager.add_chunk(
    "test_1",
    "Motor control circuit with transformer T1 and motor M1",
    metadata,
    embedding
)

# Search
results = context_manager.retrieve_relevant_context(
    "motor circuit",
    max_chunks=5
)

print(f"Found {len(results)} results")
```

---

## Benefits Over ChromaDB

| Feature | ChromaDB | Azure AI Search |
|---------|----------|-----------------|
| **Search Type** | Vector only | Hybrid (vector + keyword) |
| **Filtering** | Limited | Rich (metadata, arrays, ranges) |
| **Scalability** | Local limits | Cloud-scale (millions of docs) |
| **Dependencies** | Heavy (grpcio issues) | Lightweight SDK |
| **Production** | Not recommended | Enterprise-ready with SLA |
| **Semantic Ranking** | No | Yes (AI-powered) |
| **Cost** | Free (local) | ~$75-250/month |
| **Setup** | Complex | Simple (managed service) |

---

## Troubleshooting

### Issue: "Azure Search credentials not configured"

**Solution:** Add to `.env`:
```bash
AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-api-key
AZURE_SEARCH_INDEX_NAME=edison-diagrams
```

### Issue: "Failed to initialize Azure Search client"

**Solutions:**
1. Verify endpoint format: `https://your-service.search.windows.net`
2. Check API key is correct (Admin Key, not Query Key for write operations)
3. Ensure index exists: `python create_azure_search_index.py`

### Issue: "Index not found"

**Solution:** Create the index:
```bash
python create_azure_search_index.py
```

### Issue: "Embedding dimension mismatch"

**Solution:** Ensure you're using `text-embedding-ada-002` (1536 dims):
```bash
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

---

## Performance Tips

### 1. Pre-compute Query Embeddings

```python
# Generate once
query_embedding = await self._generate_embedding_pro(query)

# Reuse for multiple searches
results = context_manager.retrieve_relevant_context(
    query,
    query_embedding=query_embedding
)
```

### 2. Use Filters for Efficiency

```python
# Narrow search space with filters
results = context_manager.retrieve_relevant_context(
    query,
    filters={"diagram_type": "electrical"}  # Search only electrical diagrams
)
```

### 3. Batch Document Uploads

```python
# Upload multiple documents at once (future enhancement)
documents = [doc1, doc2, doc3, ...]
search_client.upload_documents(documents=documents)
```

---

## Next Steps

1. ✅ Create Azure Search index
2. ✅ Update environment variables
3. ✅ Install Azure Search SDK
4. ✅ Update code to use `AzureSearchContextManager`
5. ✅ Test with sample documents
6. ✅ Reprocess existing PDFs to populate index
7. ✅ Remove ChromaDB dependency

---

## Support

- **Azure Search Docs**: https://learn.microsoft.com/azure/search/
- **Python SDK**: https://learn.microsoft.com/python/api/azure-search-documents/
- **Pricing**: https://azure.microsoft.com/pricing/details/search/

---

## Summary

The new Azure Search integration provides:

- **Same interface**: Drop-in replacement, no API changes
- **Better search**: Hybrid (vector + keyword) with semantic ranking
- **Production-ready**: Managed service with enterprise features
- **More features**: Filtering, faceting, suggestions
- **Simpler setup**: No local database files or complex dependencies

Simply update your imports and configuration - the rest works the same!
