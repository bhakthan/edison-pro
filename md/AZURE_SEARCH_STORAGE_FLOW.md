# Azure AI Search Storage Flow - What Gets Stored & When

## 📊 Data Flow Overview

```
PDF/Images → Stage 1 → Stage 2 → Stage 3 → Azure Search
              Extract   Analyze   Index     (Storage)
```

## Stage-by-Stage Breakdown

### **Stage 1: Document Preprocessing** 
📄 **What Happens:**
- Extracts pages from PDF or loads images from folder
- Converts pages to images (if PDF)
- Extracts text using PyMuPDF (for PDFs)
- Optional OCR with MarkItDown

📝 **Intermediate Files Created:**
- `00_complete_pymupdf_extraction.txt` - All extracted text
- `01_extraction_summary.txt` - Extraction statistics
- `page_XXX_image.png` - Individual page images
- `page_XXX_extracted_text.txt` - Per-page text

❌ **NOT stored in Azure Search yet**

---

### **Stage 2: Structure Analysis & Visual Extraction**
🧠 **What Happens:**
- **o3-pro analyzes each page** with Responses API
- Identifies diagram type, components, zones, references
- Extracts visual elements (symbols, lines, connections)
- Detects technical standards, complexity, dependencies
- Performs smart chunking based on diagram boundaries

📝 **Intermediate Files Created:**
- `page_XXX_structure_analysis.json` - **Full o3-pro analysis results**
- `page_XXX_structure_summary.txt` - Human-readable summary
- `visual_elements_XXX_analysis.json` - Extracted visual elements
- `02_chunking_summary.txt` - Chunking decisions
- `chunk_XXX_content.txt` - Individual chunk content

**Example structure_analysis.json:**
```json
{
  "diagram_type": "electrical_single_line",
  "confidence_score": 0.95,
  "reasoning_summary": "This is a single-line electrical diagram...",
  "title_block": {
    "drawing_number": "E-001",
    "scale": "1:100",
    "revision": "Rev A"
  },
  "components": [
    {"id": "M1", "type": "motor", "confidence": 0.98},
    {"id": "CB1", "type": "circuit_breaker", "confidence": 0.92}
  ],
  "zones": ["power_distribution", "motor_control"],
  "references": ["E-002", "E-003"],
  "dependencies": ["power_supply_diagram"],
  "technical_standards": ["IEEE C37.2", "ANSI/NFPA 70"],
  "complexity_assessment": "moderate",
  "expert_insights": [
    "Motor protection scheme follows NFPA 70 requirements",
    "Circuit breaker rating appropriate for motor load"
  ]
}
```

❌ **NOT stored in Azure Search yet**
✅ **But saved to intermediate files for inspection**

---

### **Stage 3: Context Index Building** ⭐
💾 **What Gets Stored in Azure Search:**

For each chunk, the following document is uploaded:

```json
{
  "chunk_id": "pro_chunk_001",
  "content": "Full text content from the chunk (diagram text, labels, etc.)",
  "content_vector": [0.123, 0.456, ...],  // 1536-dim embedding
  
  // Metadata extracted from structure_analysis.json
  "page_numbers": [1, 2],
  "diagram_type": "electrical_single_line",
  "scale": "1:100",
  "reference_numbers": ["E-002", "E-003"],
  "components": ["M1", "CB1", "T1", "SW1"],
  "dependencies": ["power_supply_diagram"],
  "source_file": "electrical_manual.pdf",
  "timestamp": "2025-10-03T12:34:56Z"
}
```

**What's Included:**
- ✅ **chunk_id**: Unique identifier
- ✅ **content**: Extracted text from the chunk
- ✅ **content_vector**: 1536-dim embedding for semantic search
- ✅ **page_numbers**: Which pages this chunk covers
- ✅ **diagram_type**: From o3-pro analysis
- ✅ **scale**: From title block
- ✅ **reference_numbers**: Cross-references to other diagrams
- ✅ **components**: List of component IDs (M1, CB1, etc.)
- ✅ **dependencies**: Related diagrams/sections
- ✅ **source_file**: Original PDF/image filename
- ✅ **timestamp**: When uploaded

**What's NOT Included:**
- ❌ **Full structure_analysis.json** (too large)
- ❌ **visual_elements details** (coordinates, properties)
- ❌ **expert_insights** (qualitative analysis)
- ❌ **confidence_score** (per-component confidence)
- ❌ **reasoning_summary** (o3-pro reasoning)
- ❌ **technical_standards** (IEEE, ANSI references)
- ❌ **complexity_assessment** (simple/moderate/complex)
- ❌ **zones information** (diagram zones/areas)
- ❌ **title_block details** (drawing number, revision)

---

## 🔍 What's Available Where

