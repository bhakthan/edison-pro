# Azure AI Search Migration Checklist

## ✅ Setup Checklist (Do First)

### Step 1: Azure Search Configuration
- [ ] Add to `.env` file:
  ```bash
  AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
  AZURE_SEARCH_API_KEY=your-api-key
  AZURE_SEARCH_INDEX_NAME=edison-diagrams
  ```

### Step 2: Create Index
- [ ] Run: `python create_azure_search_index.py`
- [ ] Verify success message: "✅ Index 'edison-diagrams' created successfully!"

### Step 3: Install Dependencies
- [ ] Run: `pip install azure-search-documents==11.6.0b4`
- [ ] Test: `python azure_search_context_manager.py`

### Step 4: Test Connection
- [ ] Run example: `python example_azure_search_migration.py`
- [ ] Verify all tests pass

---

## 🔧 Code Update Checklist

### Update edisonpro.py

**Option 1: Direct Import Update** ✅ Recommended

Find this line (around line 1860):
```python
self.context_manager = ContextManagerPro(max_working_tokens=100000)
```

Replace with:
```python
from azure_search_context_manager import AzureSearchContextManager
self.context_manager = AzureSearchContextManager(max_working_tokens=100000)
```

**OR Option 2: Keep Class Definition, Change Backend**

At the top of `edisonpro.py`, add:
```python
# Use Azure Search instead of ChromaDB
from azure_search_context_manager import AzureSearchContextManager as ContextManagerPro
```

Then remove or comment out the old `ContextManagerPro` class definition.

### Update edison.py (if exists)

Same changes as above, but replace `ContextManager` instead of `ContextManagerPro`.

---

## 🧪 Testing Checklist

### Basic Tests
- [ ] Connection test: `python azure_search_context_manager.py`
- [ ] Example test: `python example_azure_search_migration.py`

### Integration Tests
- [ ] Run EDISON PRO with sample PDF:
  ```bash
  python edisonpro.py --pdf sample.pdf --interactive
  ```
- [ ] Ask questions in interactive mode
- [ ] Verify search results quality

### Feature Tests
- [ ] Test basic search (no filters)
- [ ] Test filtered search by `diagram_type`
- [ ] Test filtered search by `page_numbers`
- [ ] Test filtered search by `components`
- [ ] Test combined filters

---

## 📊 Validation Checklist

### Search Quality
- [ ] Compare results with old ChromaDB version (if available)
- [ ] Verify hybrid search finds both semantic and keyword matches
- [ ] Test edge cases (typos, partial matches)

### Performance
- [ ] Measure search latency (should be <500ms)
- [ ] Check Azure Search metrics in portal
- [ ] Monitor token usage

### Error Handling
- [ ] Test with invalid credentials (should fail gracefully)
- [ ] Test with missing index (should show helpful error)
- [ ] Test with network issues (should fall back to cache)

---

## 🧹 Cleanup Checklist (Optional)

### After Successful Migration
- [ ] Remove ChromaDB from code (if no longer needed)
- [ ] Remove ChromaDB from requirements.txt
- [ ] Uninstall: `pip uninstall chromadb -y`
- [ ] Delete old ChromaDB data files
- [ ] Update documentation to reflect Azure Search

---

## 📋 Quick Reference

### Commands to Run

```bash
# 1. Create index
python create_azure_search_index.py

# 2. Test connection
python azure_search_context_manager.py

# 3. Test functionality
python example_azure_search_migration.py

# 4. Install dependencies
pip install azure-search-documents==11.6.0b4

# 5. Uninstall ChromaDB (optional)
pip uninstall chromadb -y

# 6. Run EDISON PRO
python edisonpro.py --pdf your_document.pdf --interactive
```

### Environment Variables Required

```bash
# Azure Search (NEW - add these)
AZURE_SEARCH_ENDPOINT=https://your-service.search.windows.net
AZURE_SEARCH_API_KEY=your-api-key
AZURE_SEARCH_INDEX_NAME=edison-diagrams

# Azure OpenAI (existing)
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Azure OpenAI Pro (existing)
AZURE_OPENAI_PRO_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_PRO_DEPLOYMENT_NAME=o3-pro
```

---

## 🆘 Troubleshooting

### Common Errors

**"Azure Search credentials not configured"**
→ Add AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY to `.env`

**"Index not found"**
→ Run `python create_azure_search_index.py`

**"Permission denied"**
→ Use Admin API Key (not Query Key)

**"Dimension mismatch"**
→ Ensure using text-embedding-ada-002 (1536 dims)

### Getting Help

1. Check `AZURE_SEARCH_INTEGRATION.md` for detailed guide
2. Check `AZURE_SEARCH_MIGRATION_SUMMARY.md` for overview
3. Run `python azure_search_context_manager.py` to test config
4. Review `example_azure_search_migration.py` for working code

---

## ✅ Success Criteria

You've successfully migrated when:

- ✅ `python azure_search_context_manager.py` shows "Connection successful!"
- ✅ `python example_azure_search_migration.py` completes without errors
- ✅ `python edisonpro.py --pdf sample.pdf` processes document
- ✅ Interactive Q&A returns relevant results
- ✅ Filters work correctly (diagram_type, pages, components)
- ✅ Search results quality meets expectations

---

## 🎉 You're Done!

Once all checkboxes above are complete, you have:

✅ Production-ready hybrid search (vector + keyword)  
✅ Advanced filtering capabilities  
✅ Managed service with 99.9% SLA  
✅ No local database dependencies  
✅ Same code interface (no refactoring needed)  

**Next:** Start processing your engineering diagrams with enhanced search capabilities!
