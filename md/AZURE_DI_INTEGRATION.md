# Azure Document Intelligence Integration

## Overview

EDISON PRO now integrates **Azure Document Intelligence** (formerly Form Recognizer) as the primary text extraction method for engineering diagrams. This provides superior OCR, table extraction, and layout analysis capabilities.

## What's New

### Enhanced Extraction Pipeline

**3-Tier Priority System:**

1. **🥇 Azure Document Intelligence** (Primary - Best Quality)
   - Uses `prebuilt-layout` model
   - Superior OCR for complex engineering text
   - Table extraction with cell-level detail
   - Key-value pairs (title blocks, form fields)
   - Layout analysis with confidence scores
   - Bounding boxes for spatial understanding

2. **🥈 MarkItDown OCR** (Fallback #1)
   - Basic OCR capabilities
   - Used if Azure DI unavailable or low confidence

3. **🥉 PyMuPDF Direct** (Fallback #2)
   - Native text extraction from PDFs
   - Last resort for text-based PDFs

### Key Benefits

✅ **Superior OCR Quality**: Best-in-class text extraction from scanned engineering diagrams  
✅ **Table Intelligence**: Equipment schedules, motor lists, panel schedules properly extracted  
✅ **Title Block Parsing**: Automatic extraction of drawing metadata (numbers, dates, revisions)  
✅ **Structured Output**: JSON format with confidence scores and spatial coordinates  
✅ **Cost Effective**: Optimized for engineering diagrams with high accuracy  
✅ **Hybrid Analysis**: Azure DI extracts structure, o3-pro provides reasoning  

## Setup Instructions

### 1. Create Azure Resource

```bash
# Create Document Intelligence resource in Azure Portal
# Navigate to: https://portal.azure.com
# Search for: "Document Intelligence" or "Form Recognizer"
# Create new resource with F0 (free) or S0 (standard) tier
```

### 2. Get Credentials

From Azure Portal → Your Resource → Keys and Endpoint:
- Copy **Endpoint** (e.g., `https://your-resource.cognitiveservices.azure.com/`)
- Copy **Key 1** or **Key 2**

### 3. Update .env File

Add to your `.env` file:

```env
# Azure Document Intelligence Configuration
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-api-key-here
```

### 4. Install Package

```bash
pip install azure-ai-documentintelligence==1.0.2
```

Or use the requirements.txt:

```bash
pip install -r requirements.txt
```

### 5. Test Integration

```bash
python test_azure_di.py
```

Expected output:
```
✅ ALL TESTS PASSED!
💡 Azure Document Intelligence is ready to use in EDISON PRO
```

## Usage in EDISON PRO

### Automatic Integration

Azure Document Intelligence is **automatically used** when configured. No code changes needed!

```bash
# Just run EDISON PRO as usual
python edisonpro.py --images ./diagrams --interactive
```

### What Happens During Analysis

**Phase 1: Document Preprocessing**

```
📄 Processing image_001.jpg...
   📊 Azure Document Intelligence: Analyzing layout...
   ✅ Azure DI: Extracted 2,847 chars, 3 tables, 12 key-value pairs
   📈 Confidence: 94.2%
   📝 Saved: image_001_azure_di.json
```

**Extracted Data Includes:**

1. **Text Content**: All visible text with reading order
2. **Tables**: 
   ```json
   {
     "table_id": "table_1",
     "row_count": 5,
     "column_count": 4,
     "cells": [
       {"row_index": 0, "column_index": 0, "content": "Equipment", "confidence": 0.98},
       {"row_index": 0, "column_index": 1, "content": "Voltage", "confidence": 0.97}
     ]
   }
   ```

3. **Key-Value Pairs** (Title Block):
   ```json
   {
     "key": "Drawing Number",
     "value": "E-101",
     "confidence": 0.96
   }
   ```

4. **Confidence Scores**: Per-line and per-cell confidence metrics

### Intermediate Files

Azure DI results are saved for debugging:

```
intermediate_files_diagram_20250107_143022/
├── image_001_azure_di.json          # Full structured output
├── image_001_extracted_text.txt     # Formatted text
└── image_001_structure_analysis.json # o3-pro analysis
```

## Architecture

### Hybrid Extraction + Reasoning

```
┌─────────────────────────────────────────────────────────────┐
│                    Input: Engineering Diagram                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│      PHASE 1A: Azure Document Intelligence Extraction       │
│      • prebuilt-layout model                                 │
│      • Text blocks with reading order                        │
│      • Tables with cell structure                            │
│      • Key-value pairs (title blocks)                        │
│      • Confidence scores & bounding boxes                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│         Structured Output (JSON + Formatted Text)            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│       PHASE 1B: o3-pro Enhanced Reasoning (EXISTING)         │
│       • Receives: Original Image + ADI Structured Output     │
│       • Reasons over: Visual elements + Extracted text       │
│       • Identifies: Components, connections, relationships   │
│       • Validates: Technical specifications, standards       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              Complete Analysis Result                        │
│              • Structure (from ADI)                          │
│              • Semantics (from o3-pro)                       │
│              • Engineering Intelligence (from both)          │
└─────────────────────────────────────────────────────────────┘
```

## API Details

### DocumentIntelligenceClient

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

client = DocumentIntelligenceClient(
    endpoint="https://your-resource.cognitiveservices.azure.com/",
    credential=AzureKeyCredential("your-api-key")
)

# Analyze document
with open("diagram.png", "rb") as f:
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=f.read()
    )
    result = poller.result()

# Access results
for page in result.pages:
    for line in page.lines:
        print(f"Text: {line.content}, Confidence: {line.confidence}")

for table in result.tables:
    print(f"Table: {table.row_count}x{table.column_count}")
    for cell in table.cells:
        print(f"  [{cell.row_index},{cell.column_index}]: {cell.content}")
```

### Supported Models

- **prebuilt-layout**: ✅ Used by EDISON PRO (best for diagrams)
- **prebuilt-read**: Text extraction only
- **prebuilt-document**: General documents with key-value pairs
- **prebuilt-invoice**, **prebuilt-receipt**: Specific document types

## Pricing

### Azure Document Intelligence

**Free Tier (F0):**
- 500 pages/month free
- Perfect for testing and small projects

**Standard Tier (S0):**
- $1.50 per 1,000 pages (Layout model)
- Pay-as-you-go pricing
- See: https://azure.microsoft.com/pricing/details/ai-document-intelligence/

### Cost Comparison

For a typical engineering drawing analysis:

| Method | Cost per Page | Quality | Speed |
|--------|---------------|---------|-------|
| Azure DI (Layout) | ~$0.0015 | ⭐⭐⭐⭐⭐ | Fast |
| MarkItDown OCR | Free | ⭐⭐⭐ | Medium |
| o3-pro Visual Only | ~$0.10+ | ⭐⭐⭐⭐ | Slow |
| **Hybrid (ADI + o3-pro)** | **~$0.10** | **⭐⭐⭐⭐⭐** | **Optimal** |

**Why Hybrid is Best:**
- Azure DI: Cheap, fast text extraction
- o3-pro: Expensive but powerful reasoning
- Together: Best quality at reasonable cost

## Troubleshooting

### Error: "SDK not available"

```
⚠️ Warning: Azure Document Intelligence SDK not available
```

**Solution:**
```bash
pip install azure-ai-documentintelligence==1.0.2
```

### Error: "Credentials not configured"

```
⚠️ Azure Document Intelligence credentials not configured
```

**Solution:** Add to `.env`:
```env
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-api-key
```

### Error: "Initialization failed"

**Common causes:**
1. Wrong endpoint format (should end with `.cognitiveservices.azure.com/`)
2. Invalid API key
3. Resource not deployed

**Solution:** Verify credentials in Azure Portal

### Low Confidence Results

If confidence < 30%, EDISON PRO falls back to MarkItDown OCR.

**Reasons for low confidence:**
- Very poor scan quality
- Handwritten text
- Unusual fonts or symbols
- Heavily degraded images

**Solutions:**
- Improve source image quality
- Use higher resolution scans
- Pre-process images (contrast, brightness)

## Performance Metrics

### Typical Performance

| Metric | Value |
|--------|-------|
| Processing Time | 2-5 seconds per page |
| Text Extraction Accuracy | 95-99% |
| Table Detection Rate | 90-95% |
| Key-Value Pair Accuracy | 85-95% |
| Confidence Threshold | 30% (for fallback) |

### Best Use Cases

✅ **Excellent for:**
- Printed engineering drawings
- CAD plot outputs
- Typed specifications
- Equipment schedules
- Panel layouts
- Control schematics

⚠️ **Limitations:**
- Handwritten notes (lower accuracy)
- Very low resolution scans
- Severely degraded documents
- Non-standard fonts or symbols

## References

- [Azure Document Intelligence Documentation](https://learn.microsoft.com/azure/ai-services/document-intelligence/)
- [Python SDK Documentation](https://pypi.org/project/azure-ai-documentintelligence/)
- [API Reference](https://learn.microsoft.com/python/api/overview/azure/ai-documentintelligence-readme)
- [Pricing](https://azure.microsoft.com/pricing/details/ai-document-intelligence/)

## Support

For issues or questions:
1. Check this documentation
2. Run `python test_azure_di.py` to validate setup
3. Review intermediate files for debugging
4. Check Azure Portal for resource status

---

**Version:** 1.0  
**Last Updated:** October 7, 2025  
**Author:** Srikanth Bhakthan - Microsoft