| Information | Azure Search | Intermediate Files | In-Memory (chunk_store) |
|-------------|--------------|-------------------|------------------------|
| **Chunk Text** | ✅ | ✅ | ✅ |
| **Embeddings** | ✅ | ❌ | ✅ |
| **Page Numbers** | ✅ | ✅ | ✅ |
| **Diagram Type** | ✅ | ✅ | ✅ |
| **Components List** | ✅ (IDs only) | ✅ (full details) | ✅ |
| **Dependencies** | ✅ | ✅ | ✅ |
| **Scale** | ✅ | ✅ | ✅ |
| **Reference Numbers** | ✅ | ✅ | ✅ |
| **o3-pro Reasoning** | ❌ | ✅ | ❌ |
| **Confidence Scores** | ❌ | ✅ | ❌ |
| **Expert Insights** | ❌ | ✅ | ❌ |
| **Visual Elements** | ❌ | ✅ | ✅ (in memory) |
| **Technical Standards** | ❌ | ✅ | ❌ |
| **Complexity** | ❌ | ✅ | ❌ |
| **Title Block** | ⚠️ (scale only) | ✅ | ✅ |

---

## 💡 Why This Design?

### **Azure Search Stores:**
- **Searchable content**: Text for keyword search
- **Vectors**: For semantic similarity
- **Key metadata**: For filtering (diagram type, pages, components)

**Purpose:** Fast hybrid search (vector + keyword) for Q&A

### **Intermediate Files Store:**
- **Full o3-pro analysis**: Complete structure_analysis.json
- **Reasoning & insights**: Why o3-pro made decisions
- **Detailed component info**: With confidence scores
- **Visual element details**: Coordinates, properties

**Purpose:** Inspection, debugging, audit trail

### **In-Memory chunk_store:**
- **Full chunk data**: Content + metadata + token count
- **Quick access**: No API calls during retrieval
- **Visual elements**: For synthesis agent

**Purpose:** Fast context retrieval during interactive Q&A

---

## 🚀 Retrieval Flow (Interactive Q&A)

```
User Question
     ↓
[Generate Query Embedding]
     ↓
[Azure Search Hybrid Query]
   • Vector search (semantic similarity)
   • Keyword search (BM25)
   • Metadata filters (diagram_type, pages, etc.)
     ↓
[Get chunk_ids from Azure Search]
     ↓
[Retrieve full chunks from chunk_store]
   • Includes visual elements
   • Includes full metadata
     ↓
[Pass to o3-pro for Answer]
```

**Example:**
```
You: "What's the motor voltage rating on page 5?"

1. Generate embedding for query
2. Azure Search finds relevant chunks:
   - Vector: Semantic match for "motor voltage rating"
   - Keyword: Matches "motor", "voltage"
   - Filter: page_numbers contains 5
3. Returns: chunk_ids = ["pro_chunk_003", "pro_chunk_004"]
4. Retrieve from chunk_store:
   - Full text content
   - Visual elements (motor symbols, voltage labels)
   - Component details (M1, M2, etc.)
5. Send to o3-pro: "Based on these chunks, answer..."
```

---

## 📌 Key Insights

### **Why Not Store Everything in Azure Search?**

1. **Cost**: Azure Search charges by document size
   - Storing full structure_analysis.json would be expensive
   - 1536-dim vectors are already ~6KB per chunk

2. **Search Performance**: 
   - Only store searchable/filterable fields
   - Complex nested JSON slows down queries

3. **Query Relevance**:
   - Expert insights don't help with search ranking
   - Reasoning summaries are for humans, not search algorithms

4. **Hybrid Approach is Best**:
   - Azure Search: Fast retrieval by content/metadata
   - chunk_store: Full context for answer generation
   - Intermediate files: Audit trail and debugging

### **What If You Need Full Analysis Results?**

**Option 1:** Read intermediate files
```python
with open("page_001_structure_analysis.json") as f:
    full_analysis = json.load(f)
```

**Option 2:** Store in chunk_store (already done!)
```python
chunk = context_manager.chunk_store["pro_chunk_001"]
metadata = chunk["metadata"]  # ChunkMetadata object
# Has: diagram_type, components, dependencies, etc.
```

**Option 3:** Add to Azure Search schema (if needed)
```python
# Extend the document structure
document = {
    # ... existing fields ...
    "reasoning_summary": structure["reasoning_summary"],
    "expert_insights": structure["expert_insights"],
    "technical_standards": structure["technical_standards"],
    # ... etc ...
}
```

---

## 🎯 Summary

| Stage | What Happens | Stored in Azure Search? |
|-------|--------------|------------------------|
| **Stage 1: Extract** | PDF → Images, Text | ❌ No |
| **Stage 2: Analyze** | o3-pro → structure_analysis.json | ❌ No (saved to files) |
| **Stage 3: Index** | Chunks → Embeddings → Metadata | ✅ **YES** |

**What's in Azure Search:**
- Chunk text (searchable)
- 1536-dim vectors (semantic search)
- Key metadata: diagram_type, pages, components, dependencies, scale, references

**What's NOT in Azure Search:**
- Full o3-pro analysis results
- Expert insights
- Confidence scores
- Reasoning summaries
- Visual element coordinates
- Technical standards
- Complexity assessments

**Why:**
- Azure Search = Fast hybrid search
- Intermediate files = Complete analysis audit trail
- chunk_store = Full context for answer generation

**Best of all worlds!** 🚀
