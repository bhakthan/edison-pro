"""
Author: Srikanth Bhakthan - Microsoft
EDISON PRO - Advanced Multi-Agent System for Engineering Diagram Analysis
Enhanced version using Azure OpenAI o3-pro model with Responses API
Optimized for the latest o3-pro reasoning capabilities with Azure AI Search

USAGE EXAMPLES:

1. AUTO-PLANNING MODE (Recommended - System Detects Discipline):
   python edisonpro.py --images ./diagram_images --interactive
   # System automatically detects: civil+electrical, mechanical, P&ID, etc.

2. Manual Domain Specification:
   python edisonpro.py --images ./diagrams --domain electrical --no-auto-plan --interactive
   python edisonpro.py --pdf manual.pdf --domain utility --interactive

3. Hybrid Domain Analysis:
   python edisonpro.py --images ./utility_plans --domain civil,electrical --interactive
   python edisonpro.py --pdf plans.pdf --domain utility --interactive  # Preset for civil+electrical

4. PDF Analysis with Auto-Planning:
   python edisonpro.py --pdf electrical_manual.pdf --interactive

5. Different Reasoning Levels:
   python edisonpro.py --images ./scans --reasoning-effort maximum --interactive
   python edisonpro.py --pdf diagrams.pdf --reasoning-effort medium --interactive

6. Domain Presets:
   --domain utility          # Civil + Electrical (underground distribution, plan-and-profile)
   --domain mep             # Mechanical + Electrical + P&ID (building systems)
   --domain structural-civil # Structural + Civil (foundations, site work)
   --domain process         # Mechanical + P&ID (process engineering)

FEATURES:
- 🧠 Intelligent Planning Agent (auto-detects discipline, complexity, key features)
- 📄 PDF and image folder input support
- 🔍 Azure AI Search with hybrid search (vector + keyword)
- 💡 o3-pro advanced reasoning capabilities
- 🎯 Smart chunking with metadata
- 💬 Interactive Q&A mode
- 🌐 Hybrid domain support (electrical, mechanical, P&ID, civil, structural, general)
- ⚡ Reasoning effort control (low, medium, high, maximum)
- 📊 Automatic analysis optimization based on detected characteristics
"""

import os
import json
import base64
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from collections import defaultdict, Counter
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Awaitable
import threading
from functools import partial
from pathlib import Path
import datetime
from datetime import timezone
import glob


PLANNING_HISTORY_FILE = Path("planning_history.json")

# Load environment variables first (before other imports)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    print("⚠️  python-dotenv not installed. Please set environment variables manually.")
    def load_dotenv(**kwargs):
        pass
except Exception as e:
    print(f"⚠️  Warning: Could not parse .env file: {e}")
    print("   Continuing with system environment variables...")
    def load_dotenv(**kwargs):
        pass

# External dependencies (install via pip):
# pip install openai pymupdf pillow numpy azure-search-documents networkx tiktoken python-dotenv

# Core imports (required)
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    print("❌ Error: PyMuPDF (fitz) is required. Install with: pip install pymupdf")
    HAS_PYMUPDF = False

try:
    from PIL import Image
    import numpy as np
    HAS_PIL_NUMPY = True
except ImportError:
    print("❌ Error: PIL and numpy are required. Install with: pip install pillow numpy")
    HAS_PIL_NUMPY = False

try:
    from openai import OpenAI, AzureOpenAI  # AzureOpenAI used for Responses API on Azure
    HAS_OPENAI = True
except ImportError:
    print("❌ Error: OpenAI is required. Install with: pip install openai")
    HAS_OPENAI = False

# Azure AI Search imports
try:
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    HAS_AZURE_SEARCH = True
except ImportError:
    print("⚠️  Warning: Azure Search SDK not available. Install with: pip install azure-search-documents")
    print("   Using in-memory fallback for vector storage.")
    HAS_AZURE_SEARCH = False

# Azure Document Intelligence imports
try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    HAS_AZURE_DI = True
except ImportError:
    print("⚠️  Warning: Azure Document Intelligence SDK not available. Install with: pip install azure-ai-documentintelligence")
    print("   Using fallback extraction methods.")
    HAS_AZURE_DI = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    print("⚠️  Warning: NetworkX not available. Install with: pip install networkx")
    print("   Using simple fallback for graph operations.")
    HAS_NETWORKX = False
    nx = None

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    print("⚠️  Warning: tiktoken not available. Install with: pip install tiktoken")
    print("   Using character-based token estimation.")
    HAS_TIKTOKEN = False
    tiktoken = None

try:
    from markitdown import MarkItDown
    HAS_MARKITDOWN = True
except ImportError:
    print("⚠️  Warning: MarkItDown not available. Install with: pip install markitdown")
    print("   PyMuPDF will be the only extraction method.")
    HAS_MARKITDOWN = False
    MarkItDown = None

try:
    from agents.pdf_router import PdfProcessingRouter
except ImportError:
    PdfProcessingRouter = None

# Blob storage imports (optional)
try:
    from blob_storage import BlobStorageManager, create_blob_manager_from_env
    HAS_BLOB_STORAGE = True
except ImportError:
    print("⚠️  Warning: blob_storage.py not found or azure-storage-blob not available.")
    print("   Install with: pip install azure-storage-blob azure-identity")
    print("   Blob storage features will be disabled.")
    HAS_BLOB_STORAGE = False

# Check critical dependencies
if not (HAS_PYMUPDF and HAS_PIL_NUMPY and HAS_OPENAI):
    print("\n❌ Critical dependencies missing. Please install required packages:")
    print("   pip install openai pymupdf pillow numpy")
    exit(1)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# ============================================================================
# ADVANCED PROMPTING CONSTRAINTS
# Engineering-domain negative prompting injected into every LLM call to
# reduce hallucination of absent standards, components, and ratings.
# ============================================================================
ENGINEERING_CONSTRAINTS = """
CONSTRAINTS — STRICTLY FOLLOW:
- DO NOT cite NEC / ASME / ISO / NFPA / OSHA section numbers you cannot directly trace to the provided context
- DO NOT assume component ratings (voltage, current, pressure, temperature) that are not explicitly stated in the diagram chunks
- DO NOT confuse IEC and NEMA equipment naming conventions when both are plausible
- DO NOT generalise findings from one diagram section to the entire system without explicit cross-reference evidence
- DO NOT state "appears to comply" without identifying the specific standard clause and its version year
- DO NOT assign confidence > 0.85 when fewer than 3 independent evidence chunks support the claim
- IF UNSURE: state explicitly "insufficient diagram data to determine [X]" rather than speculating
"""


async def safe_responses_api_call(client, **params):
    """Enhanced Azure OpenAI Responses API call with detailed error diagnostics and usage tracking"""
    try:
        # Run synchronous API call in executor to avoid blocking
        # Note: client.responses.create() is synchronous, not async
        loop = asyncio.get_event_loop()
        
        # Get reasoning effort for timeout estimation
        reasoning_effort = params.get('reasoning', {}).get('effort', 'medium')
        timeout_map = {'low': 90, 'medium': 300, 'high': 900, 'maximum': 1800}  # seconds - maximum can take 30min
        timeout = timeout_map.get(reasoning_effort, 1800)  # default to max for safety
        
        print(f"   🔄 Making o3-pro API call (reasoning: {reasoning_effort}, timeout: {timeout}s)...")
        
        def make_api_call():
            return client.responses.create(**params)
        
        response = await asyncio.wait_for(
            loop.run_in_executor(None, make_api_call),
            timeout=timeout
        )
        
        # Log token usage for monitoring
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            reasoning_tokens = 0
            if hasattr(usage, 'output_tokens_details') and usage.output_tokens_details:
                reasoning_tokens = usage.output_tokens_details.reasoning_tokens
            
            # Only log if reasoning tokens were used (indicates o3-pro reasoning)
            if reasoning_tokens > 0:
                print(f"   💡 o3-pro reasoning: {reasoning_tokens} tokens used")
        
        return response
        
    except asyncio.TimeoutError:
        reasoning_effort = params.get('reasoning', {}).get('effort', 'unknown')
        print(f"⏱️  TIMEOUT ERROR:")
        print(f"   Reasoning effort: {reasoning_effort}")
        print(f"   Cause: API call took too long (may be normal for high reasoning)")
        print(f"   Solution: Try using lower reasoning effort or wait longer")
        raise
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Categorize the error type
        if "content filter" in error_msg or "content policy" in error_msg:
            print("🚫 CONTENT FILTER DETECTED:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: Content flagged by Azure OpenAI safety filters")
            print("   Solution: Try rephrasing input or use different content")
        elif "rate limit" in error_msg or "quota" in error_msg:
            print("⏱️  RATE LIMIT EXCEEDED:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: API rate limits or quota exceeded")
            print("   Solution: Wait and retry, or check quota limits")
        elif "unauthorized" in error_msg or "authentication" in error_msg:
            print("🔑 AUTHENTICATION ERROR:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: Invalid API key or endpoint configuration")
            print("   Solution: Check AZURE_OPENAI_API_KEY and AZURE_OPENAI_PRO_ENDPOINT")
        elif "not found" in error_msg or "404" in error_msg:
            print("🚨 DEPLOYMENT/MODEL NOT FOUND:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: o3-pro model deployment not found or not accessible")
            print("   Solutions:")
            print("     1. Verify AZURE_OPENAI_PRO_DEPLOYMENT_NAME is correct")
            print("     2. Check if o3-pro model is deployed in your Azure OpenAI resource")
            print("     3. Ensure the deployment name matches exactly (case-sensitive)")
            print("     4. Verify your Azure OpenAI resource has o3-pro model access")
            print("     5. Try using a different model deployment if o3-pro is not available")
        elif "model" in error_msg and "not available" in error_msg:
            print("🙅 MODEL NOT AVAILABLE:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: Requested model not available in this region/resource")
            print("   Solution: Try using a different model or check model availability")
        elif "insufficient quota" in error_msg or "quota exceeded" in error_msg:
            print("📈 QUOTA EXCEEDED:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: Token quota exceeded for current period")
            print("   Solution: Wait for quota reset or upgrade quota limits")
        else:
            print("❌ API CALL FAILED:")
            print(f"   Error: {str(e)[:200]}")
            print("   Cause: Unknown API error (not extraction related)")
            print("   Solution: Check Azure OpenAI service status")
        
        # Re-raise for proper handling
        raise e


def create_intermediate_dir(pdf_path: str) -> Path:
    """Create intermediate files directory for debugging"""
    pdf_name = Path(pdf_path).stem
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    intermediate_dir = Path(f"intermediate_files_{pdf_name}_{timestamp}")
    intermediate_dir.mkdir(exist_ok=True)
    return intermediate_dir


def save_intermediate_file(content: str, filename: str, intermediate_dir: Path, description: str = ""):
    """Save intermediate processing files for debugging"""
    try:
        file_path = intermediate_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📝 Saved {description}: {file_path}")
        return file_path
    except Exception as e:
        print(f"⚠️  Failed to save {filename}: {e}")
        return None


def save_intermediate_json(data: dict, filename: str, intermediate_dir: Path, description: str = ""):
    """Save intermediate JSON data for debugging"""
    try:
        file_path = intermediate_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"📊 Saved {description}: {file_path}")
        return file_path
    except Exception as e:
        print(f"⚠️  Failed to save {filename}: {e}")
        return None


def save_intermediate_image(image_base64: str, filename: str, intermediate_dir: Path, description: str = ""):
    """Save intermediate image files for debugging"""
    try:
        file_path = intermediate_dir / filename
        image_data = base64.b64decode(image_base64)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        print(f"🖼️  Saved {description}: {file_path}")
        return file_path
    except Exception as e:
        print(f"⚠️  Failed to save {filename}: {e}")
        return None


def get_supported_image_files(input_folder: str) -> List[str]:
    """Get list of supported image files from input folder"""
    supported_extensions = [
        '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff', '*.tif', 
        '*.gif', '*.webp', '*.svg'
    ]
    
    image_files = []
    input_path = Path(input_folder)
    
    if not input_path.exists():
        print(f"⚠️  Input folder not found: {input_folder}")
        return []
    
    for ext in supported_extensions:
        pattern = str(input_path / ext)
        files = glob.glob(pattern, recursive=False)
        image_files.extend(files)
    
    # Sort files naturally (image1.jpg, image2.jpg, etc.)
    image_files.sort()
    
    return image_files


def convert_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string"""
    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"⚠️  Failed to convert {image_path} to base64: {e}")
        return ""


def detect_image_content_type(image_path: str) -> str:
    """Detect image content type from file extension"""
    ext = Path(image_path).suffix.lower()
    content_types = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.bmp': 'image/bmp',
        '.tiff': 'image/tiff', '.tif': 'image/tiff',
        '.gif': 'image/gif', '.webp': 'image/webp',
        '.svg': 'image/svg+xml'
    }
    return content_types.get(ext, 'image/jpeg')


def diagnose_pdf_extraction(pdf_path: str, text_content: str, page_count: int) -> Dict[str, Any]:
    """Enhanced PDF extraction diagnostics for edisonpro"""
    diagnosis = {
        "pdf_path": pdf_path,
        "page_count": page_count,
        "total_characters": len(text_content),
        "avg_chars_per_page": len(text_content) // page_count if page_count > 0 else 0,
        "is_protected": False,
        "is_scanned": False,
        "has_text": len(text_content.strip()) > 0,
        "extraction_quality": "unknown",
        "issues_detected": [],
        "recommendations": [],
        "markitdown_available": HAS_MARKITDOWN,
        "extraction_methods_used": set()
    }
    
    text_lower = text_content.lower().strip()
    
    # Check for protected PDF indicators
    protection_indicators = [
        "this pdf file is protected",
        "you'll need a different reader",
        "this pdf document has been protected",
        "microsoft office",
        "download a compatible pdf reader",
        "document is password protected",
        "enter password",
        "access denied",
        "permission denied"
    ]
    
    for indicator in protection_indicators:
        if indicator in text_lower:
            diagnosis["is_protected"] = True
            diagnosis["issues_detected"].append(f"Protected PDF detected: '{indicator}'")
            diagnosis["extraction_quality"] = "failed_protected"
            break
    
    # Enhanced scanned document detection
    if not diagnosis["is_protected"]:
        if len(text_content.strip()) < 50 and page_count > 0:
            diagnosis["is_scanned"] = True
            diagnosis["issues_detected"].append("Very low text content - likely scanned images")
            diagnosis["extraction_quality"] = "poor_scanned"
        elif diagnosis["avg_chars_per_page"] < 100:
            diagnosis["is_scanned"] = True
            diagnosis["issues_detected"].append("Low text density - possibly scanned or image-heavy")
            diagnosis["extraction_quality"] = "poor_low_density"
        elif len(text_content.strip()) > 1000:
            diagnosis["extraction_quality"] = "excellent"
        elif len(text_content.strip()) > 500:
            diagnosis["extraction_quality"] = "good"
        else:
            diagnosis["extraction_quality"] = "moderate"
    
    # Generate enhanced recommendations
    if diagnosis["is_protected"]:
        diagnosis["recommendations"] = [
            "🔒 PDF is password protected or has usage restrictions",
            "✅ Try: Get unprotected version from document owner",
            "✅ Try: Use password if available with: qpdf --password=PASSWORD --decrypt input.pdf output.pdf",
            "✅ Try: Use Adobe Acrobat to remove restrictions",
            "✅ Try: Print to new PDF to remove protection",
            "⚠️  Note: o3-pro reasoning cannot analyze protected content"
        ]
    elif diagnosis["is_scanned"]:
        recommendations = [
            "🖼️  Document appears to be scanned images",
            "✅ MarkItDown fallback will attempt OCR" if HAS_MARKITDOWN else "❌ Install MarkItDown for OCR: pip install markitdown",
            "✅ Try: Use Adobe Acrobat Pro for OCR conversion",
            "✅ Try: Use online OCR tools (Google Drive, OneDrive)",
            "✅ Try: Convert with Tesseract OCR",
            "💡 o3-pro can still analyze visual elements from images"
        ]
        diagnosis["recommendations"] = recommendations
    else:
        diagnosis["recommendations"] = [
            "✅ PDF text extraction successful",
            "✅ Content ready for o3-pro enhanced analysis",
            "💡 Both text and visual analysis will be performed"
        ]
    
    return diagnosis


def log_extraction_diagnosis_pro(diagnosis: Dict[str, Any]):
    """Enhanced extraction diagnosis logging for edisonpro"""
    print("\n" + "="*70)
    print("🧠 EDISON PRO - PDF EXTRACTION DIAGNOSTICS")
    print("="*70)
    
    print(f"📄 File: {diagnosis['pdf_path']}")
    print(f"📊 Pages: {diagnosis['page_count']}")
    print(f"📝 Characters: {diagnosis['total_characters']:,}")
    print(f"📈 Avg per page: {diagnosis['avg_chars_per_page']:,}")
    print(f"🔧 MarkItDown: {'Available' if diagnosis['markitdown_available'] else 'Not Available'}")
    
    # Enhanced status indicators
    if diagnosis['is_protected']:
        print("🔒 Status: PROTECTED PDF DETECTED")
        print("❌ Text Extraction: FAILED (Protection/Encryption)")
        print("⚠️  Analysis Impact: o3-pro cannot process protected content")
    elif diagnosis['is_scanned']:
        print("🖼️  Status: SCANNED/IMAGE PDF DETECTED")
        print("⚠️  Text Extraction: POOR (OCR Required)")
        print("✅ Analysis Impact: o3-pro can still analyze visual elements")
    elif diagnosis['extraction_quality'] == 'excellent':
        print("🌟 Status: EXCELLENT TEXT EXTRACTION")
        print("✅ Text Extraction: OPTIMAL")
        print("🚀 Analysis Impact: Full o3-pro reasoning capabilities available")
    elif diagnosis['extraction_quality'] == 'good':
        print("✅ Status: GOOD TEXT EXTRACTION")
        print("✅ Text Extraction: SUCCESS")
        print("💪 Analysis Impact: Strong o3-pro analysis possible")
    else:
        print("⚠️  Status: MODERATE EXTRACTION")
        print("⚠️  Text Extraction: PARTIAL SUCCESS")
        print("🔄 Analysis Impact: o3-pro will focus on visual analysis")
    
    if diagnosis['issues_detected']:
        print("\n🚨 Issues Detected:")
        for issue in diagnosis['issues_detected']:
            print(f"   • {issue}")
    
    print("\n💡 Recommendations:")
    for rec in diagnosis['recommendations']:
        print(f"   {rec}")
    
    print("="*70 + "\n")


# ============================================================================
# FALLBACK IMPLEMENTATIONS
# ============================================================================

class FallbackGraph:
    """Simple fallback graph implementation when NetworkX is not available"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = defaultdict(list)
    
    def add_node(self, node_id: str, metadata: Any = None):
        self.nodes[node_id] = metadata
    
    def add_edge(self, from_node: str, to_node: str, **kwargs):
        self.edges[from_node].append(to_node)
    
    def get_neighbors(self, node_id: str) -> List[str]:
        return self.edges.get(node_id, [])
    
    def has_node(self, node_id: str) -> bool:
        return node_id in self.nodes


# ============================================================================
# CONFIGURATION & DATA MODELS
# ============================================================================

@dataclass
class ChunkMetadata:
    """Metadata for document chunks"""
    chunk_id: str
    page_numbers: List[int]
    diagram_type: Optional[str]
    scale: Optional[str]
    reference_numbers: List[str]
    components: List[str]
    bounding_box: Optional[Dict[str, float]]
    dependencies: List[str]
    source_file: Optional[str] = None

@dataclass
class VisualElement:
    """Extracted visual elements from diagrams."""
    element_id: str
    element_type: str  # symbol, line, text, dimension, etc.
    coordinates: Dict[str, float]
    properties: Dict[str, Any]
    connections: List[str]
    text_content: Optional[str]

@dataclass
class TechnicalInterpretation:
    """Domain expert interpretation of a technical component."""
    component_id: str
    function: str
    specifications: Dict[str, Any]
    standards: List[str]
    failure_modes: List[str]
    interactions: List[Dict[str, str]]
    confidence: float

@dataclass
class CrossReference:
    """Cross-reference between document sections."""
    source_id: str
    target_id: str
    reference_type: str
    reference_text: str
    resolved: bool

class DiagramType(Enum):
    """Enumeration of supported engineering diagram types."""
    ELECTRICAL_SCHEMATIC = "electrical_schematic"
    MECHANICAL_ASSEMBLY = "mechanical_assembly"
    PID = "pid"  # Piping & Instrumentation Diagram
    STRUCTURAL = "structural"
    CIVIL = "civil"
    UNKNOWN = "unknown"


# ============================================================================
# CONTEXT MANAGER - Enhanced for o3-pro
# ============================================================================

class ContextManagerPro:
    """Enhanced context manager using Azure AI Search with hybrid search capabilities."""
    
    def __init__(self, max_working_tokens: int = 100000):
        """Initialize the ContextManager with Azure AI Search."""
        self.max_working_tokens = max_working_tokens
        
        # Load Azure Search configuration
        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.api_key = os.getenv("AZURE_SEARCH_API_KEY")
        self.index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "edison-diagrams")
        
        # Initialize token counting
        if HAS_TIKTOKEN:
            try:
                self.encoding = tiktoken.encoding_for_model("gpt-4")
            except Exception:
                self.encoding = None
        else:
            self.encoding = None
        
        # Initialize Azure Search client
        self.search_client = None
        if HAS_AZURE_SEARCH and self.endpoint and self.api_key:
            try:
                self.search_client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=AzureKeyCredential(self.api_key)
                )
                print(f"✅ Azure AI Search initialized: {self.index_name}")
            except Exception as e:
                print(f"⚠️  Azure Search initialization failed: {e}")
                print("   Using fallback storage.")
                self.search_client = None
        else:
            if not self.endpoint or not self.api_key:
                print("⚠️  Azure Search credentials not configured.")
                print("   Set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME in .env")
            print("   Using in-memory fallback storage.")
        
        # Local cache for chunks
        self.chunk_store: Dict[str, Dict[str, Any]] = {}
        
        # Staging buffer for Azure Search (deferred upload)
        self.pending_documents: List[Dict[str, Any]] = []
        
        # Fallback storage
        self.fallback_embeddings: Dict[str, List[float]] = {}
        self.fallback_documents: Dict[str, str] = {}

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken or fallback"""
        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass
        # Fallback: rough estimate of 1 token per 4 characters
        return len(text) // 4
    
    def add_chunk(self, chunk_id: str, content: str, metadata: ChunkMetadata, embedding: List[float]):
        """Add a chunk to Azure AI Search with metadata."""
        # Build document for Azure Search (ensure all fields are properly typed for Azure Search)
        document = {
            "chunk_id": chunk_id,
            "content": content or "",  # Ensure not None
            "content_vector": embedding or [],  # Ensure not None
            "page_numbers": metadata.page_numbers or [],
            "diagram_type": metadata.diagram_type or "",  # Convert None to empty string
            "scale": metadata.scale or "",  # Convert None to empty string
            "reference_numbers": metadata.reference_numbers or [],
            "components": metadata.components or [],
            "dependencies": metadata.dependencies or [],
            "source_file": metadata.source_file or "",
            "timestamp": datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        
        # Stage document for later upload (deferred until analysis completes)
        if self.search_client:
            self.pending_documents.append(document)
            print(f"   📝 Staged {chunk_id} for Azure AI Search (deferred upload)")
        else:
            # Use fallback storage
            self.fallback_embeddings[chunk_id] = embedding
            self.fallback_documents[chunk_id] = content
        
        # Store full chunk
        self.chunk_store[chunk_id] = {
            "content": content,
            "metadata": metadata,
            "token_count": self.count_tokens(content)
        }
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for search queries (synchronous wrapper)."""
        try:
            import asyncio
            # Use the orchestrator's embedding method if available
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, but need sync - use dummy
                import random
                return [random.random() for _ in range(1536)]
            else:
                # Can run async
                from openai import AsyncAzureOpenAI
                import os
                
                embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
                api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
                # Use dedicated embedding endpoint if available
                azure_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
                
                client = AsyncAzureOpenAI(
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    api_version=api_version,
                    azure_endpoint=azure_endpoint
                )
                
                response = loop.run_until_complete(
                    client.embeddings.create(model=embedding_deployment, input=text[:8000])
                )
                return response.data[0].embedding
        except Exception as e:
            print(f"⚠️  Embedding generation failed: {e}. Using fallback.")
            import random
            return [random.random() for _ in range(1536)]
    
    def retrieve_relevant_context(
        self, 
        query: str, 
        max_chunks: int = 15,  # Increased for o3-pro
        include_neighbors: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks using Azure AI Search hybrid search."""
        relevant_chunks = []
        total_tokens = 0
        
        # Warn if there are pending uncommitted documents
        if self.pending_documents:
            print(f"⚠️  Warning: {len(self.pending_documents)} documents are staged but not yet uploaded to Azure Search")
            print("   Search results may be incomplete. Ensure analysis completes successfully.")
        
        # Try Azure AI Search hybrid search first
        if self.search_client:
            try:
                # Generate query embedding for vector search
                query_embedding = self._generate_embedding(query)
                
                # Create vector query
                vector_query = VectorizedQuery(
                    vector=query_embedding,
                    k_nearest_neighbors=max_chunks,
                    fields="content_vector"
                )
                
                # Execute hybrid search (vector + keyword)
                results = self.search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    select=["chunk_id", "content", "page_numbers", "diagram_type", "scale", 
                           "reference_numbers", "components", "dependencies", "source_file"],
                    top=max_chunks
                )
                
                # Process results
                for result in results:
                    chunk_id = result.get("chunk_id")
                    if not chunk_id:
                        continue

                    chunk = self.chunk_store.get(chunk_id)
                    if not chunk:
                        content = result.get("content") or ""
                        metadata = ChunkMetadata(
                            chunk_id=chunk_id,
                            page_numbers=result.get("page_numbers") or [],
                            diagram_type=result.get("diagram_type") or None,
                            scale=result.get("scale") or None,
                            reference_numbers=result.get("reference_numbers") or [],
                            components=result.get("components") or [],
                            bounding_box=None,
                            dependencies=result.get("dependencies") or [],
                            source_file=result.get("source_file") or None,
                        )
                        chunk = {
                            "content": content,
                            "metadata": metadata,
                            "token_count": self.count_tokens(content)
                        }
                        # Cache chunk so subsequent queries reuse it without another search round-trip
                        self.chunk_store[chunk_id] = chunk

                    if total_tokens + chunk['token_count'] > self.max_working_tokens:
                        break

                    relevant_chunks.append(chunk)
                    total_tokens += chunk['token_count']
                    
            except Exception as e:
                print(f"⚠️  Azure Search query failed: {e}. Using fallback search.")
                relevant_chunks = self._fallback_search(query, max_chunks)
        else:
            relevant_chunks = self._fallback_search(query, max_chunks)
        
        return relevant_chunks
    
    def commit_to_search(self) -> bool:
        """Upload all staged documents to Azure Search after successful analysis.
        
        Returns:
            bool: True if upload successful, False otherwise
        """
        if not self.search_client or not self.pending_documents:
            if not self.pending_documents:
                print("   ℹ️  No documents to upload")
            return True
        
        try:
            print(f"\n💾 Committing {len(self.pending_documents)} documents to Azure AI Search...")
            # Batch upload all documents
            self.search_client.upload_documents(documents=self.pending_documents)
            print(f"   ✅ Successfully uploaded {len(self.pending_documents)} documents to index")
            self.pending_documents.clear()  # Clear staging buffer
            return True
        except Exception as e:
            print(f"   ❌ Azure Search batch upload failed: {e}")
            print(f"   ⚠️  {len(self.pending_documents)} documents remain staged")
            # Keep documents in staging buffer for potential retry
            return False
    
    def _fallback_search(self, query: str, max_chunks: int) -> List[Dict[str, Any]]:
        """Enhanced fallback search for o3-pro"""
        query_lower = query.lower()
        scored_chunks = []
        
        for chunk_id, chunk_data in self.chunk_store.items():
            content = chunk_data['content'].lower()
            # Enhanced scoring for o3-pro
            score = sum(1 for word in query_lower.split() if word in content)
            # Boost score for technical terms
            technical_terms = ['motor', 'pump', 'valve', 'transformer', 'switch', 'controller']
            score += sum(2 for term in technical_terms if term in content and term in query_lower)
            
            if score > 0:
                scored_chunks.append((score, chunk_data))
        
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_chunks[:max_chunks]]


# ============================================================================
# AGENT 0: PLANNING AGENT - Strategic Analysis Planning with o3-pro
# ============================================================================

@dataclass
class AnalysisPlan:
    """Strategic plan for document/image analysis."""
    detected_disciplines: List[str]
    drawing_types: List[str]
    complexity: str  # simple, medium, complex
    key_features: List[str]
    recommended_reasoning: str  # low, medium, high, maximum
    estimated_duration_minutes: int
    focus_areas: List[str]
    special_considerations: List[str]
    agent_config: Dict[str, Any]
    confidence: float

class PlanningAgentPro:
    """Phase 0: Fast reconnaissance and strategic planning for analysis optimization.
    
    Uses o3-pro with low reasoning effort to quickly assess drawings and create
    an intelligent analysis plan that guides all subsequent agents.
    """
    
    def __init__(self, client: OpenAI, deployment_name: str):
        self.client = client
        self.deployment_name = deployment_name
        self.planning_reasoning_effort = "high"  # gpt-5-pro only supports 'high'
        self.history: List[Dict[str, Any]] = self._load_history()
        self._history_cache: Optional[str] = None

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load prior planning history if available."""
        try:
            if PLANNING_HISTORY_FILE.exists():
                with open(PLANNING_HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as exc:
            print(f"⚠️  Could not load planning history: {exc}")
        return []

    def _save_history(self):
        """Persist planning history to disk (keep recent entries only)."""
        try:
            entries = self.history[-50:]
            self.history = entries
            PLANNING_HISTORY_FILE.write_text(
                json.dumps(entries, indent=2),
                encoding="utf-8"
            )
        except Exception as exc:
            print(f"⚠️  Could not save planning history: {exc}")

    def _record_plan(self, plan: AnalysisPlan, metadata: Dict[str, Any], refined: bool = False):
        """Record the generated plan and optional refinement metadata."""
        plan_payload = asdict(plan)
        entry = {
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "plan": plan_payload,
            "agent_config": plan.agent_config,
            "metadata": metadata
        }

        if refined and self.history:
            self.history[-1].setdefault("refinements", []).append(entry)
        else:
            self.history.append(entry)

        self._save_history()
        self._history_cache = None

    def _build_history_context(self, user_domain_hint: Optional[str]) -> Optional[str]:
        """Summarize historical planning signals to inform the prompt."""
        if self._history_cache:
            return self._history_cache

        if not self.history:
            return None

        recent_entries = self.history[-20:]
        discipline_counter: Counter = Counter()
        complexity_counter: Counter = Counter()
        consideration_counter: Counter = Counter()

        for entry in recent_entries:
            plan_data = entry.get("plan", {})
            for discipline in plan_data.get("detected_disciplines", []):
                discipline_counter[discipline] += 1
            complexity = plan_data.get("complexity")
            if complexity:
                complexity_counter[complexity] += 1
            for consideration in plan_data.get("special_considerations", []):
                consideration_counter[consideration] += 1

        top_disciplines = ", ".join(
            f"{name} ({count})" for name, count in discipline_counter.most_common(3)
        ) or "none"
        top_complexity = complexity_counter.most_common(1)
        complexity_insight = top_complexity[0][0] if top_complexity else "medium"
        top_considerations = ", ".join(
            consideration for consideration, _ in consideration_counter.most_common(2)
        ) or "None recorded"

        domain_hint_text = f"User hint: {user_domain_hint}." if user_domain_hint else "No user domain hint provided."
        summary = (
            "Historical planning insights:\n"
            f"- Frequent disciplines: {top_disciplines}\n"
            f"- Typical complexity: {complexity_insight}\n"
            f"- Recurring considerations: {top_considerations}\n"
            f"- {domain_hint_text}"
        )

        self._history_cache = summary
        return summary

    def _apply_cost_controls(self, plan: AnalysisPlan, sample_count: int) -> List[str]:
        """Apply lightweight cost optimizations without breaking behaviour."""
        adjustments = []

        current_effort = plan.agent_config.get("reasoning_effort", plan.recommended_reasoning)
        complexity = plan.complexity

        if complexity == "simple" and current_effort in {"high", "maximum"}:
            plan.agent_config["reasoning_effort"] = "high"
            plan.recommended_reasoning = "high"
            note = "gpt-5-pro only supports high reasoning effort"
            if note not in plan.special_considerations:
                plan.special_considerations.append(note)
            adjustments.append("reasoning_effort -> high")

        if sample_count <= 1 and plan.agent_config.get("max_concurrent_pages", 5) > 4:
            plan.agent_config["max_concurrent_pages"] = 4
            adjustments.append("max_concurrent_pages capped at 4 for small batch")

        return adjustments

    def refine_plan_with_diagnostics(
        self,
        plan: Optional[AnalysisPlan],
        diagnostics: Optional[Dict[str, Any]]
    ) -> Tuple[Optional[AnalysisPlan], List[str]]:
        """Refine an existing plan with preprocessing diagnostics."""
        if not plan or not diagnostics:
            return plan, []

        updates: List[str] = []
        considerations = plan.special_considerations[:]
        agent_config = plan.agent_config.copy()

        input_type = diagnostics.get("input_type", "unknown")
        quality = diagnostics.get("extraction_quality")

        if diagnostics.get("is_protected"):
            note = "Source protected - rely on visual reasoning"
            if note not in considerations:
                considerations.append(note)
            agent_config["reasoning_effort"] = "high"
            plan.recommended_reasoning = "high"
            updates.append("escalated reasoning for protected source")

        if diagnostics.get("is_scanned") or (quality in {"poor_scanned", "poor_low_density"}):
            note = "Scanned quality - prioritize OCR improvements"
            if note not in considerations:
                considerations.append(note)
            if agent_config.get("reasoning_effort") != "high":
                agent_config["reasoning_effort"] = "high"
                plan.recommended_reasoning = "high"
                updates.append("raised reasoning for scanned input")
            agent_config["enable_smart_chunking"] = True

        if diagnostics.get("total_characters", 0) < 200 and input_type == "pdf":
            note = "Low text density - lean on visual extraction"
            if note not in considerations:
                considerations.append(note)
            updates.append("noted low text density")

        if diagnostics.get("image_count"):
            agent_config.setdefault("metadata", {})["image_count"] = diagnostics["image_count"]

        if diagnostics.get("issues_detected"):
            common_issue = diagnostics["issues_detected"][0]
            if common_issue not in considerations:
                considerations.append(common_issue)

        plan.special_considerations = considerations
        plan.agent_config.update(agent_config)

        if updates:
            summary = {
                "input_type": input_type,
                "quality": quality,
                "issues": diagnostics.get("issues_detected", [])[:3]
            }
            self._record_plan(plan, {"refined": True, "diagnostics": summary}, refined=True)

        return plan, updates
    
    async def create_analysis_plan(
        self, 
        image_data_list: List[Tuple[bytes, str]], 
        user_domain_hint: Optional[str] = None
    ) -> AnalysisPlan:
        """Create strategic analysis plan from quick scan of images/pages.
        
        Args:
            image_data_list: List of (image_bytes, filename) tuples
            user_domain_hint: Optional user-specified domain to validate/refine
            
        Returns:
            AnalysisPlan with detected characteristics and recommendations
        """
        print("\n🔍 PLANNING PHASE: Quick reconnaissance with o3-pro...")
        print(f"   Analyzing {len(image_data_list)} image(s) for characteristics...")
        
        # Take up to 3 representative samples for quick scan
        samples = image_data_list[:min(3, len(image_data_list))]
        
        # Build planning prompt enriched with history context
        history_context = self._build_history_context(user_domain_hint)
        planning_prompt = self._build_planning_prompt(user_domain_hint, history_context)
        
        # Prepare images for o3-pro
        image_contents = []
        for img_bytes, filename in samples:
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(img_bytes).decode('utf-8')}"
                }
            })
        
        # Quick o3-pro call with low reasoning
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": planning_prompt},
                            *image_contents
                        ]
                    }
                ],
                reasoning_effort=self.planning_reasoning_effort,
                temperature=0.3,
                max_completion_tokens=2000
            )
            
            plan_text = response.choices[0].message.content
            
            # Parse the structured response
            plan = self._parse_planning_response(plan_text, user_domain_hint)
            cost_adjustments = self._apply_cost_controls(plan, len(image_data_list))
            if cost_adjustments:
                print(f"   💸 Cost guard applied: {', '.join(cost_adjustments)}")
            metadata = {
                "sample_count": len(image_data_list),
                "user_hint": user_domain_hint,
                "history_context_used": bool(history_context)
            }
            self._record_plan(plan, metadata)
            
            # Display plan summary
            self._display_plan_summary(plan)
            
            return plan
            
        except Exception as e:
            print(f"⚠️  Planning phase encountered error: {e}")
            print("   Falling back to default analysis plan...")
            fallback = self._create_fallback_plan(user_domain_hint)
            self._record_plan(fallback, {"error": str(e)[:160], "fallback": True})
            return fallback
    
    def _build_planning_prompt(self, user_domain_hint: Optional[str], history_context: Optional[str]) -> str:
        """Build the planning prompt for o3-pro."""
        prompt = """STRATEGIC ANALYSIS PLANNING PHASE

You are an expert engineering document analyst. Perform a QUICK reconnaissance of these engineering drawing(s) to create an optimal analysis plan.

ANALYZE AND RESPOND IN THIS EXACT JSON FORMAT:

{
  "detected_disciplines": ["discipline1", "discipline2"],
  "drawing_types": ["type1", "type2"],
  "complexity": "simple|medium|complex",
  "key_features": ["feature1", "feature2", "feature3", "feature4", "feature5"],
  "recommended_reasoning": "medium|high|maximum",
  "estimated_duration_minutes": X,
  "focus_areas": ["area1", "area2", "area3"],
  "special_considerations": ["consideration1", "consideration2"],
  "confidence": 0.0-1.0
}

FIELD DEFINITIONS:

1. detected_disciplines: Choose from [electrical, mechanical, pid, civil, structural]. List ALL that apply.
   - electrical: Power systems, motors, transformers, circuits, panels, distribution
   - mechanical: Pumps, valves, piping, HVAC, equipment layouts
   - pid: P&IDs, instrumentation, control loops, process diagrams
   - civil: Site plans, grading, utilities, foundations, underground routing
   - structural: Beams, columns, connections, reinforcement, structural framing

2. drawing_types: Specific document types detected
   - Examples: "single-line diagram", "P&ID", "plan-and-profile", "control schematic", 
     "site plan", "connection detail", "equipment layout", "panel schedule"

3. complexity: Overall analysis difficulty
   - simple: Clear, single-discipline, standard symbols, good quality
   - medium: Multi-element, readable, some interdisciplinary aspects
   - complex: Multi-discipline, dense information, poor quality, or highly technical

4. key_features: 5-10 SPECIFIC elements you observe (be concrete)
   - Examples: "480V 3-phase motor", "25kV transformer", "fire hydrant", "I-beam W12x26"
   - NOT generic like "electrical equipment" - BE SPECIFIC

5. recommended_reasoning: Based on complexity and drawing quality
   - medium: Simple, clear drawings with standard symbols
   - high: Most engineering diagrams (recommended default)
   - maximum: Complex, poor quality, or critical safety systems

6. estimated_duration_minutes: Rough estimate for FULL analysis (planning + deep analysis)

7. focus_areas: What should deep analysis prioritize?
   - Examples: "equipment identification", "voltage ratings", "pipe routing", "connection types"

8. special_considerations: Quality issues, multi-sheet aspects, unusual characteristics
   - Examples: "poor scan quality", "handwritten annotations", "multi-sheet coordination needed"

9. confidence: Your confidence in this assessment (0.0-1.0)
"""
        
        if user_domain_hint:
            prompt += f"\n\nUSER DOMAIN HINT: User specified '{user_domain_hint}'. Validate if this matches what you observe.\n"
        if history_context:
            prompt += f"\nHISTORICAL CONTEXT FROM PRIOR RUNS:\n{history_context}\n"
        
        prompt += "\nRESPOND WITH ONLY THE JSON OBJECT. Be specific and actionable.\n"
        
        return prompt
    
    def _parse_planning_response(self, plan_text: str, user_domain_hint: Optional[str]) -> AnalysisPlan:
        """Parse o3-pro response into AnalysisPlan object."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_text = plan_text.strip()
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
            
            plan_data = json.loads(json_text)
            
            # Build combined domain string
            disciplines = plan_data.get("detected_disciplines", ["general"])
            domain_str = ",".join(disciplines)
            
            # Create agent config based on recommendations
            agent_config = {
                "domain": domain_str,
                "reasoning_effort": plan_data.get("recommended_reasoning", "high"),
                "enable_smart_chunking": True,
                "max_concurrent_pages": 5 if plan_data.get("complexity") != "complex" else 3,
                "focus_keywords": plan_data.get("key_features", [])
            }
            
            return AnalysisPlan(
                detected_disciplines=disciplines,
                drawing_types=plan_data.get("drawing_types", ["unknown"]),
                complexity=plan_data.get("complexity", "medium"),
                key_features=plan_data.get("key_features", []),
                recommended_reasoning=plan_data.get("recommended_reasoning", "high"),
                estimated_duration_minutes=plan_data.get("estimated_duration_minutes", 5),
                focus_areas=plan_data.get("focus_areas", []),
                special_considerations=plan_data.get("special_considerations", []),
                agent_config=agent_config,
                confidence=plan_data.get("confidence", 0.8)
            )
            
        except Exception as e:
            print(f"⚠️  Could not parse planning response: {e}")
            return self._create_fallback_plan(user_domain_hint)
    
    def _create_fallback_plan(self, user_domain_hint: Optional[str]) -> AnalysisPlan:
        """Create a safe fallback plan if planning fails."""
        domain = user_domain_hint if user_domain_hint else "general"
        return AnalysisPlan(
            detected_disciplines=[domain] if "," not in domain else domain.split(","),
            drawing_types=["unknown"],
            complexity="medium",
            key_features=[],
            recommended_reasoning="high",
            estimated_duration_minutes=5,
            focus_areas=["general analysis"],
            special_considerations=["planning phase failed - using defaults"],
            agent_config={
                "domain": domain,
                "reasoning_effort": "high",
                "enable_smart_chunking": True,
                "max_concurrent_pages": 5,
                "focus_keywords": []
            },
            confidence=0.5
        )
    
    def _display_plan_summary(self, plan: AnalysisPlan):
        """Display the analysis plan summary to user."""
        print("\n" + "="*70)
        print("📋 ANALYSIS PLAN CREATED")
        print("="*70)
        
        # Disciplines
        disciplines_display = " + ".join(d.upper() for d in plan.detected_disciplines)
        print(f"🎯 Detected Disciplines: {disciplines_display}")
        
        # Drawing types
        if plan.drawing_types and plan.drawing_types != ["unknown"]:
            types_str = ", ".join(plan.drawing_types)
            print(f"📐 Drawing Type(s): {types_str}")
        
        # Complexity and reasoning
        complexity_emoji = {"simple": "🟢", "medium": "🟡", "complex": "🔴"}.get(plan.complexity, "⚪")
        print(f"{complexity_emoji} Complexity: {plan.complexity.upper()}")
        print(f"🧠 Recommended Reasoning: {plan.recommended_reasoning.upper()}")
        print(f"⏱️  Estimated Duration: {plan.estimated_duration_minutes} minutes")
        
        # Key features (show top 5)
        if plan.key_features:
            print(f"\n🔍 Key Features Identified:")
            for i, feature in enumerate(plan.key_features[:5], 1):
                print(f"   {i}. {feature}")
        
        # Focus areas
        if plan.focus_areas:
            print(f"\n🎯 Analysis Focus:")
            for area in plan.focus_areas[:3]:
                print(f"   • {area}")
        
        # Special considerations
        if plan.special_considerations:
            print(f"\n⚠️  Special Considerations:")
            for consideration in plan.special_considerations:
                print(f"   • {consideration}")
        
        print(f"\n📊 Confidence: {plan.confidence:.1%}")
        print("="*70 + "\n")


# ============================================================================
# AGENT 1: DOCUMENT PREPROCESSOR - Enhanced for o3-pro
# ============================================================================

class DocumentPreprocessorPro:
    """Enhanced document preprocessor optimized for o3-pro reasoning capabilities."""
    
    def __init__(self, client: OpenAI, deployment_name: str, reasoning_effort: str = "high", max_concurrent_pages: int = 5, enable_smart_chunking: bool = True, intermediate_dir: Path = None, domain: str = "general"):
        self.client = client
        self.deployment_name = deployment_name
        self.reasoning_effort = reasoning_effort
        self.overlap_percentage = 0.15
        self.max_concurrent_pages = max_concurrent_pages
        self.enable_smart_chunking = enable_smart_chunking
        self.intermediate_dir = intermediate_dir
        self.domain = domain
        self._processing_semaphore = asyncio.Semaphore(max_concurrent_pages)
        self.latest_diagnostics: Optional[Dict[str, Any]] = None
        
        # Initialize Azure Document Intelligence client
        self.di_client = None
        if HAS_AZURE_DI:
            di_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            di_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")
            if di_endpoint and di_key:
                try:
                    self.di_client = DocumentIntelligenceClient(
                        endpoint=di_endpoint,
                        credential=AzureKeyCredential(di_key)
                    )
                    print("✅ Azure Document Intelligence initialized")
                except Exception as e:
                    print(f"⚠️  Azure Document Intelligence initialization failed: {e}")
                    self.di_client = None
            else:
                print("⚠️  Azure Document Intelligence credentials not configured")
                print("   Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_API_KEY in .env")
    
    def _get_domain_context(self) -> str:
        """Get domain-specific analysis context for o3-pro. Supports hybrid domains."""
        domain_contexts = {
            "electrical": """
ELECTRICAL ENGINEERING DOMAIN EXPERTISE:
- Components: Motors, transformers, circuit breakers, relays, contactors, MCCs, switchgear, panels, service laterals, pull boxes
- Standards: IEEE, NFPA 70 (NEC), ANSI, IEC, UL
- Diagram Types: Single-line diagrams, three-line diagrams, control schematics, ladder logic, panel layouts, underground distribution
- Key Focus: Voltage ratings, current ratings, power calculations, protection schemes, grounding, primary/secondary distribution
- Terminology: kV, kW, HP, amps, phases, neutral, ground, fault current, short circuit, service entrance
""",
            "mechanical": """
MECHANICAL ENGINEERING DOMAIN EXPERTISE:
- Components: Pumps, valves, actuators, gearboxes, bearings, couplings, seals, pipes, fittings
- Standards: ASME, API, ISO, ANSI B
- Diagram Types: Piping layouts, assembly drawings, fabrication drawings, BOM (Bill of Materials)
- Key Focus: Dimensions, tolerances, materials, flow rates, pressures, temperatures, speeds
- Terminology: GPM, PSI, RPM, torque, clearances, fits, threads, welding symbols
""",
            "pid": """
P&ID (PIPING & INSTRUMENTATION) DOMAIN EXPERTISE:
- Components: Valves (gate, globe, ball, check), instruments, transmitters, controllers, analyzers
- Standards: ISA, ANSI/ISA-5.1, ISO 14617, API
- Diagram Types: P&IDs (Piping & Instrumentation Diagrams), loop diagrams, instrument indexes
- Key Focus: Process flow, control loops, instrument tags, line numbers, valve positions
- Terminology: FT (flow transmitter), PT (pressure transmitter), LCV (level control valve), PID loops
- Symbols: Instrument bubbles, valve symbols, line types (process, instrument, electrical)
""",
            "civil": """
CIVIL ENGINEERING DOMAIN EXPERTISE:
- Components: Foundations, footings, retaining walls, drainage systems, manholes, catch basins, utility trenches, crossings
- Standards: ACI, ASTM, AASHTO, IBC (International Building Code), local utility standards
- Diagram Types: Site plans, grading plans, foundation plans, utility plans, plan-and-profile sheets, detail drawings
- Key Focus: Elevations, grades, slopes, drainage, soil bearing capacity, underground routing, trench depths, utility crossings
- Terminology: Rebar (reinforcement), PSF (pounds per square foot), grade beams, cut/fill, invert elevation, station points
""",
            "structural": """
STRUCTURAL ENGINEERING DOMAIN EXPERTISE:
- Components: Steel beams, columns, trusses, connections, bolts, welds, concrete reinforcement, equipment pads
- Standards: AISC, ACI 318, ASCE 7, AWS (welding)
- Diagram Types: Structural plans, framing plans, connection details, reinforcement details, equipment foundation details
- Key Focus: Load paths, member sizes, connection types, moment connections, shear, pad dimensions, anchor bolts
- Terminology: W-beams, C-channels, HSS (hollow structural sections), moment frames, bracing, slab-on-grade
""",
            "general": """
GENERAL ENGINEERING DOMAIN EXPERTISE:
- Analyze broadly across multiple engineering disciplines
- Identify diagram type from visual and textual cues
- Extract common elements: title blocks, revision numbers, reference drawings, scales
- Focus on standard engineering documentation practices
- Apply general technical standards and best practices
"""
        }
        
        # Handle hybrid domains (comma-separated)
        if "," in self.domain:
            domains = [d.strip() for d in self.domain.split(",")]
            combined_context = "HYBRID MULTI-DISCIPLINE DOMAIN EXPERTISE:\n"
            combined_context += f"This drawing combines: {', '.join(d.upper() for d in domains)}\n"
            combined_context += "Apply expertise from ALL relevant domains:\n\n"
            for domain in domains:
                if domain in domain_contexts:
                    combined_context += domain_contexts[domain] + "\n"
            return combined_context
        
        return domain_contexts.get(self.domain, domain_contexts["general"])
    
    async def _extract_with_azure_di(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Extract structured content using Azure Document Intelligence Layout API.
        
        Returns:
            Dict containing:
                - text: Formatted extracted text
                - tables: List of extracted tables with structure
                - key_value_pairs: Extracted form fields (e.g., title block)
                - raw_result: Full ADI response for debugging
                - confidence: Average confidence score
        """
        if not self.di_client:
            return None
        
        try:
            print(f"   📊 Azure Document Intelligence: Analyzing layout...")
            
            # Read image file
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            # Analyze document with Layout model (prebuilt-layout)
            # Layout model is ideal for engineering diagrams - extracts text, tables, structure
            poller = self.di_client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=image_data
            )
            result = poller.result()
            
            # Extract text content with reading order
            text_blocks = []
            for page in result.pages:
                page_text = f"\n=== PAGE {page.page_number} ===\n"
                # Get lines in reading order
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        text_blocks.append(line.content)
                page_text += "\n".join([line.content for line in page.lines]) if page.lines else ""
            
            full_text = "\n".join(text_blocks)
            
            # Extract tables with structure
            tables = []
            if hasattr(result, 'tables') and result.tables:
                for table_idx, table in enumerate(result.tables):
                    table_data = {
                        "table_id": f"table_{table_idx + 1}",
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }
                    
                    # Extract cell data
                    for cell in table.cells:
                        table_data["cells"].append({
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "content": cell.content,
                            "row_span": getattr(cell, 'row_span', 1),
                            "column_span": getattr(cell, 'column_span', 1),
                            "confidence": getattr(cell, 'confidence', 1.0)
                        })
                    
                    tables.append(table_data)
            
            # Extract key-value pairs (useful for title blocks)
            key_value_pairs = []
            if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
                for kv in result.key_value_pairs:
                    if kv.key and kv.value:
                        key_value_pairs.append({
                            "key": kv.key.content if hasattr(kv.key, 'content') else str(kv.key),
                            "value": kv.value.content if hasattr(kv.value, 'content') else str(kv.value),
                            "confidence": getattr(kv, 'confidence', 1.0)
                        })
            
            # Calculate average confidence
            # Note: prebuilt-layout model may not provide per-line confidence scores for images
            all_confidences = []
            
            # Try to get confidence from multiple sources
            # 1. Check line-level confidence (may not be available for images)
            for page in result.pages:
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        if hasattr(line, 'confidence') and line.confidence is not None:
                            all_confidences.append(line.confidence)
            
            # 2. Check word-level confidence (alternative source)
            if not all_confidences:
                for page in result.pages:
                    if hasattr(page, 'words') and page.words:
                        for word in page.words:
                            if hasattr(word, 'confidence') and word.confidence is not None:
                                all_confidences.append(word.confidence)
            
            # 3. If extraction succeeded but no confidence available, use extraction success indicator
            if all_confidences:
                avg_confidence = sum(all_confidences) / len(all_confidences)
            elif full_text.strip():
                # Extraction succeeded - use high confidence indicator (85%)
                avg_confidence = 0.85
            else:
                avg_confidence = 0.0
            
            # Format results
            formatted_text = f"Engineering Diagram Analysis - Azure Document Intelligence\n"
            formatted_text += f"Source: {Path(image_path).name}\n"
            formatted_text += f"Confidence: {avg_confidence:.2%}\n\n"
            
            # Add key-value pairs (title block info)
            if key_value_pairs:
                formatted_text += "=== TITLE BLOCK / METADATA ===\n"
                for kv in key_value_pairs:
                    formatted_text += f"{kv['key']}: {kv['value']}\n"
                formatted_text += "\n"
            
            # Add extracted text
            formatted_text += "=== EXTRACTED TEXT ===\n"
            formatted_text += full_text + "\n\n"
            
            # Add tables
            if tables:
                formatted_text += "=== EXTRACTED TABLES ===\n"
                for table in tables:
                    formatted_text += f"\nTable {table['table_id']} ({table['row_count']}x{table['column_count']}):\n"
                    # Format as simple table
                    rows_dict = {}
                    for cell in table['cells']:
                        row_idx = cell['row_index']
                        if row_idx not in rows_dict:
                            rows_dict[row_idx] = {}
                        rows_dict[row_idx][cell['column_index']] = cell['content']
                    
                    for row_idx in sorted(rows_dict.keys()):
                        row_cells = rows_dict[row_idx]
                        row_text = " | ".join(row_cells.get(col_idx, "") for col_idx in range(table['column_count']))
                        formatted_text += f"  {row_text}\n"
                formatted_text += "\n"
            
            print(f"   ✅ Azure DI: Extracted {len(full_text)} chars, {len(tables)} tables, {len(key_value_pairs)} key-value pairs")
            if all_confidences:
                print(f"   📊 Confidence: {avg_confidence:.2%} (from {len(all_confidences)} scored elements)")
            elif avg_confidence > 0:
                print(f"   📊 Confidence: {avg_confidence:.2%} (estimated - extraction successful)")
            else:
                print(f"   ⚠️  Confidence: N/A (no text extracted)")
            
            return {
                "text": formatted_text,
                "raw_text": full_text,
                "tables": tables,
                "key_value_pairs": key_value_pairs,
                "confidence": avg_confidence,
                "page_count": len(result.pages) if hasattr(result, 'pages') else 1
            }
            
        except Exception as e:
            print(f"   ⚠️  Azure Document Intelligence extraction failed: {e}")
            return None
    
    async def process_images_from_folder(self, input_folder: str) -> List[Dict[str, Any]]:
        """Enhanced image processing from input folder with o3-pro capabilities"""
        image_files = get_supported_image_files(input_folder)
        
        if not image_files:
            print(f"❌ No supported image files found in {input_folder}")
            print("   Supported formats: JPG, PNG, BMP, TIFF, GIF, WEBP, SVG")
            return []
        
        print(f"📁 Found {len(image_files)} images in {input_folder}")
        print(f"🧠 Processing with o3-pro enhanced image analysis...")
        
        for img in image_files:
            print(f"   📷 {Path(img).name}")
        
        # Convert images to page data format
        page_data = []
        all_extracted_text = []
        
        for i, image_path in enumerate(image_files):
            print(f"🖼️  Processing {Path(image_path).name} with o3-pro...")
            
            # Convert image to base64
            img_base64 = convert_image_to_base64(image_path)
            if not img_base64:
                continue
            
            # Enhanced extraction pipeline: Azure DI → MarkItDown → Direct Visual
            text_content = ""
            extraction_method = "image_direct"
            di_result = None
            
            # PRIORITY 1: Try Azure Document Intelligence (best for engineering diagrams)
            if self.di_client:
                di_result = await self._extract_with_azure_di(image_path)
                if di_result and di_result.get('confidence', 0) > 0.3:  # Reasonable confidence threshold
                    extraction_method = "azure_document_intelligence"
                    text_content = di_result['text']
                    print(f"   ✅ Azure DI: Extracted {len(text_content)} characters (confidence: {di_result['confidence']:.2%})")
                    
                    # Save ADI structured output
                    if self.intermediate_dir:
                        save_intermediate_json(
                            di_result,
                            f"image_{i + 1:03d}_{Path(image_path).stem}_azure_di.json",
                            self.intermediate_dir,
                            f"Azure Document Intelligence structured output for image {i + 1}"
                        )
            
            # PRIORITY 2: Fallback to MarkItDown OCR if ADI unavailable or low confidence
            if not di_result and HAS_MARKITDOWN:
                try:
                    print(f"   📝 Attempting MarkItDown OCR...")
                    md = MarkItDown()
                    result = md.convert(image_path)
                    text_content = result.text_content if hasattr(result, 'text_content') else str(result)
                    if len(text_content.strip()) > 10:
                        extraction_method = "markitdown_ocr"
                        text_content = f"Engineering diagram: {Path(image_path).name}\n\nExtracted text content:\n{text_content}\n\nThis is an engineering diagram image containing technical specifications, components, and layout information."
                        print(f"   ✅ Extracted {len(text_content)} characters via OCR")
                    else:
                        text_content = f"Engineering diagram image: {Path(image_path).name}\n\nThis appears to be a technical drawing or schematic containing engineering components, symbols, and specifications. The image shows various engineering elements that require visual analysis for proper interpretation."
                        print(f"   📊 No text detected - will use pure visual analysis")
                except Exception as e:
                    print(f"   ⚠️  OCR failed: {e}")
                    text_content = f"Engineering diagram image: {Path(image_path).name}\n\nThis is a technical drawing or engineering schematic that contains visual elements requiring expert analysis. The image may include components, symbols, specifications, and technical details."
            
            # PRIORITY 3: Pure visual analysis fallback
            if not text_content or len(text_content.strip()) < 50:
                text_content = f"Engineering diagram image: {Path(image_path).name}\n\nThis is a technical engineering diagram image containing components, symbols, and specifications. The image requires visual analysis to identify and interpret engineering elements, connections, and technical details."
            
            # Save to intermediate files if available
            if self.intermediate_dir:
                # Save original image
                save_intermediate_image(
                    img_base64,
                    f"image_{i + 1:03d}_{Path(image_path).stem}_original.{Path(image_path).suffix[1:]}",
                    self.intermediate_dir,
                    f"Original image {i + 1}: {Path(image_path).name}"
                )
                
                # Save extracted text
                image_text_content = f"=== IMAGE {i + 1} ({extraction_method.upper()}) ===\n\n"
                image_text_content += f"Source: {image_path}\n"
                image_text_content += f"Method: {extraction_method}\n\n"
                image_text_content += f"{text_content}\n\n"
                all_extracted_text.append(image_text_content)
                
                save_intermediate_file(
                    image_text_content,
                    f"image_{i + 1:03d}_extracted_text_{extraction_method}.txt",
                    self.intermediate_dir,
                    f"Image {i + 1} {extraction_method.upper()} text extraction"
                )
            
            page_data.append({
                "page_num": i,
                "text": text_content,
                "image": img_base64,
                "images": [],
                "extraction_method": extraction_method,
                "source_file": image_path
            })
        
        # Save complete extraction summary if intermediate dir exists
        if self.intermediate_dir and all_extracted_text:
            complete_text = "\n".join(all_extracted_text)
            save_intermediate_file(
                complete_text,
                "00_complete_image_extraction.txt",
                self.intermediate_dir,
                "Complete image extraction from all files"
            )
            
            # Save extraction summary
            summary = f"Image Processing Summary\n{'=' * 40}\n\n"
            summary += f"Input Folder: {input_folder}\n"
            summary += f"Total Images: {len(page_data)}\n"
            summary += f"Total Characters: {len(complete_text)}\n"
            summary += f"MarkItDown Available: {'Yes' if HAS_MARKITDOWN else 'No'}\n\n"
            
            # Count extraction methods used
            method_counts = {}
            for page_info in page_data:
                method = page_info.get('extraction_method', 'image_direct')
                method_counts[method] = method_counts.get(method, 0) + 1
            
            summary += "Extraction Methods Used:\n"
            for method, count in method_counts.items():
                summary += f"  {method.upper()}: {count} images\n"
            summary += "\n"
            
            for i, page_info in enumerate(page_data):
                method = page_info.get('extraction_method', 'image_direct')
                source = Path(page_info.get('source_file', '')).name
                summary += f"Image {i + 1} ({method.upper()}): {len(page_info['text'])} chars - {source}\n"
            
            save_intermediate_file(
                summary,
                "01_image_processing_summary.txt",
                self.intermediate_dir,
                "Image processing summary"
            )
        
        print(f"✅ Processed {len(page_data)} images with o3-pro enhanced analysis")
        
        # Enhanced image analysis diagnostics
        all_text = "\n".join([page['text'] for page in page_data])
        diagnosis = {
            "input_type": "images",
            "input_folder": input_folder,
            "image_count": len(page_data),
            "total_characters": len(all_text),
            "avg_chars_per_image": len(all_text) // len(page_data) if page_data else 0,
            "extraction_quality": "image_based",
            "has_ocr": HAS_MARKITDOWN,
            "analysis_capability": "full_visual"
        }
        self.latest_diagnostics = diagnosis
        
        print("\n" + "="*70)
        print("🧠 EDISON PRO - IMAGE PROCESSING DIAGNOSTICS")
        print("="*70)
        print(f"📁 Input Folder: {input_folder}")
        print(f"🖼️  Images Processed: {diagnosis['image_count']}")
        print(f"📝 Total Characters: {diagnosis['total_characters']:,}")
        print(f"📊 Avg per Image: {diagnosis['avg_chars_per_image']:,}")
        print(f"🔧 OCR Available: {'Yes' if diagnosis['has_ocr'] else 'No'}")
        print(f"🎯 Analysis Type: Direct image analysis with o3-pro visual reasoning")
        print(f"🚀 Capability: Full o3-pro enhanced visual analysis available")
        print("="*70 + "\n")
        
        # Process using existing enhanced pipeline
        processed_pages = await self._process_pages_parallel(page_data)
        
        # Create enhanced chunks
        if self.enable_smart_chunking:
            final_chunks = await self._create_smart_chunks_pro(processed_pages)
        else:
            final_chunks = self._create_overlapping_chunks(processed_pages)
        
        return final_chunks

    async def process_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process PDF with enhanced capabilities for o3-pro."""
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        routing_plan = {
            "document_type": "unknown",
            "recommended_primary": "pymupdf",
            "recommended_fallback": "markitdown" if HAS_MARKITDOWN else "none",
            "prefer_markitdown": False,
            "prioritize_visual_analysis": False,
            "is_protected": False,
            "reasons": ["Default routing"],
            "metrics": {"pdf_path": pdf_path, "total_pages": total_pages},
        }

        if PdfProcessingRouter is not None:
            try:
                router = PdfProcessingRouter(
                    has_markitdown=HAS_MARKITDOWN,
                    has_azure_di=self.di_client is not None,
                )
                routing_plan = router.plan(pdf_path).to_dict()
            except Exception as e:
                print(f"⚠️  PDF router failed, falling back to default extraction path: {e}")

        print(f"🧭 PDF routing: {routing_plan.get('document_type', 'unknown')} -> {routing_plan.get('recommended_primary', 'pymupdf')}")
        for reason in routing_plan.get("reasons", [])[:3]:
            print(f"   • {reason}")

        if self.intermediate_dir:
            save_intermediate_json(
                routing_plan,
                "00_pdf_routing_plan.json",
                self.intermediate_dir,
                "PDF routing plan and classification",
            )
        
        print(f"📄 Processing {total_pages} pages with o3-pro enhanced analysis (max concurrent: {self.max_concurrent_pages})")
        
        # Extract all page data first
        page_data = []
        all_extracted_text = []  # For complete text dump
        markitdown_text = None
        
        # Try MarkItDown extraction first if available
        if HAS_MARKITDOWN:
            try:
                print("📋 Attempting MarkItDown extraction as fallback option...")
                md = MarkItDown()
                result = md.convert(pdf_path)
                markitdown_text = result.text_content if hasattr(result, 'text_content') else str(result)
                print(f"📋 MarkItDown extracted {len(markitdown_text)} characters total")
                
                # Save MarkItDown extraction if intermediate dir exists
                if self.intermediate_dir:
                    save_intermediate_file(
                        markitdown_text,
                        "00_markitdown_extraction.txt",
                        self.intermediate_dir,
                        "Complete MarkItDown extraction"
                    )
            except Exception as e:
                print(f"⚠️  MarkItDown extraction failed: {e}")
                markitdown_text = None
        
        for page_num in range(total_pages):
            page = doc[page_num]
            pymupdf_text = page.get_text()
            images = page.get_images()
            
            # Determine best text extraction method
            text = pymupdf_text
            extraction_method = "pymupdf"
            
            # Use MarkItDown if PyMuPDF extraction is poor and MarkItDown is available
            prefer_markitdown = routing_plan.get("prefer_markitdown", False)
            if markitdown_text and (
                prefer_markitdown
                or (len(pymupdf_text.strip()) < 50 and len(markitdown_text) > len(pymupdf_text) * 2)
            ):
                # Estimate this page's portion of MarkItDown text
                start_pos = int((page_num / total_pages) * len(markitdown_text))
                end_pos = int(((page_num + 1) / total_pages) * len(markitdown_text))
                text = markitdown_text[start_pos:end_pos]
                extraction_method = "markitdown_router" if prefer_markitdown else "markitdown"
                print(f"📄 Page {page_num + 1}: Using MarkItDown extraction ({len(text)} chars, {len(images)} images)")
            else:
                print(f"📄 Page {page_num + 1}: Using PyMuPDF extraction ({len(text)} chars, {len(images)} images)")
            
            # Save individual page text if intermediate dir exists
            if self.intermediate_dir:
                page_text_content = f"=== PAGE {page_num + 1} ({extraction_method.upper()}) ===\n\n{text}\n\n"
                all_extracted_text.append(page_text_content)
                
                # Save individual page text
                save_intermediate_file(
                    page_text_content,
                    f"page_{page_num + 1:03d}_extracted_text_{extraction_method}.txt",
                    self.intermediate_dir,
                    f"Page {page_num + 1} {extraction_method.upper()} text extraction"
                )
            
            # Convert page to image for vision analysis
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode()
            
            # Save page image if intermediate dir exists
            if self.intermediate_dir:
                save_intermediate_image(
                    img_base64,
                    f"page_{page_num + 1:03d}_image.png",
                    self.intermediate_dir,
                    f"Page {page_num + 1} rendered image"
                )
            
            page_data.append({
                "page_num": page_num,
                "text": text,
                "image": img_base64,
                "images": images,
                "extraction_method": extraction_method
            })
        
        # Save complete extracted text dump
        if self.intermediate_dir and all_extracted_text:
            complete_text = "\n".join(all_extracted_text)
            save_intermediate_file(
                complete_text,
                "00_complete_pymupdf_extraction.txt",
                self.intermediate_dir,
                "Complete PyMuPDF text extraction from all pages"
            )
            
            # Also save extraction summary
            summary = f"Text Extraction Summary\n{'=' * 40}\n\n"
            summary += f"Total Pages: {total_pages}\n"
            summary += f"Total Characters: {len(complete_text)}\n"
            summary += f"Average Characters per Page: {len(complete_text) // total_pages if total_pages > 0 else 0}\n"
            summary += f"MarkItDown Available: {'Yes' if HAS_MARKITDOWN else 'No'}\n\n"
            
            # Count extraction methods used
            method_counts = {}
            for page_info in page_data:
                method = page_info.get('extraction_method', 'pymupdf')
                method_counts[method] = method_counts.get(method, 0) + 1
            
            summary += "Extraction Methods Used:\n"
            for method, count in method_counts.items():
                summary += f"  {method.upper()}: {count} pages\n"
            summary += "\n"
            
            for i, page_info in enumerate(page_data):
                method = page_info.get('extraction_method', 'pymupdf')
                summary += f"Page {i + 1} ({method.upper()}): {len(page_info['text'])} chars, {len(page_info['images'])} images\n"
            
            save_intermediate_file(
                summary,
                "01_extraction_summary.txt",
                self.intermediate_dir,
                "Text extraction summary with methods"
            )
        
        doc.close()
        
        # Enhanced extraction diagnostics
        all_text = "\n".join([page['text'] for page in page_data])
        diagnosis = diagnose_pdf_extraction(pdf_path, all_text, total_pages)
        diagnosis["routing_plan"] = routing_plan
        diagnosis["pdf_classification"] = routing_plan.get("document_type", "unknown")
        log_extraction_diagnosis_pro(diagnosis)
        self.latest_diagnostics = diagnosis
        
        # Save detailed diagnosis to intermediate files
        if self.intermediate_dir:
            # Save extraction methods used
            method_counts = {}
            for page in page_data:
                method = page.get('extraction_method', 'pymupdf')
                method_counts[method] = method_counts.get(method, 0) + 1
                diagnosis['extraction_methods_used'].add(method)
            
            # Create comprehensive diagnosis report
            diagnosis_report = f"EDISON PRO - PDF Extraction Diagnosis\n{'=' * 60}\n\n"
            diagnosis_report += f"File: {diagnosis['pdf_path']}\n"
            diagnosis_report += f"Analysis Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            diagnosis_report += f"EXTRACTION RESULTS:\n"
            diagnosis_report += f"  Pages: {diagnosis['page_count']}\n"
            diagnosis_report += f"  Total Characters: {diagnosis['total_characters']:,}\n"
            diagnosis_report += f"  Average per Page: {diagnosis['avg_chars_per_page']:,}\n"
            diagnosis_report += f"  Quality: {diagnosis['extraction_quality']}\n\n"
            
            diagnosis_report += f"EXTRACTION METHODS USED:\n"
            for method, count in method_counts.items():
                diagnosis_report += f"  {method.upper()}: {count} pages\n"
            diagnosis_report += "\n"
            
            diagnosis_report += f"STATUS FLAGS:\n"
            diagnosis_report += f"  Protected PDF: {'YES' if diagnosis['is_protected'] else 'NO'}\n"
            diagnosis_report += f"  Scanned Images: {'YES' if diagnosis['is_scanned'] else 'NO'}\n"
            diagnosis_report += f"  Has Text Content: {'YES' if diagnosis['has_text'] else 'NO'}\n"
            diagnosis_report += f"  MarkItDown Available: {'YES' if diagnosis['markitdown_available'] else 'NO'}\n\n"
            
            if diagnosis['issues_detected']:
                diagnosis_report += f"ISSUES DETECTED:\n"
                for issue in diagnosis['issues_detected']:
                    diagnosis_report += f"  • {issue}\n"
                diagnosis_report += "\n"
            
            diagnosis_report += f"RECOMMENDATIONS:\n"
            for rec in diagnosis['recommendations']:
                diagnosis_report += f"  {rec}\n"
            diagnosis_report += "\n"
            
            diagnosis_report += f"ANALYSIS IMPACT:\n"
            if diagnosis['is_protected']:
                diagnosis_report += "  • o3-pro cannot analyze protected content\n"
                diagnosis_report += "  • Visual analysis will be limited\n"
                diagnosis_report += "  • Text reasoning capabilities unavailable\n"
            elif diagnosis['is_scanned']:
                diagnosis_report += "  • o3-pro will focus on visual element analysis\n"
                diagnosis_report += "  • Limited text-based reasoning\n"
                diagnosis_report += "  • MarkItDown OCR may improve results\n"
            else:
                diagnosis_report += "  • Full o3-pro reasoning capabilities available\n"
                diagnosis_report += "  • Both text and visual analysis optimal\n"
                diagnosis_report += "  • Enhanced reasoning with high effort setting\n"
            
            save_intermediate_file(
                diagnosis_report,
                "00_extraction_diagnosis.txt",
                self.intermediate_dir,
                "PDF extraction diagnosis report"
            )
            
            # Save diagnosis as JSON
            save_intermediate_json(
                diagnosis,
                "00_extraction_diagnosis.json",
                self.intermediate_dir,
                "PDF extraction diagnosis data"
            )
        
        # Process pages in parallel with enhanced analysis
        processed_pages = await self._process_pages_parallel(page_data)
        
        # Create enhanced chunks
        if self.enable_smart_chunking:
            final_chunks = await self._create_smart_chunks_pro(processed_pages)
        else:
            final_chunks = self._create_overlapping_chunks(processed_pages)
        
        return final_chunks
    
    async def _process_pages_parallel(self, page_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process pages in parallel with o3-pro enhanced analysis"""
        async def process_single_page(page_info: Dict[str, Any]) -> Dict[str, Any]:
            async with self._processing_semaphore:
                try:
                    structure_data = await self._analyze_page_structure_pro(
                        page_info["page_num"], 
                        page_info["text"], 
                        page_info["image"]
                    )
                    
                    return {
                        "page_num": page_info["page_num"],
                        "text": page_info["text"],
                        "image": page_info["image"],
                        "structure": structure_data,
                        "images": page_info["images"]
                    }
                except Exception as e:
                    print(f"⚠️  Error processing page {page_info['page_num']}: {str(e)}")
                    return {
                        "page_num": page_info["page_num"],
                        "text": page_info["text"],
                        "image": page_info["image"],
                        "structure": {
                            "diagram_type": "unknown",
                            "sections": [],
                            "references": [],
                            "components": [],
                            "dependencies": []
                        },
                        "images": page_info["images"]
                    }
        
        tasks = [process_single_page(page_info) for page_info in page_data]
        processed_pages = await asyncio.gather(*tasks)
        processed_pages.sort(key=lambda x: x["page_num"])
        return processed_pages
    
    async def _analyze_page_structure_pro(
        self, page_num: int, text: str, image_base64: str
    ) -> Dict[str, Any]:
        """Enhanced page structure analysis using o3-pro reasoning capabilities"""
        
        prompt = f"""You are an expert technical document analyst specializing in engineering drawings, enhanced with advanced reasoning capabilities.

{self._get_domain_context()}

ADVANCED REASONING PROCESS FOR o3-pro:
1. Deep Multi-Modal Analysis: Systematically examine both textual and visual elements
2. Pattern Recognition: Identify recurring symbols, layouts, and documentation standards
3. Contextual Understanding: Infer implicit relationships and dependencies
4. Technical Standards Mapping: Connect observed elements to industry standards
5. Predictive Analysis: Anticipate what additional information might be needed
6. Domain-Specific Recognition: Apply {self.domain} engineering expertise to identify specialized components and standards

ENHANCED TASK: Process this PDF page (page {page_num}) with deep reasoning:

PRIMARY ANALYSIS:
- Diagram type identification with confidence scoring (consider {self.domain} domain context)
- Comprehensive component cataloging with specifications (focus on {self.domain}-specific components)
- Spatial relationship mapping
- Cross-reference network analysis
- Standards compliance assessment (apply {self.domain}-relevant standards)

REASONING DEPTH:
- Why is this classified as this diagram type?
- What do the component arrangements suggest about system function?
- Which elements are critical vs. supplementary?
- How do standards influence the interpretation?
- What questions would an expert engineer ask?

Page text content:
{text[:3000]}

OUTPUT: Enhanced JSON object with reasoning traces:
{{
    "diagram_type": "type",
    "confidence_score": 0.95,
    "reasoning_summary": "Brief explanation of classification logic",
    "title_block": {{"drawing_number": "", "revision": "", "scale": "", "standards": []}},
    "sections": [{{"name": "", "bounding_box": {{}}, "type": "", "importance": "high|medium|low"}}],
    "references": ["ref1", "ref2"],
    "components": [{{
        "id": "comp1", 
        "type": "motor|pump|valve|...", 
        "specifications": {{}},
        "confidence": 0.9
    }}],
    "zones": ["A1", "A2"],
    "dependencies": ["page_x", "drawing_y"],
    "technical_standards": ["ANSI", "ISO", "NEMA"],
    "complexity_assessment": "simple|moderate|complex",
    "expert_insights": ["insight1", "insight2"]
}}"""

        # Use Responses API with enhanced input structure
        input_data = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_base64}"
                    }
                ]
            }
        ]

        response = await safe_responses_api_call(
            self.client,
            model=self.deployment_name,
            input=input_data,
            reasoning={"effort": "high"},
            max_output_tokens=32000
        )
        
        # Extract text from response output (handle o3-pro response structure)
        output_text = ""
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                # Check for message output (o3-pro returns type='message')
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                output_text += content_item.text
                    else:
                        print(f"⚠️  Warning: Message output has None content")
                # Check for reasoning output (o3-pro returns type='reasoning')
                elif hasattr(output_item, 'type') and output_item.type == 'reasoning':
                    # Skip reasoning, we only want the message content
                    pass
                # Fallback for other response formats
                elif hasattr(output_item, 'content') and output_item.content:
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            output_text += content_item.text
                elif hasattr(output_item, 'text'):
                    output_text += output_item.text
        
        if not output_text:
            print(f"⚠️  Warning: No text extracted from o3-pro response for page {page_num}")
            print(f"   Response status: {response.status if hasattr(response, 'status') else 'unknown'}")
            # Return a minimal structure to avoid breaking the pipeline
            return {
                "diagram_type": "unknown",
                "title_block": {},
                "sections": [],
                "references": [],
                "components": [],
                "dependencies": [],
                "technical_standards": [],
                "complexity_assessment": "unknown",
                "expert_insights": []
            }
        
        try:
            structure_data = json.loads(output_text)
            
            # Save intermediate structure analysis if dir exists
            if hasattr(self, 'intermediate_dir') and self.intermediate_dir:
                save_intermediate_json(
                    structure_data,
                    f"page_{page_num + 1:03d}_structure_analysis.json",
                    self.intermediate_dir,
                    f"Page {page_num + 1} structure analysis"
                )
                
                # Save human-readable structure summary
                summary = f"Page {page_num + 1} Structure Analysis\n{'=' * 50}\n\n"
                summary += f"Diagram Type: {structure_data.get('diagram_type', 'unknown')}\n"
                summary += f"Confidence: {structure_data.get('confidence_score', 0.5):.1%}\n"
                summary += f"Reasoning: {structure_data.get('reasoning_summary', 'N/A')}\n\n"
                
                if structure_data.get('components'):
                    summary += f"Components ({len(structure_data['components'])}):\n"
                    for comp in structure_data['components'][:10]:  # First 10
                        summary += f"  - {comp.get('id', 'N/A')}: {comp.get('type', 'unknown')}\n"
                    if len(structure_data['components']) > 10:
                        summary += f"  ... and {len(structure_data['components']) - 10} more\n"
                    summary += "\n"
                
                if structure_data.get('expert_insights'):
                    summary += "Expert Insights:\n"
                    for insight in structure_data['expert_insights']:
                        summary += f"  • {insight}\n"
                    summary += "\n"
                
                save_intermediate_file(
                    summary,
                    f"page_{page_num + 1:03d}_structure_summary.txt",
                    self.intermediate_dir,
                    f"Page {page_num + 1} structure summary"
                )
            
            return structure_data
        except json.JSONDecodeError:
            # Fallback structure if JSON parsing fails
            fallback_structure = {
                "diagram_type": "unknown",
                "confidence_score": 0.5,
                "reasoning_summary": "Analysis completed but format parsing failed",
               
                "sections": [],
                "references": [],
                "components": [],
                "dependencies": [],
                "technical_standards": [],
                "complexity_assessment": "unknown",
                "expert_insights": []
            }
            
            # Save fallback info if dir exists
            if hasattr(self, 'intermediate_dir') and self.intermediate_dir:
                save_intermediate_json(
                    fallback_structure,
                    f"page_{page_num + 1:03d}_structure_analysis_fallback.json",
                    self.intermediate_dir,
                    f"Page {page_num + 1} fallback structure"
                )
            
            return fallback_structure
    
    async def _create_smart_chunks_pro(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced smart chunking with o3-pro reasoning"""
        print("🧠 Creating intelligent chunks with o3-pro enhanced boundary detection...")
        
        chunks = []
        current_chunk_pages = []
        current_chunk_type = None
        
        for i, page in enumerate(pages):
            page_type = page["structure"].get("diagram_type", "unknown")
            page_complexity = page["structure"].get("complexity_assessment", "moderate")
            page_components = page["structure"].get("components", [])
            
            # Enhanced decision logic for o3-pro
            should_start_new_chunk = (
                # Different diagram type with high confidence
                (current_chunk_type and page_type != current_chunk_type and 
                 page["structure"].get("confidence_score", 0) > 0.8) or
                # High complexity pages get their own chunks
                (page_complexity == "complex") or
                # Many high-confidence components (likely new system)
                (len([c for c in page_components if c.get("confidence", 0) > 0.8]) > 8) or
                # Explicit boundaries from standards
                (any("sheet" in str(ref).lower() for ref in page["structure"].get("references", []))) or
                # Force new chunk every 4 pages (increased for o3-pro)
                len(current_chunk_pages) >= 4
            )
            
            if should_start_new_chunk and current_chunk_pages:
                chunk = await self._create_multi_page_chunk_pro(current_chunk_pages, len(chunks))
                chunks.append(chunk)
                current_chunk_pages = []
            
            current_chunk_pages.append(page)
            current_chunk_type = page_type if page_type != "unknown" else current_chunk_type
        
        # Handle remaining pages
        if current_chunk_pages:
            chunk = await self._create_multi_page_chunk_pro(current_chunk_pages, len(chunks))
            chunks.append(chunk)
        
        # Add enhanced overlap chunks
        final_chunks = chunks.copy()
        for i in range(len(chunks) - 1):
            overlap_chunk = self._create_overlap_chunk_pro(chunks[i], chunks[i + 1], i)
            final_chunks.append(overlap_chunk)
        
        # Save chunking results if intermediate dir exists
        if hasattr(self, 'intermediate_dir') and self.intermediate_dir:
            chunking_summary = f"Smart Chunking Results\n{'=' * 40}\n\n"
            chunking_summary += f"Total Pages Processed: {len(pages)}\n"
            chunking_summary += f"Main Chunks Created: {len(chunks)}\n"
            chunking_summary += f"Overlap Chunks: {len(final_chunks) - len(chunks)}\n"
            chunking_summary += f"Total Final Chunks: {len(final_chunks)}\n\n"
            
            for i, chunk in enumerate(final_chunks):
                chunk_type = "Overlap" if "overlap" in chunk['chunk_id'] else "Main"
                pages_str = ", ".join(map(str, [p + 1 for p in chunk['pages']]))
                chunking_summary += f"Chunk {i + 1} ({chunk_type}): Pages {pages_str}\n"
                chunking_summary += f"  ID: {chunk['chunk_id']}\n"
                chunking_summary += f"  Content Length: {len(chunk['content'])} chars\n"
                if chunk.get('structure', {}).get('diagram_type'):
                    chunking_summary += f"  Diagram Type: {chunk['structure']['diagram_type']}\n"
                chunking_summary += "\n"
            
            save_intermediate_file(
                chunking_summary,
                "02_chunking_summary.txt",
                self.intermediate_dir,
                "Smart chunking results summary"
            )
            
            # Save individual chunk contents
            for i, chunk in enumerate(final_chunks):
                chunk_content = f"Chunk: {chunk['chunk_id']}\n"
                chunk_content += f"Pages: {[p + 1 for p in chunk['pages']]}\n"
                chunk_content += f"Type: {chunk.get('structure', {}).get('diagram_type', 'unknown')}\n"
                chunk_content += f"Content Length: {len(chunk['content'])} characters\n"
                chunk_content += "=" * 60 + "\n\n"
                chunk_content += chunk['content']
                
                save_intermediate_file(
                    chunk_content,
                    f"chunk_{i + 1:03d}_{chunk['chunk_id']}.txt",
                    self.intermediate_dir,
                    f"Chunk {i + 1} content"
                )
        
        print(f"   ✓ Created {len(chunks)} intelligent chunks with {len(final_chunks) - len(chunks)} enhanced overlaps")
        return final_chunks
    
    async def _create_multi_page_chunk_pro(self, pages: List[Dict[str, Any]], chunk_index: int) -> Dict[str, Any]:
        """Create enhanced multi-page chunk with o3-pro insights"""
        if len(pages) == 1:
            page = pages[0]
            return {
                "chunk_id": f"pro_chunk_{chunk_index}",
                "pages": [page["page_num"]],
                "content": page["text"],
                "image": page["image"],
                "structure": page["structure"],
                "metadata": self._extract_metadata_pro(page)
            }
        
        # Enhanced combination for multiple pages
        combined_text = "\n\n--- PAGE BOUNDARY ---\n\n".join([p["text"] for p in pages])
        page_numbers = [p["page_num"] for p in pages]
        
        # Merge structures with enhanced reasoning
        merged_structure = await self._merge_page_structures_pro([p["structure"] for p in pages])
        
        return {
            "chunk_id": f"pro_chunk_{chunk_index}",
            "pages": page_numbers,
            "content": combined_text,
            "image": pages[0]["image"],
            "structure": merged_structure,
            "metadata": self._extract_multi_page_metadata_pro(pages)
        }
    
    async def _merge_page_structures_pro(self, structures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced structure merging with o3-pro reasoning"""
        merged = {
            "diagram_type": structures[0].get("diagram_type", "unknown"),
            "confidence_score": sum(s.get("confidence_score", 0.5) for s in structures) / len(structures),
            "reasoning_summary": "Merged analysis from multiple related pages",
            "title_block": structures[0].get("title_block", {}),
            "sections": [],
            "references": [],
            "components": [],
            "zones": [],
            "dependencies": [],
            "technical_standards": [],
            "complexity_assessment": "moderate",
            "expert_insights": []
        }
        
        # Aggregate with enhanced logic
        all_standards = set()
        all_insights = []
        max_complexity = "simple"
        
        for structure in structures:
            merged["sections"].extend(structure.get("sections", []))
            merged["references"].extend(structure.get("references", []))
            merged["components"].extend(structure.get("components", []))
            merged["zones"].extend(structure.get("zones", []))
            merged["dependencies"].extend(structure.get("dependencies", []))
            all_standards.update(structure.get("technical_standards", []))
            all_insights.extend(structure.get("expert_insights", []))
            
            # Upgrade complexity assessment
            complexity = structure.get("complexity_assessment", "simple")
            if complexity == "complex":
                max_complexity = "complex"
            elif complexity == "moderate" and max_complexity == "simple":
                max_complexity = "moderate"
        
        # Remove duplicates and finalize
        for key in ["references", "components", "zones", "dependencies"]:
            if key == "components":
                # Keep unique components by ID
                seen_ids = set()
                unique_components = []
                for comp in merged[key]:
                    comp_id = comp.get("id", str(comp))
                    if comp_id not in seen_ids:
                        unique_components.append(comp)
                        seen_ids.add(comp_id)
                merged[key] = unique_components
            else:
                merged[key] = list(set(merged[key]))
        
        merged["technical_standards"] = list(all_standards)
        merged["complexity_assessment"] = max_complexity
        merged["expert_insights"] = list(set(all_insights))
        
        return merged
    
    def _create_overlap_chunk_pro(self, chunk1: Dict[str, Any], chunk2: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Enhanced overlap chunk for o3-pro with better context preservation"""
        # Larger overlap for better context (increased for o3-pro)
        text1_end = chunk1["content"][-1200:] if len(chunk1["content"]) > 1200 else chunk1["content"]
        text2_start = chunk2["content"][:1200] if len(chunk2["content"]) > 1200 else chunk2["content"]
        
        overlap_content = text1_end + "\n\n--- INTELLIGENT BOUNDARY ---\n\n" + text2_start
        
        return {
            "chunk_id": f"pro_overlap_{index}_{index+1}",
            "pages": chunk1["pages"] + chunk2["pages"],
            "content": overlap_content,
            "image": chunk1["image"],
            "structure": chunk1["structure"],
            "metadata": chunk1["metadata"]
        }
    
    def _extract_metadata_pro(self, page: Dict[str, Any]) -> ChunkMetadata:
        """Enhanced metadata extraction for o3-pro"""
        structure = page["structure"]
        
        return ChunkMetadata(
            chunk_id="",
            page_numbers=[page["page_num"]],
            diagram_type=structure.get("diagram_type"),
            scale=structure.get("title_block", {}).get("scale"),
            reference_numbers=structure.get("references", []),
            components=[comp.get("id", str(comp)) for comp in structure.get("components", [])],
            bounding_box=None,
            dependencies=structure.get("dependencies", []),
            source_file=page.get("source_file")
        )
    
    def _extract_multi_page_metadata_pro(self, pages: List[Dict[str, Any]]) -> ChunkMetadata:
        """Enhanced multi-page metadata extraction for o3-pro"""
        page_numbers = [p["page_num"] for p in pages]
        
        all_components = []
        all_references = []
        all_dependencies = []
        diagram_types = set()
        
        for page in pages:
            structure = page["structure"]
            components = structure.get("components", [])
            all_components.extend([comp.get("id", str(comp)) for comp in components])
            all_references.extend(structure.get("references", []))
            all_dependencies.extend(structure.get("dependencies", []))
            if structure.get("diagram_type"):
                diagram_types.add(structure["diagram_type"])
        
        # Determine primary diagram type with enhanced logic
        primary_type = None
        if len(diagram_types) == 1:
            primary_type = list(diagram_types)[0]
        elif diagram_types:
            # Prefer specific types over unknown
            non_unknown = [t for t in diagram_types if t != "unknown"]
            primary_type = non_unknown[0] if non_unknown else "unknown"
        
        return ChunkMetadata(
            chunk_id="",
            page_numbers=page_numbers,
            diagram_type=primary_type,
            scale=pages[0]["structure"].get("title_block", {}).get("scale"),
            reference_numbers=list(set(all_references)),
            components=list(set(all_components)),
            bounding_box=None,
            dependencies=list(set(all_dependencies)),
            source_file=pages[0].get("source_file") if pages else None
        )
    
    def _create_overlapping_chunks(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Traditional overlapping chunks method"""
        chunks = []
        
        for i, page in enumerate(pages):
            chunk = {
                "chunk_id": f"chunk_{i}",
                "pages": [i],
                "content": page["text"],
                "image": page["image"],
                "structure": page["structure"],
                "metadata": self._extract_metadata_pro(page)
            }
            chunks.append(chunk)
            
            if i < len(pages) - 1:
                overlap_chunk = {
                    "chunk_id": f"chunk_{i}_{i+1}_overlap",
                    "pages": [i, i+1],
                    "content": page["text"][-500:] + "\n\n--- PAGE BREAK ---\n\n" + pages[i+1]["text"][:500],
                    "image": page["image"],
                    "structure": page["structure"],
                    "metadata": self._extract_metadata_pro(page)
                }
                chunks.append(overlap_chunk)
        
        return chunks


# ============================================================================
# AGENT 2: VISUAL ELEMENT EXTRACTOR - Enhanced for o3-pro
# ============================================================================

class VisualElementExtractorPro:
    """Enhanced visual element extractor using o3-pro reasoning capabilities"""
    
    def __init__(self, client: OpenAI, deployment_name: str, reasoning_effort: str = "high"):
        self.client = client
        self.deployment_name = deployment_name
        self.reasoning_effort = reasoning_effort
    
    async def extract_elements(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Extract visual elements with o3-pro enhanced reasoning"""
        
        diagram_type = chunk["metadata"].diagram_type or "unknown"
        
        prompt = f"""You are a senior engineering drawing interpreter with advanced reasoning capabilities, enhanced for o3-pro analysis.

ADVANCED REASONING FRAMEWORK FOR o3-pro:
1. Multi-Layer Visual Analysis: Examine symbols, connections, annotations, and spatial relationships
2. Domain Expertise Application: Apply specialized knowledge for {diagram_type} diagrams
3. Pattern Recognition: Identify standard symbols and custom notations
4. Inference Engine: Deduce implicit connections and relationships
5. Uncertainty Quantification: Assess confidence in interpretations

ENHANCED SYSTEMATIC ANALYSIS:
First, establish context:
- Document type: {diagram_type}
- Industry standards: ISO, ANSI, IEC, NEMA (as applicable)
- Drawing conventions and symbol libraries

Then, perform EXHAUSTIVE deep analysis:
1. SYMBOL IDENTIFICATION: Catalog EVERY SINGLE symbol, icon, and graphical element
   - Standard symbols (electrical, mechanical, P&ID, civil)
   - Custom symbols and notations
   - Equipment symbols (transformers, valves, pumps, switches, etc.)
   - Connection points, terminals, junction boxes
   - Measurement and instrumentation symbols

2. CONNECTION ANALYSIS: Trace ALL lines and connections
   - Electrical wires, cables, and conduits
   - Piping and ductwork
   - Mechanical linkages
   - Signal and control lines
   - Hidden or implied connections

3. ANNOTATION PROCESSING: Extract EVERY piece of text
   - Component labels and identifiers
   - Specifications and ratings (voltage, current, pressure, size)
   - Dimensions and measurements
   - Callouts and keynotes
   - Reference designators
   - Part numbers and model numbers
   - Notes and warnings

4. SPATIAL REASONING: Map complete layout
   - Component positions and orientations
   - Spacing and clearances
   - Zones and boundaries
   - Coordinate systems
   - Scale and grid references

5. SYSTEM INTEGRATION: Understand relationships
   - How components interconnect
   - Signal flow and power distribution
   - Control logic and sequences
   - Dependencies and hierarchies

CRITICAL: Extract AT LEAST 20-50 elements per page. Include:
- Every labeled component
- Every line and connection
- Every text annotation
- Every dimension
- All table entries and legends
- Title blocks and drawing metadata

REASONING DEPTH:
- What engineering principles govern this design?
- Which elements are critical for system function?
- What standards or codes apply to each component?
- How do tolerances and specifications relate?

Extract ALL visual elements with enhanced metadata (be COMPREHENSIVE):

Page context (first 2000 chars):
{chunk['content'][:2000]}

OUTPUT: Enhanced JSON array with reasoning:
{{
    "analysis_summary": "Brief overview of visual analysis",
    "elements": [
        {{
            "element_id": "unique_id",
            "element_type": "symbol|line|text|dimension|table|legend|callout",
            "coordinates": {{"x": 0.5, "y": 0.3, "width": 0.1, "height": 0.05}},
            "properties": {{
                "symbol_standard": "ISO 14617|ANSI Y32|IEC 60617",
                "line_type": "solid|dashed|dotted",
                "color": "black|red|blue",
                "thickness": "thin|medium|thick",
                "material": "steel|copper|aluminum",
                "specifications": {{}}
            }},
            "connections": ["element_id1", "element_id2"],
            "text_content": "extracted text",
            "confidence": 0.95,
            "engineering_significance": "brief explanation",
            "standards_reference": "applicable standard"
        }}
    ],
    "system_insights": ["insight1", "insight2"],
    "quality_assessment": {{
        "drawing_clarity": "excellent|good|fair|poor",
        "completeness": "complete|mostly_complete|incomplete",
        "standard_compliance": "compliant|mostly_compliant|non_compliant"
    }}
}}"""

        # Use Responses API with enhanced reasoning
        input_data = [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{chunk['image']}"
                    }
                ]
            }
        ]

        response = await safe_responses_api_call(
            self.client,
            model=self.deployment_name,
            input=input_data,
            reasoning={"effort": "high"},
            max_output_tokens=32000
        )
        
        # Extract text from response (handle o3-pro response structure)
        output_text = ""
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                # Check for message output (o3-pro returns type='message')
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                output_text += content_item.text
                    else:
                        print(f"⚠️  Warning: Message output has None content for chunk {chunk.get('chunk_id', 'unknown')}")
                # Check for reasoning output (o3-pro returns type='reasoning')
                elif hasattr(output_item, 'type') and output_item.type == 'reasoning':
                    # Skip reasoning, we only want the message content
                    pass
                # Fallback for other response formats
                elif hasattr(output_item, 'content') and output_item.content:
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            output_text += content_item.text
                elif hasattr(output_item, 'text'):
                    output_text += output_item.text
        
        if not output_text:
            print(f"⚠️  Warning: No text extracted from o3-pro response for chunk {chunk.get('chunk_id', 'unknown')}")
            print(f"   Response status: {response.status if hasattr(response, 'status') else 'unknown'}")
            return {}
        
        try:
            elements_data = json.loads(output_text)
        except json.JSONDecodeError:
            print(f"⚠️  Failed to parse visual elements JSON for chunk {chunk.get('chunk_id', 'unknown')}")
            return {}
        
        elements = elements_data.get("elements", [])
        if not isinstance(elements, list):
            elements = []
            elements_data["elements"] = elements
        
        # Save visual elements analysis if client has intermediate_dir
        if (hasattr(self.client, '_orchestrator') and 
            hasattr(self.client._orchestrator, 'intermediate_dir') and 
            self.client._orchestrator.intermediate_dir):
            
            intermediate_dir = self.client._orchestrator.intermediate_dir
            chunk_id = chunk.get('chunk_id', 'unknown')
            
            # Save raw analysis JSON
            save_intermediate_json(
                elements_data,
                f"visual_elements_{chunk_id}_analysis.json",
                intermediate_dir,
                f"Visual elements analysis for {chunk_id}"
            )
            
            # Save human-readable summary
            elements_summary = f"Visual Elements Analysis: {chunk_id}\n{'=' * 60}\n\n"
            elements_summary += f"Total Elements Found: {len(elements)}\n"
            elements_summary += f"Analysis Quality: {elements_data.get('quality_assessment', {}).get('drawing_clarity', 'unknown')}\n\n"
            
            if elements_data.get('analysis_summary'):
                elements_summary += f"Analysis Summary:\n{elements_data['analysis_summary']}\n\n"
            
            # Group elements by type
            element_types = {}
            for elem in elements:
                elem_type = elem.get("element_type", "unknown")
                if elem_type not in element_types:
                    element_types[elem_type] = []
                element_types[elem_type].append(elem)
            
            elements_summary += "Elements by Type:\n"
            for elem_type, type_elements in element_types.items():
                elements_summary += f"  {elem_type}: {len(type_elements)} elements\n"
                for elem in type_elements[:3]:  # Show first 3 of each type
                    elem_id = elem.get("element_id", "unknown")
                    elem_text = elem.get("text_content") or "no text"
                    elements_summary += f"    - {elem_id}: {elem_text}\n"
                if len(type_elements) > 3:
                    elements_summary += f"    ... and {len(type_elements) - 3} more\n"
                elements_summary += "\n"
            
            if elements_data.get('system_insights'):
                elements_summary += "System Insights:\n"
                for insight in elements_data['system_insights']:
                    elements_summary += f"  • {insight}\n"
                elements_summary += "\n"
            
            save_intermediate_file(
                elements_summary,
                f"visual_elements_{chunk_id}_summary.txt",
                intermediate_dir,
                f"Visual elements summary for {chunk_id}"
            )
        
        return elements_data


# ============================================================================
# ENHANCED ORCHESTRATOR for o3-pro
# ============================================================================

class DiagramAnalysisOrchestratorPro:
    """Enhanced orchestrator using o3-pro reasoning capabilities"""
    
    def __init__(self, reasoning_effort: str = "high"):
        # Load and validate Azure OpenAI Pro configuration
        azure_pro_endpoint = os.getenv("AZURE_OPENAI_PRO_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
        deployment_name = os.getenv("AZURE_OPENAI_PRO_DEPLOYMENT_NAME") or os.getenv("AZURE_DEPLOYMENT_PRO_NAME") or "o3-pro"
        
        print(f"\n🔧 EDISON PRO Configuration:")
        print(f"   Endpoint: {azure_pro_endpoint[:50] + '...' if azure_pro_endpoint and len(azure_pro_endpoint) > 50 else azure_pro_endpoint or 'NOT SET'}")
        print(f"   API Key: {'SET' if azure_api_key else 'NOT SET'}")
        print(f"   Deployment: {deployment_name}")
        
        if not azure_pro_endpoint:
            print("\n⚠️  AZURE_OPENAI_PRO_ENDPOINT not set. Trying fallback to standard endpoint...")
            azure_pro_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if azure_pro_endpoint:
                print(f"   Using fallback endpoint: {azure_pro_endpoint[:50]}...")
            else:
                raise ValueError("Either AZURE_OPENAI_PRO_ENDPOINT or AZURE_OPENAI_ENDPOINT must be set")
                
        if not azure_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY must be set for EDISON Pro")
        
        # Initialize AzureOpenAI client — sends api-key header (not Bearer token)
        api_version = os.getenv("AZURE_OPENAI_PRO_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2025-03-01-preview")
        
        print(f"   API Version: {api_version}")
        
        self.client = AzureOpenAI(
            api_key=azure_api_key,
            azure_endpoint=azure_pro_endpoint.rstrip('/'),
            api_version=api_version
        )

        self.deployment_name = deployment_name
        self.reasoning_effort = reasoning_effort
        self.context_manager = ContextManagerPro(max_working_tokens=100000)  # Increased for o3-pro
        self.intermediate_dir = None  # Will be set during analysis
        self.log_file = None  # For logging output to file
        
        print(f"\n✅ EDISON PRO initialized with {self.deployment_name}")
        print(f"   Ready for o3-pro enhanced analysis with Responses API")
        
        # Test configuration
        self._test_configuration()
        
        # Store orchestrator reference in client for agents to access
        self.client._orchestrator = self
        
        # Initialize enhanced agents (preprocessor will get intermediate_dir during analysis)
        self.preprocessor = None  # Will be initialized with intermediate_dir
        self.planner = PlanningAgentPro(self.client, self.deployment_name)  # Phase 0 planning
        self.visual_extractor = VisualElementExtractorPro(self.client, self.deployment_name, self.reasoning_effort)
        
        # Storage
        self.processed_chunks = []
        self.visual_elements_by_chunk = {}
        self.interpretations_by_chunk = {}
        self.cross_references = []
        self.synthesis_result = None
        self.analysis_plan = None  # Will be set by planning phase
        self.sheet_correlations = {}
        self.quality_summary = {}
        # Q&A history for few-shot injection (most recent exchanges first)
        self.qa_history: list = []  # List of (question, answer) tuples
    
    def _start_logging(self):
        """Start logging all output to file in intermediate directory"""
        if self.intermediate_dir and not self.log_file:
            log_path = self.intermediate_dir / "00_analysis_log.txt"
            try:
                self.log_file = open(log_path, 'w', encoding='utf-8', buffering=1)
                print(f"📋 Logging to: {log_path}")
                self._log(f"EDISON PRO Analysis Log\n{'=' * 80}\n")
                self._log(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._log(f"Model: {self.deployment_name}\n")
                self._log(f"Reasoning Effort: {self.reasoning_effort}\n")
                self._log(f"{'=' * 80}\n\n")
            except Exception as e:
                print(f"⚠️  Could not create log file: {e}")
    
    def _log(self, message: str):
        """Write message to both console and log file"""
        print(message, end='')
        if self.log_file and not self.log_file.closed:
            try:
                self.log_file.write(message)
                self.log_file.flush()
            except Exception:
                pass
    
    def _stop_logging(self):
        """Stop logging and close log file"""
        if self.log_file:
            try:
                self._log(f"\n{'=' * 80}\n")
                self._log(f"Completed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                self._log(f"{'=' * 80}\n")
                self.log_file.close()
            except:
                pass
            finally:
                self.log_file = None
    
    def _test_configuration(self):
        """Test Azure OpenAI configuration with a simple API call"""
        try:
            print("\n🧪 Testing Azure OpenAI o3-pro configuration...")
            
            # Test with a minimal Responses API call
            import asyncio
            
            async def test_call():
                try:
                    test_input = [
                        {
                            "role": "user", 
                            "content": [
                                {"type": "input_text", "text": "Hello, are you working?"}
                            ]
                        }
                    ]
                    
                    response = await safe_responses_api_call(
                        self.client,
                        model=self.deployment_name,
                        input=test_input,
                        reasoning={"effort": "high"},
                        max_output_tokens=100
                    )
                    
                    print("   ✅ Configuration test successful!")
                    return True
                    
                except Exception as e:
                    print(f"   ❌ Configuration test failed: {str(e)[:100]}")
                    print("   ⚠️  This may indicate deployment or model access issues")
                    return False
            
            # Run test if we're in an async context, otherwise skip
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    print("   ⏭️  Skipping config test (already in async context)")
                else:
                    asyncio.run(test_call())
            except RuntimeError:
                print("   ⏭️  Skipping config test (no event loop)")
                
        except Exception as e:
            print(f"   ⚠️  Could not perform configuration test: {e}")
    
    def _image_to_bytes(self, img: Image.Image) -> bytes:
        """Convert PIL Image to bytes for planning agent."""
        from io import BytesIO
        buffer = BytesIO()
        
        # Convert to RGB if needed
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # Resize if too large (for planning efficiency)
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _summarize_sheet_correlations(self, chunks: List[Dict[str, Any]]):
        """Build lightweight sheet correlation summary for downstream agents."""
        sheet_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "pages": set(),
            "diagram_types": Counter(),
            "references": Counter(),
            "components": Counter()
        })

        for chunk in chunks:
            metadata = chunk.get("metadata")
            if not isinstance(metadata, ChunkMetadata):
                continue

            if metadata.source_file:
                sheet_id = Path(metadata.source_file).stem
            else:
                sheet_id = "pages_" + "_".join(str(p) for p in metadata.page_numbers)

            sheet_entry = sheet_map[sheet_id]
            sheet_entry["pages"].update(metadata.page_numbers)

            if metadata.diagram_type:
                sheet_entry["diagram_types"][metadata.diagram_type] += 1

            for ref in metadata.reference_numbers:
                sheet_entry["references"][ref] += 1

            for component in metadata.components:
                sheet_entry["components"][component] += 1

        self.sheet_correlations = {}
        for sheet_id, data in sheet_map.items():
            self.sheet_correlations[sheet_id] = {
                "page_span": sorted(data["pages"]),
                "top_diagram_types": data["diagram_types"].most_common(2),
                "top_references": [ref for ref, _ in data["references"].most_common(5)],
                "total_components": sum(data["components"].values())
            }

        if self.sheet_correlations:
            print("   🔁 Sheet correlation overview ready:")
            for sheet_id, summary in list(self.sheet_correlations.items())[:3]:
                types = ", ".join(t for t, _ in summary["top_diagram_types"]) or "unknown"
                refs = ", ".join(summary["top_references"]) or "none"
                pages = ",".join(str(p + 1) for p in summary["page_span"])
                print(f"      • {sheet_id}: pages {pages} | types {types} | refs {refs}")

    def _aggregate_quality_metrics(self, visual_results: List[Dict[str, Any]]):
        """Aggregate drawing quality metrics from visual analysis."""
        if not visual_results:
            self.quality_summary = {}
            return

        clarity_counter: Counter = Counter()
        completeness_counter: Counter = Counter()
        compliance_counter: Counter = Counter()
        insight_samples: List[str] = []

        for result in visual_results:
            if not isinstance(result, dict):
                continue
            qa = result.get("quality_assessment", {})
            clarity = qa.get("drawing_clarity")
            completeness = qa.get("completeness")
            compliance = qa.get("standard_compliance")

            if clarity:
                clarity_counter[clarity] += 1
            if completeness:
                completeness_counter[completeness] += 1
            if compliance:
                compliance_counter[compliance] += 1

            insights = result.get("system_insights", [])
            for insight in insights[:2]:
                if insight not in insight_samples:
                    insight_samples.append(insight)

        self.quality_summary = {
            "clarity": clarity_counter.most_common(),
            "completeness": completeness_counter.most_common(),
            "standard_compliance": compliance_counter.most_common(),
            "insights": insight_samples[:5]
        }

    def _print_quality_summary(self):
        """Print aggregated quality feedback if available."""
        if not self.quality_summary:
            return

        print("   📏 Scan quality feedback:")
        clarity = self.quality_summary.get("clarity", [])
        if clarity:
            top_clarity = ", ".join(f"{label} x{count}" for label, count in clarity[:2])
            print(f"      • Clarity: {top_clarity}")

        completeness = self.quality_summary.get("completeness", [])
        if completeness:
            top_completeness = ", ".join(f"{label} x{count}" for label, count in completeness[:2])
            print(f"      • Completeness: {top_completeness}")

        compliance = self.quality_summary.get("standard_compliance", [])
        if compliance:
            top_compliance = ", ".join(f"{label} x{count}" for label, count in compliance[:2])
            print(f"      • Standards: {top_compliance}")

        insights = self.quality_summary.get("insights", [])
        if insights:
            for insight in insights:
                print(f"      • Insight: {insight}")
    
    
    async def analyze_images_from_folder(self, input_folder: str, domain: str = "general", auto_plan: bool = True) -> Dict[str, Any]:
        """Execute enhanced image analysis from folder with o3-pro capabilities"""
        print(f"🚀 Starting o3-pro enhanced image analysis from {input_folder}")
        
        # Create intermediate files directory
        folder_name = Path(input_folder).name
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.intermediate_dir = Path(f"intermediate_files_{folder_name}_{timestamp}")
        self.intermediate_dir.mkdir(exist_ok=True)
        print(f"📁 Created intermediate files directory: {self.intermediate_dir}")
        
        # Start logging to file
        self._start_logging()
        
        # PHASE 0: PLANNING (if auto_plan enabled)
        if auto_plan:
            # Load images for planning
            image_files = get_supported_image_files(input_folder)
            if not image_files:
                raise ValueError(f"No supported images found in {input_folder}")
            
            # Prepare image data for planner
            image_data_list = []
            for img_path in image_files[:3]:  # Sample first 3 for planning
                try:
                    with Image.open(img_path) as img:
                        img_bytes = self._image_to_bytes(img)
                        image_data_list.append((img_bytes, os.path.basename(img_path)))
                except Exception as e:
                    print(f"⚠️  Could not load {img_path} for planning: {e}")
            
            if image_data_list:
                # Run planning phase
                user_hint = domain if domain != "general" else None
                self.analysis_plan = await self.planner.create_analysis_plan(image_data_list, user_hint)
                
                # Use plan recommendations
                domain = self.analysis_plan.agent_config["domain"]
                self.reasoning_effort = self.analysis_plan.agent_config["reasoning_effort"]
                max_concurrent = self.analysis_plan.agent_config["max_concurrent_pages"]
            else:
                print("⚠️  Could not load images for planning, using manual domain settings")
                max_concurrent = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))
        else:
            max_concurrent = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))
        
        # Display final domain configuration
        domain_display = domain.upper().replace(",", " + ")
        print(f"📋 Domain: {domain_display}")
        print(f"🧠 Reasoning Effort: {self.reasoning_effort.upper()}")
        
        # Initialize preprocessor with optimized settings
        self.preprocessor = DocumentPreprocessorPro(
            self.client,
            self.deployment_name,
            self.reasoning_effort,
            max_concurrent_pages=max_concurrent,
            enable_smart_chunking=os.getenv("ENABLE_SMART_CHUNKING", "true").lower() == "true",
            intermediate_dir=self.intermediate_dir,
            domain=domain
        )
        
        # Wrap in try-finally to ensure commit happens
        try:
            # Stage 1: Enhanced Image Processing
            print("\n🖼️  Stage 1: Enhanced image processing with o3-pro reasoning...")
            chunks = await self.preprocessor.process_images_from_folder(input_folder)
            self.processed_chunks = chunks
            print(f"   ✓ Created {len(chunks)} intelligent chunks from images")

            # Multi-stage planning feedback loop
            self._summarize_sheet_correlations(chunks)
            diagnostics = getattr(self.preprocessor, "latest_diagnostics", None)
            if self.analysis_plan:
                self.analysis_plan, plan_updates = self.planner.refine_plan_with_diagnostics(self.analysis_plan, diagnostics)
                if plan_updates:
                    print("   🔁 Plan refined based on preprocessing diagnostics:")
                    for update in plan_updates:
                        print(f"      • {update}")
                self.reasoning_effort = self.analysis_plan.agent_config.get("reasoning_effort", self.reasoning_effort)
                self.visual_extractor.reasoning_effort = self.reasoning_effort
                new_max = self.analysis_plan.agent_config.get("max_concurrent_pages")
                if new_max and new_max != self.preprocessor.max_concurrent_pages:
                    self.preprocessor.max_concurrent_pages = new_max
                    self.preprocessor._processing_semaphore = asyncio.Semaphore(new_max)
                    print(f"   ⚙️  Updated concurrency limit to {new_max} based on plan feedback")
            
            # Stage 2: Enhanced Visual Element Extraction
            print("👁️  Stage 2: Enhanced visual element extraction with o3-pro...")
            visual_tasks = [
                self.visual_extractor.extract_elements(chunk)
                for chunk in chunks
            ]
            visual_results = await asyncio.gather(*visual_tasks)
            
            for chunk, elements in zip(chunks, visual_results):
                self.visual_elements_by_chunk[chunk['chunk_id']] = elements
            
            total_elements = sum(
                len(result.get('elements', []))
                for result in visual_results
                if isinstance(result, dict)
            )
            print(f"   ✓ Extracted {total_elements} visual elements with enhanced reasoning")
            self._aggregate_quality_metrics(visual_results)
            self._print_quality_summary()
            
            # Stage 3: Build Context Index with Enhanced Embeddings
            print("💾 Stage 3: Building enhanced context index...")
            
            # Create embeddings subfolder for backup
            embeddings_dir = None
            if self.intermediate_dir:
                embeddings_dir = self.intermediate_dir / "embeddings"
                embeddings_dir.mkdir(exist_ok=True)
                self._log(f"   📁 Embeddings will be saved to: {embeddings_dir}\n")
            
            for chunk in chunks:
                chunk_id = chunk.get('chunk_id', 'unknown')
                try:
                    # Build enriched content with ALL analysis results
                    chunk_content = chunk.get('content', '')
                    if not chunk_content:
                        chunk_content = f"Image chunk {chunk_id}"
                    
                    # ADD STRUCTURE ANALYSIS TO CONTENT
                    structure = chunk.get('structure', {})
                    if structure:
                        chunk_content += "\n\n=== DIAGRAM STRUCTURE ANALYSIS ===\n\n"
                        
                        if structure.get('diagram_type'):
                            chunk_content += f"Diagram Type: {structure['diagram_type']}\n"
                        
                        if structure.get('confidence_score'):
                            chunk_content += f"Confidence: {structure['confidence_score']:.2%}\n"
                        
                        if structure.get('reasoning_summary'):
                            chunk_content += f"\nReasoning: {structure['reasoning_summary']}\n"
                        
                        # Add title block info
                        if structure.get('title_block'):
                            chunk_content += "\nTitle Block:\n"
                            title_block = structure['title_block']
                            for key, value in title_block.items():
                                if isinstance(value, list):
                                    chunk_content += f"  {key}: {', '.join(str(v) for v in value[:5])}\n"
                                else:
                                    chunk_content += f"  {key}: {value}\n"
                        
                        # Add sections
                        if structure.get('sections'):
                            chunk_content += f"\nSections ({len(structure['sections'])} detected):\n"
                            for section in structure['sections'][:10]:  # Top 10 sections
                                chunk_content += f"  • {section.get('name', 'Unnamed')}: {section.get('type', 'unknown')} (importance: {section.get('importance', 'medium')})\n"
                        
                        # Add components from structure
                        if structure.get('components'):
                            chunk_content += f"\nComponents ({len(structure['components'])} detected):\n"
                            for comp in structure['components'][:20]:  # Top 20 components
                                comp_id = comp.get('id', 'unknown')
                                comp_type = comp.get('type', 'unknown')
                                chunk_content += f"  • {comp_id}: {comp_type}\n"
                                if comp.get('specifications'):
                                    specs = comp['specifications']
                                    for key, value in list(specs.items())[:3]:  # Top 3 specs
                                        chunk_content += f"    - {key}: {value}\n"
                        
                        # Add references
                        if structure.get('references'):
                            chunk_content += f"\nReferences:\n"
                            for ref in structure['references'][:10]:
                                chunk_content += f"  • {ref}\n"
                    
                    # ADD VISUAL ELEMENTS TO CONTENT
                    visual_elements = self.visual_elements_by_chunk.get(chunk_id, {})
                    if visual_elements and isinstance(visual_elements, dict):
                        chunk_content += "\n\n=== VISUAL ELEMENTS ANALYSIS ===\n\n"
                        
                        # Add summary
                        summary_text = visual_elements.get('summary') or visual_elements.get('analysis_summary')
                        if summary_text:
                            chunk_content += f"Summary: {summary_text}\n\n"
                        
                        # Add elements by category
                        elements_payload = visual_elements.get('elements')
                        if isinstance(elements_payload, dict):
                            chunk_content += "Detected Elements:\n"
                            for category, items in elements_payload.items():
                                if items:
                                    chunk_content += f"\n{category.upper()} ({len(items)} items):\n"
                                    for item in items[:20]:  # Limit to 20 per category
                                        elem_id = item.get('id', item.get('element_id', 'unknown'))
                                        elem_desc = item.get('description') or item.get('text_content', '')
                                        elem_props = item.get('properties', {})
                                        chunk_content += f"  • {elem_id}: {elem_desc}\n"
                                        if isinstance(elem_props, dict):
                                            for key, value in list(elem_props.items())[:3]:
                                                chunk_content += f"    - {key}: {value}\n"
                        elif isinstance(elements_payload, list):
                            chunk_content += "Detected Elements:\n"
                            for item in elements_payload[:30]:  # Limit total items appended
                                elem_id = item.get('element_id', 'unknown')
                                elem_type = item.get('element_type', 'unknown')
                                elem_text = item.get('text_content') or item.get('engineering_significance', '')
                                chunk_content += f"  • {elem_id} [{elem_type}]: {elem_text}\n"
                                properties = item.get('properties', {})
                                if isinstance(properties, dict):
                                    for key, value in list(properties.items())[:2]:
                                        chunk_content += f"    - {key}: {value}\n"
                        
                        # Add insights
                        insights_payload = visual_elements.get('insights') or visual_elements.get('system_insights', [])
                        if insights_payload:
                            chunk_content += "\nSystem Insights:\n"
                            for insight in insights_payload[:10]:  # Top 10 insights
                                chunk_content += f"  • {insight}\n"
                        quality_payload = visual_elements.get('quality_assessment')
                        if isinstance(quality_payload, dict):
                            chunk_content += "\nQuality Assessment:\n"
                            for key, value in quality_payload.items():
                                chunk_content += f"  • {key.replace('_', ' ').title()}: {value}\n"
                    
                    self._log(f"   📝 Generating embedding for {chunk_id} ({len(chunk_content)} chars)...\n")
                    embedding = await self._generate_embedding_pro(chunk_content)
                    
                    if embedding:
                        self._log(f"   ✓ Embedding generated ({len(embedding)} dims)\n")
                    else:
                        self._log(f"   ⚠️  Empty embedding returned for {chunk_id}\n")
                    
                    self.context_manager.add_chunk(
                        chunk['chunk_id'],
                        chunk_content,
                        chunk['metadata'],
                        embedding
                    )
                    self._log(f"   ✓ Chunk {chunk_id} added to context manager\n")
                    
                    # Save embedding to file for backup/recovery
                    if embeddings_dir and embedding:
                        try:
                            import json
                            # Save embedding vector
                            emb_file = embeddings_dir / f"{chunk_id}_embedding.json"
                            with open(emb_file, 'w') as f:
                                json.dump({
                                    'chunk_id': chunk_id,
                                    'embedding': embedding,
                                    'dimensions': len(embedding)
                                }, f, indent=2)
                            
                            # Save content
                            content_file = embeddings_dir / f"{chunk_id}_content.txt"
                            with open(content_file, 'w', encoding='utf-8') as f:
                                f.write(chunk_content)
                            
                            # Save metadata
                            metadata_file = embeddings_dir / f"{chunk_id}_metadata.json"
                            metadata_dict = {
                                'page_numbers': chunk['metadata'].page_numbers,
                                'diagram_type': chunk['metadata'].diagram_type,
                                'scale': chunk['metadata'].scale,
                                'reference_numbers': chunk['metadata'].reference_numbers,
                                'components': chunk['metadata'].components,
                                'dependencies': chunk['metadata'].dependencies,
                                'source_file': chunk['metadata'].source_file
                            }
                            with open(metadata_file, 'w') as f:
                                json.dump(metadata_dict, f, indent=2)
                            
                            self._log(f"   💾 Saved embedding backup for {chunk_id}\n")
                        except Exception as save_error:
                            self._log(f"   ⚠️  Failed to save embedding backup: {save_error}\n")
                    
                except Exception as e:
                    error_msg = f"⚠️  Failed to process chunk {chunk_id}: {e}\n"
                    self._log(error_msg)
                    import traceback
                    self._log(f"   Traceback: {traceback.format_exc()}\n")
                    continue
            
            print("   ✓ Enhanced context index built with o3-pro capabilities")
            if embeddings_dir:
                print(f"   💾 Embeddings backed up to: {embeddings_dir}")
            
            # Save final analysis summary
            if self.intermediate_dir:
                final_summary = f"EDISON PRO Image Analysis Complete\n{'=' * 50}\n\n"
                final_summary += f"Input Folder: {input_folder}\n"
                final_summary += f"Analysis Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                final_summary += f"Model Used: {self.deployment_name}\n"
                final_summary += f"Domain: {domain}\n\n"
                
                final_summary += f"Processing Results:\n"
                final_summary += f"  • Images Processed: {len([c for c in chunks if 'source_file' in c])}\n"
                final_summary += f"  • Chunks Created: {len(chunks)}\n"
                final_summary += f"  • Visual Elements: {total_elements}\n"
                final_summary += f"  • Intermediate Files: {self.intermediate_dir}\n\n"

                if self.sheet_correlations:
                    final_summary += "Sheet Correlation Highlights:\n"
                    for sheet_id, summary in list(self.sheet_correlations.items())[:5]:
                        types = ", ".join(t for t, _ in summary.get("top_diagram_types", [])) or "unknown"
                        refs = ", ".join(summary.get("top_references", [])) or "none"
                        pages = ",".join(str(p + 1) for p in summary.get("page_span", []))
                        final_summary += f"  • {sheet_id}: pages {pages or '-'} | types {types} | refs {refs}\n"
                    final_summary += "\n"

                if self.quality_summary:
                    final_summary += "Quality Insights:\n"
                    clarity = ", ".join(f"{label} x{count}" for label, count in self.quality_summary.get("clarity", [])[:2])
                    completeness = ", ".join(f"{label} x{count}" for label, count in self.quality_summary.get("completeness", [])[:2])
                    compliance = ", ".join(f"{label} x{count}" for label, count in self.quality_summary.get("standard_compliance", [])[:2])
                    if clarity:
                        final_summary += f"  • Clarity: {clarity}\n"
                    if completeness:
                        final_summary += f"  • Completeness: {completeness}\n"
                    if compliance:
                        final_summary += f"  • Standards: {compliance}\n"
                    for insight in self.quality_summary.get("insights", [])[:3]:
                        final_summary += f"  • Insight: {insight}\n"
                    final_summary += "\n"
                
                final_summary += "Files Generated:\n"
                final_summary += "  📷 image_XXX_original.jpg - Original image files\n"
                final_summary += "  📄 00_complete_image_extraction.txt - All extracted text\n"
                final_summary += "  📊 01_image_processing_summary.txt - Processing statistics\n"
                final_summary += "  🧠 image_XXX_structure_analysis.json - o3-pro analysis\n"
                final_summary += "  👁️  visual_elements_XXX_analysis.json - Visual elements\n"
                final_summary += "  📋 chunk_XXX_content.txt - Individual chunk content\n\n"
                
                final_summary += "Analysis Capabilities:\n"
                final_summary += "  ✅ Direct image analysis (bypasses PDF protection)\n"
                final_summary += "  ✅ o3-pro enhanced visual reasoning\n"
                final_summary += "  ✅ Advanced symbol and component detection\n"
                final_summary += "  ✅ OCR text extraction (if MarkItDown available)\n"
                final_summary += "  ✅ Full engineering diagram interpretation\n\n"
                
                final_summary += "Next Steps:\n"
                final_summary += "  1. Review image processing quality in extraction files\n"
                final_summary += "  2. Check o3-pro structure analysis for accuracy\n"
                final_summary += "  3. Verify visual elements detection\n"
                final_summary += "  4. Use interactive mode for Q&A testing\n"
                
                save_intermediate_file(
                    final_summary,
                    "99_image_analysis_complete_summary.txt",
                    self.intermediate_dir,
                    "Final image analysis summary"
                )
                
                print(f"📋 All intermediate files saved to: {self.intermediate_dir}")
        
        finally:
            # Commit all staged documents to Azure Search (happens even if errors occurred)
            self._log("\n💾 Committing embeddings to Azure Search...\n")
            commit_result = self.context_manager.commit_to_search()
            if commit_result > 0:
                self._log(f"   ✓ Committed {commit_result} documents to search index\n")
            else:
                self._log(f"   ⚠️  No documents committed (may have failed earlier)\n")
            
            # Stop logging
            self._stop_logging()
        
        return {
            "status": "success",
            "images_processed": len([c for c in chunks if 'source_file' in c]),
            "chunks_processed": len(chunks),
            "visual_elements": total_elements,
            "analysis_type": "o3-pro enhanced image analysis",
            "model_used": self.deployment_name,
            "intermediate_dir": str(self.intermediate_dir) if self.intermediate_dir else None
        }
    
    async def analyze_document(self, pdf_path: str, domain: str = "general", auto_plan: bool = True) -> Dict[str, Any]:
        """Execute enhanced document analysis with o3-pro capabilities"""
        print(f"🚀 Starting o3-pro enhanced analysis of {pdf_path}")
        
        # Create intermediate files directory
        self.intermediate_dir = create_intermediate_dir(pdf_path)
        print(f"📁 Created intermediate files directory: {self.intermediate_dir}")
        
        # PHASE 0: PLANNING (if auto_plan enabled)
        if auto_plan:
            # Extract first few pages as images for planning
            try:
                pdf_doc = fitz.open(pdf_path)
                image_data_list = []
                
                for page_num in range(min(3, len(pdf_doc))):
                    page = pdf_doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    img_bytes = pix.tobytes("png")
                    image_data_list.append((img_bytes, f"page_{page_num + 1}.png"))
                
                pdf_doc.close()
                
                if image_data_list:
                    # Run planning phase
                    user_hint = domain if domain != "general" else None
                    self.analysis_plan = await self.planner.create_analysis_plan(image_data_list, user_hint)
                    
                    # Use plan recommendations
                    domain = self.analysis_plan.agent_config["domain"]
                    self.reasoning_effort = self.analysis_plan.agent_config["reasoning_effort"]
                    max_concurrent = self.analysis_plan.agent_config["max_concurrent_pages"]
                else:
                    max_concurrent = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))
                    
            except Exception as e:
                print(f"⚠️  Could not run planning phase: {e}")
                print("   Using manual domain settings")
                max_concurrent = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))
        else:
            max_concurrent = int(os.getenv("MAX_CONCURRENT_PAGES", "5"))
        
        # Display final domain configuration
        domain_display = domain.upper().replace(",", " + ")
        print(f"📋 Domain: {domain_display}")
        print(f"🧠 Reasoning Effort: {self.reasoning_effort.upper()}")
        
        # Initialize preprocessor with optimized settings
        self.preprocessor = DocumentPreprocessorPro(
            self.client,
            self.deployment_name,
            self.reasoning_effort,
            max_concurrent_pages=max_concurrent,
            enable_smart_chunking=os.getenv("ENABLE_SMART_CHUNKING", "true").lower() == "true",
            intermediate_dir=self.intermediate_dir,
            domain=domain
        )
        
        # Stage 1: Enhanced Preprocessing & Chunking
        print("\n📄 Stage 1: Enhanced document preprocessing with o3-pro reasoning...")
        chunks = await self.preprocessor.process_pdf(pdf_path)
        self.processed_chunks = chunks
        print(f"   ✓ Created {len(chunks)} intelligent chunks")
        self._summarize_sheet_correlations(chunks)

        diagnostics = getattr(self.preprocessor, "latest_diagnostics", None)
        if self.analysis_plan:
            self.analysis_plan, plan_updates = self.planner.refine_plan_with_diagnostics(self.analysis_plan, diagnostics)
            if plan_updates:
                print("   🔁 Plan refined based on preprocessing diagnostics:")
                for update in plan_updates:
                    print(f"      • {update}")
            self.reasoning_effort = self.analysis_plan.agent_config.get("reasoning_effort", self.reasoning_effort)
            self.visual_extractor.reasoning_effort = self.reasoning_effort
            new_max = self.analysis_plan.agent_config.get("max_concurrent_pages")
            if new_max and new_max != self.preprocessor.max_concurrent_pages:
                self.preprocessor.max_concurrent_pages = new_max
                self.preprocessor._processing_semaphore = asyncio.Semaphore(new_max)
                print(f"   ⚙️  Updated concurrency limit to {new_max} based on plan feedback")
        
        # Stage 2: Enhanced Visual Element Extraction
        print("👁️  Stage 2: Enhanced visual element extraction with o3-pro...")
        visual_tasks = [
            self.visual_extractor.extract_elements(chunk)
            for chunk in chunks
        ]
        visual_results = await asyncio.gather(*visual_tasks)
        
        for chunk, elements in zip(chunks, visual_results):
            self.visual_elements_by_chunk[chunk['chunk_id']] = elements
        
        total_elements = sum(
            len(result.get('elements', []))
            for result in visual_results
            if isinstance(result, dict)
        )
        print(f"   ✓ Extracted {total_elements} visual elements with enhanced reasoning")
        self._aggregate_quality_metrics(visual_results)
        self._print_quality_summary()
        
        # Stage 3: Build Context Index with Enhanced Embeddings
        print("💾 Stage 3: Building enhanced context index...")
        for chunk in chunks:
            try:
                chunk_content = chunk.get('content', '')
                if not chunk_content:
                    chunk_content = f"Empty chunk {chunk.get('chunk_id', 'unknown')}"
                
                embedding = await self._generate_embedding_pro(chunk_content)
                
                self.context_manager.add_chunk(
                    chunk['chunk_id'],
                    chunk_content,
                    chunk['metadata'],
                    embedding
                )
            except Exception as e:
                print(f"⚠️  Failed to process chunk {chunk.get('chunk_id', 'unknown')}: {e}")
                continue
        
        print("   ✓ Enhanced context index built with o3-pro capabilities")
        
        # Save final analysis summary
        if self.intermediate_dir:
            final_summary = f"EDISON PRO Analysis Complete\n{'=' * 50}\n\n"
            final_summary += f"PDF File: {pdf_path}\n"
            final_summary += f"Analysis Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            final_summary += f"Model Used: {self.deployment_name}\n"
            final_summary += f"Domain: {domain}\n\n"
            
            final_summary += f"Processing Results:\n"
            final_summary += f"  • Chunks Processed: {len(chunks)}\n"
            final_summary += f"  • Visual Elements: {total_elements}\n"
            final_summary += f"  • Intermediate Files: {self.intermediate_dir}\n\n"

            if self.sheet_correlations:
                final_summary += "Sheet Correlation Highlights:\n"
                for sheet_id, summary in list(self.sheet_correlations.items())[:5]:
                    types = ", ".join(t for t, _ in summary.get("top_diagram_types", [])) or "unknown"
                    refs = ", ".join(summary.get("top_references", [])) or "none"
                    pages = ",".join(str(p + 1) for p in summary.get("page_span", []))
                    final_summary += f"  • {sheet_id}: pages {pages or '-'} | types {types} | refs {refs}\n"
                final_summary += "\n"

            if self.quality_summary:
                final_summary += "Quality Insights:\n"
                clarity = ", ".join(f"{label} x{count}" for label, count in self.quality_summary.get("clarity", [])[:2])
                completeness = ", ".join(f"{label} x{count}" for label, count in self.quality_summary.get("completeness", [])[:2])
                compliance = ", ".join(f"{label} x{count}" for label, count in self.quality_summary.get("standard_compliance", [])[:2])
                if clarity:
                    final_summary += f"  • Clarity: {clarity}\n"
                if completeness:
                    final_summary += f"  • Completeness: {completeness}\n"
                if compliance:
                    final_summary += f"  • Standards: {compliance}\n"
                for insight in self.quality_summary.get("insights", [])[:3]:
                    final_summary += f"  • Insight: {insight}\n"
                final_summary += "\n"
            
            final_summary += "Files Generated:\n"
            final_summary += "  📄 00_complete_pymupdf_extraction.txt - All extracted text\n"
            final_summary += "  📊 01_extraction_summary.txt - Extraction statistics\n"
            final_summary += "  🧠 02_chunking_summary.txt - Chunking results\n"
            final_summary += "  🖼️  page_XXX_image.png - Page images\n"
            final_summary += "  📝 page_XXX_extracted_text.txt - Individual page text\n"
            final_summary += "  🔍 page_XXX_structure_analysis.json - Structure analysis\n"
            final_summary += "  👁️  visual_elements_XXX_analysis.json - Visual elements\n"
            final_summary += "  📋 chunk_XXX_content.txt - Individual chunk content\n\n"
            
            final_summary += "Next Steps:\n"
            final_summary += "  1. Review PyMuPDF extraction quality in extraction files\n"
            final_summary += "  2. Check structure analysis for accuracy\n"
            final_summary += "  3. Verify visual elements detection\n"
            final_summary += "  4. Use interactive mode for Q&A testing\n"
            
            save_intermediate_file(
                final_summary,
                "99_analysis_complete_summary.txt",
                self.intermediate_dir,
                "Final analysis summary"
            )
            
            print(f"📋 All intermediate files saved to: {self.intermediate_dir}")
        
        print("\n✅ o3-pro Enhanced Analysis Complete!")
        
        # Commit all staged documents to Azure Search after successful analysis
        self.context_manager.commit_to_search()

        diagnostics = getattr(self.preprocessor, "latest_diagnostics", {}) or {}
        routing_plan = diagnostics.get("routing_plan", {})
        
        return {
            "status": "success",
            "chunks_processed": len(chunks),
            "visual_elements": total_elements,
            "analysis_type": "o3-pro enhanced",
            "model_used": self.deployment_name,
            "intermediate_dir": str(self.intermediate_dir) if self.intermediate_dir else None,
            "pdf_classification": diagnostics.get("pdf_classification", "unknown"),
            "pdf_routing_primary": routing_plan.get("recommended_primary", "pymupdf"),
            "pdf_routing_fallback": routing_plan.get("recommended_fallback", "none"),
            "pdf_routing_reasons": routing_plan.get("reasons", [])[:5],
            "pdf_routing_plan": routing_plan,
            "extraction_quality": diagnostics.get("extraction_quality", "unknown"),
            "is_scanned": diagnostics.get("is_scanned", False),
            "is_protected": diagnostics.get("is_protected", False)
        }
    
    async def _generate_embedding_pro(self, text: str) -> List[float]:
        """Enhanced embedding generation for o3-pro"""
        try:
            embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
            
            clean_text = text.strip()
            if not clean_text:
                clean_text = "empty text"
            
            if len(clean_text) > 8000:
                clean_text = clean_text[:8000]
            
            print(f"🔍 Generating enhanced embedding with model: {embedding_deployment}")
            print(f"   Text length: {len(clean_text)} characters")
            print(f"   Text preview: {clean_text[:50]}...")
            
            # Use the standard embeddings endpoint (not Responses API)
            # Embeddings use AsyncAzureOpenAI with api_version
            from openai import AsyncAzureOpenAI
            
            api_version = os.getenv("AZURE_OPENAI_PRO_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
            azure_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT")
            
            embedding_client = AsyncAzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=api_version,
                azure_endpoint=azure_endpoint
            )
            
            response = await embedding_client.embeddings.create(
                model=embedding_deployment,
                input=clean_text
            )
            
            print(f"   ✅ Enhanced embedding generated (dimension: {len(response.data[0].embedding)})")
            return response.data[0].embedding
            
        except Exception as e:
            print(f"⚠️  Enhanced embedding generation failed: {e}")
            print(f"   Model: {embedding_deployment}")
            print(f"   Text preview: {clean_text[:50] if 'clean_text' in locals() else 'N/A'}...")
            print("   Using fallback embedding (random vector)")
            import random
            return [random.random() for _ in range(1536)]
    
    async def ask_question_pro(self, question: str) -> Dict[str, Any]:
        """Enhanced question answering with o3-pro reasoning"""
        has_remote_index = self.context_manager.search_client is not None
        has_local_chunks = bool(self.processed_chunks or self.context_manager.chunk_store)
        if not has_local_chunks and not has_remote_index:
            return {
                "error": "No analyzed content is available. Please run analyze_document or analyze_images_from_folder first."
            }
        
        print(f"\n❓ Processing question with o3-pro reasoning: {question}")
        
        # Retrieve enhanced context
        relevant_chunks = self.context_manager.retrieve_relevant_context(
            question, max_chunks=15  # Increased for o3-pro
        )

        if not relevant_chunks:
            source_hint = "Azure AI Search index" if has_remote_index else "local analysis cache"
            message = (
                "No relevant content found in the "
                f"{source_hint}. Ensure analysis results are committed and the index contains documents."
            )
            return {
                "answer": message,
                "reasoning_chain": ["Context retrieval returned zero results"],
                "confidence": 0.0,
                "raw_output": "",
                "error": message
            }
        
        # Enhanced context preparation
        context_text = "\n\n".join([
            f"Chunk {c['metadata'].chunk_id} (Pages {c['metadata'].page_numbers}):\n{c['content'][:1500]}"
            for c in relevant_chunks
        ])

        # ── Few-shot block: inject up to 3 most recent Q&A exchanges ──
        few_shot_block = ""
        if self.qa_history:
            few_shot_block = "\nEXAMPLES FROM PRIOR EXCHANGES IN THIS SESSION:\n"
            for past_q, past_a in self.qa_history[-3:]:
                few_shot_block += f"Q: {past_q}\nA (summary): {past_a[:400]}\n---\n"
            few_shot_block += "\nNOW ANSWER THE NEW QUESTION BELOW with the same analytical rigour.\n"
        
        prompt = f"""You are an expert engineering consultant with advanced reasoning capabilities, enhanced for o3-pro analysis.
{few_shot_block}
QUESTION: {question}

ENHANCED EXPERT RESPONSE FRAMEWORK with o3-pro REASONING:

1. DEEP QUESTION ANALYSIS:
   - What specific technical knowledge is being requested?
   - What level of detail and precision is needed?
   - Are there multiple valid interpretations or approaches?

2. COMPREHENSIVE KNOWLEDGE SYNTHESIS:
   - Which diagram sections contain relevant information?
   - What engineering principles and standards apply?
   - How do different components and systems interact?

3. ADVANCED REASONING CHAIN:
   - Step through the logical analysis systematically
   - Consider multiple scenarios and edge cases
   - Validate conclusions against engineering best practices
   - Quantify uncertainties and confidence levels

4. EXPERT-LEVEL RESPONSE:
   - Provide comprehensive answer with supporting evidence
   - Include relevant specifications, standards, and codes
   - Explain the reasoning process and assumptions
   - Offer practical implications and recommendations

5. QUALITY ASSURANCE:
   - Cross-check against all available diagram information
   - Identify any conflicting or ambiguous details
   - Suggest additional information that would improve accuracy

RELEVANT CONTEXT FROM ANALYZED DIAGRAMS:
{context_text[:12000]}
{ENGINEERING_CONSTRAINTS}
OUTPUT: Enhanced JSON response with o3-pro reasoning:
{{
    "answer": "comprehensive expert answer",
    "reasoning_chain": [
        "Step 1: Initial analysis and approach",
        "Step 2: Technical evaluation and calculations", 
        "Step 3: Standards and code review",
        "Step 4: Integration and system-level considerations",
        "Step 5: Validation and confidence assessment"
    ],
    "evidence": [
        {{
            "chunk_id": "chunk_id",
            "page": 0,
            "quote": "relevant excerpt",
            "location": "specific location description",
            "technical_significance": "why this evidence matters"
        }}
    ],
    "technical_analysis": {{
        "specifications": {{}},
        "standards_referenced": [],
        "engineering_calculations": "if applicable",
        "safety_considerations": "if relevant"
    }},
    "confidence": 0.95,
    "uncertainty_factors": ["factor1", "factor2"],
    "recommendations": ["recommendation1", "recommendation2"],
    "follow_up_questions": ["question1", "question2"],
    "sources": ["chunk_1", "chunk_3"]
}}"""

        # Use Responses API with maximum reasoning effort
        input_data = [
            {
                "role": "user", 
                "content": [
                    {"type": "input_text", "text": prompt}
                ]
            }
        ]

        response = await safe_responses_api_call(
            self.client,
            model=self.deployment_name,
            input=input_data,
            reasoning={"effort": "high"},
            max_output_tokens=16000
        )
        
        # Extract and parse response (handle o3-pro response structure)
        output_text = ""
        reasoning_text = ""
        
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                # Check for reasoning output
                if hasattr(output_item, 'type') and output_item.type == 'reasoning':
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                reasoning_text += content_item.text
                
                # Check for message output (o3-pro returns type='message')
                elif hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and output_item.content:
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                output_text += content_item.text
                
                # Fallback for other response formats
                elif hasattr(output_item, 'content') and output_item.content:
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            output_text += content_item.text
                elif hasattr(output_item, 'text'):
                    output_text += output_item.text
        
        # Log reasoning process if available
        if reasoning_text:
            print(f"\n🧠 o3-pro Reasoning Process:")
            print(f"   Length: {len(reasoning_text)} characters")
            if hasattr(response, 'usage') and response.usage:
                if hasattr(response.usage, 'output_tokens_details') and response.usage.output_tokens_details:
                    print(f"   Reasoning Tokens: {response.usage.output_tokens_details.reasoning_tokens}")
        
        print(f"\n📝 Raw output length: {len(output_text)} chars")
        if output_text:
            print(f"   First 200 chars: {output_text[:200]}")
        
        try:
            # Try to extract JSON from markdown code blocks if present
            if "```json" in output_text:
                json_text = output_text.split("```json")[1].split("```", 1)[0].strip()
            elif "```" in output_text:
                json_text = output_text.split("```", 1)[1].split("```", 1)[0].strip()
            else:
                json_text = output_text.strip()

            result = json.loads(json_text)
            # Persist this exchange for future few-shot context (cap at 10 pairs)
            answer_summary = result.get("answer", output_text)
            self.qa_history.append((question, answer_summary))
            if len(self.qa_history) > 10:
                self.qa_history.pop(0)
            print(f"✓ Successfully parsed JSON response: {result}")
            return result
        except Exception as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print(f"   Output text: {output_text[:500]}")
            print(f"   Returning fallback result dict with raw_output.")
            # Still store raw output for few-shot continuity
            self.qa_history.append((question, output_text[:400]))
            if len(self.qa_history) > 10:
                self.qa_history.pop(0)
            return {
                "answer": output_text if output_text else "No response generated from o3-pro",
                "reasoning_chain": ["Analysis completed with o3-pro reasoning"],
                "confidence": 0.8,
                "raw_output": output_text,
                "error": f"Response format parsing failed: {str(e)}"
            }

    async def ask_with_self_critique(self, question: str, domain: str = "general") -> Dict[str, Any]:
        """
        Two-pass self-critique loop.
        Pass 1: generate initial answer via ask_question_pro.
        Pass 2: the model critiques its own output against engineering QA checklist.
        Returns the revised answer when issues are found, otherwise the original.
        """
        initial = await self.ask_question_pro(question)

        # Only run critique when we have a substantive answer
        initial_answer = initial.get("answer", "")
        if not initial_answer or initial.get("error"):
            return initial

        critique_prompt = f"""You are a senior QA engineer reviewing an AI-generated engineering analysis.

ORIGINAL QUESTION:
{question}

ANALYSIS TO REVIEW:
{initial_answer[:3000]}

REVIEW CHECKLIST — identify any of the following issues:
1. Factual errors or claims not supported by diagram evidence
2. Missing or incorrect code/standard references (NEC, ASME, OSHA, NFPA, IBC)
3. Safety considerations overlooked
4. Overconfident claims where evidence is thin (< 3 chunks)
5. Ambiguous component designators interpreted without hedging
6. IEC/NEMA naming convention confusion

{ENGINEERING_CONSTRAINTS}

OUTPUT JSON:
{{
    "issues_found": ["issue1", "issue2"],
    "is_acceptable": true,
    "revised_answer": "corrected answer (copy original if no changes needed)"
}}"""

        try:
            critique = await self.ask_question_pro(critique_prompt)
            if not critique.get("is_acceptable", True) and critique.get("revised_answer"):
                print("🔍 Self-critique: issues found — using revised answer")
                return {**initial,
                        "answer": critique["revised_answer"],
                        "self_critique_issues": critique.get("issues_found", [])}
            else:
                print("✅ Self-critique: answer accepted as-is")
        except Exception as e:
            print(f"⚠️  Self-critique pass failed (returning original): {e}")

        return initial

    def print_interpretations_summary_pro(self):
        """Enhanced interpretations summary for o3-pro"""
        print("\n🧠 o3-pro ENHANCED ANALYSIS SUMMARY")
        print("=" * 60)
        
        total_chunks = len(self.processed_chunks)
        total_elements = sum(
            len(data.get('elements', []))
            for data in self.visual_elements_by_chunk.values()
            if isinstance(data, dict)
        )
        
        print(f"📊 Document Analysis Overview:")
        print(f"   • Chunks Processed: {total_chunks}")
        print(f"   • Visual Elements: {total_elements}")
        print(f"   • Analysis Model: {self.deployment_name}")
        print(f"   • Reasoning Level: Enhanced o3-pro")
        
        for chunk in self.processed_chunks[:5]:  # Show first 5 chunks
            chunk_id = chunk['chunk_id']
            pages = chunk['metadata'].page_numbers
            diagram_type = chunk['metadata'].diagram_type
            chunk_visuals = self.visual_elements_by_chunk.get(chunk_id, {})
            elements = len(chunk_visuals.get('elements', [])) if isinstance(chunk_visuals, dict) else 0
            
            print(f"\n📄 {chunk_id} (Pages {pages}):")
            print(f"   🎯 Type: {diagram_type or 'Unknown'}")
            print(f"   🔍 Elements: {elements}")
            if chunk.get('structure', {}).get('confidence_score'):
                confidence = chunk['structure']['confidence_score']
                print(f"   📈 Confidence: {confidence:.1%}")
        
        if total_chunks > 5:
            print(f"\n   ... and {total_chunks - 5} more chunks")
        
        print(f"\n💡 Tip: Use ask_question_pro() for enhanced o3-pro reasoning on your diagrams")


# ============================================================================
# CLI INTERFACE - Enhanced for o3-pro
# ============================================================================

def parse_domain_input(domain_str: str) -> str:
    """Parse and normalize domain input, supporting hybrid domains and presets."""
    # Preset mappings for common interdisciplinary combinations
    presets = {
        "utility": "civil,electrical",
        "mep": "mechanical,electrical,pid",
        "structural-civil": "structural,civil",
        "process": "mechanical,pid",
        "building": "structural,mechanical,electrical"
    }
    
    # Check if it's a preset
    domain_lower = domain_str.lower().strip()
    if domain_lower in presets:
        return presets[domain_lower]
    
    # Validate individual domains
    valid_domains = {"electrical", "mechanical", "pid", "civil", "structural", "general"}
    domains = [d.strip().lower() for d in domain_str.split(",")]
    
    invalid = [d for d in domains if d not in valid_domains]
    if invalid:
        raise ValueError(f"Invalid domain(s): {', '.join(invalid)}. Valid: {', '.join(valid_domains)}")
    
    return ",".join(domains)

async def cli_main_pro():
    """Enhanced CLI for o3-pro with image folder support"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="EDISON PRO - Advanced Engineering Diagram Analysis with o3-pro"
    )
    
    # Make input mutually exclusive
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--pdf", help="Path to the PDF file to analyze")
    input_group.add_argument("--images", help="Path to folder containing images (image1.jpg, image2.png, etc.)")
    input_group.add_argument("--blob-container", help="Azure Blob Storage container name to read from")
    
    # Blob storage options
    parser.add_argument("--blob-prefix", type=str, default="", 
                       help="Blob prefix/folder path (e.g., 'drawings/2024/')")
    parser.add_argument("--blob-extensions", type=str, default=".pdf,.png,.jpg,.jpeg,.tiff,.bmp",
                       help="Comma-separated file extensions to process from blob (default: .pdf,.png,.jpg,.jpeg,.tiff,.bmp)")
    parser.add_argument("--output-blob-container", type=str,
                       help="Azure Blob Storage container to write results to (optional)")
    parser.add_argument("--output-blob-prefix", type=str, default="",
                       help="Blob prefix for output files (default: analysis-{timestamp}/)")
    parser.add_argument("--keep-temp-files", action="store_true",
                       help="Keep temporary downloaded files from blob storage")
    
    parser.add_argument("--domain", type=str,
                       default="general", 
                       help="Engineering domain(s): electrical, mechanical, pid, civil, structural, general. "
                            "Supports multiple domains (comma-separated): 'civil,electrical'. "
                            "Presets: 'utility' (civil+electrical), 'mep' (mechanical+electrical+pid), "
                            "'structural-civil', 'process' (mechanical+pid)")
    parser.add_argument("--auto-plan", action="store_true", default=True,
                       help="Enable automatic planning phase (default: enabled, use --no-auto-plan to disable)")
    parser.add_argument("--no-auto-plan", action="store_false", dest="auto_plan",
                       help="Disable automatic planning phase and use manual domain")
    parser.add_argument("--interactive", action="store_true", help="Enhanced interactive Q&A mode")
    parser.add_argument("--reasoning-effort", choices=["high"], 
                       default="high", help="gpt-5-pro reasoning effort level (only 'high' supported)")
    
    args = parser.parse_args()
    
    # Parse and normalize domain input
    try:
        args.domain = parse_domain_input(args.domain)
    except ValueError as e:
        print(f"❌ Domain error: {e}")
        return
    
    # Initialize blob storage manager if needed
    blob_manager = None
    temp_input_path = None
    output_blob_prefix = args.output_blob_prefix
    
    if args.blob_container:
        if not HAS_BLOB_STORAGE:
            print("❌ Error: Blob storage support not available")
            print("   Install with: pip install azure-storage-blob azure-identity")
            return
        
        print(f"\n📦 BLOB STORAGE INPUT MODE")
        print(f"   Container: {args.blob_container}")
        print(f"   Prefix: {args.blob_prefix or '(root)'}")
        
        # Create blob manager
        blob_manager = create_blob_manager_from_env(container_name=args.blob_container)
        if not blob_manager:
            print("❌ Error: Could not initialize blob storage")
            print("   Check AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL in .env")
            return
        
        # Parse file extensions
        extensions = [ext.strip() for ext in args.blob_extensions.split(',')]
        
        # Download blobs to temp directory
        try:
            local_files = blob_manager.download_blobs_to_temp(
                prefix=args.blob_prefix,
                file_extensions=extensions,
                max_workers=4
            )
            
            if not local_files:
                print(f"❌ No files found in blob container matching criteria")
                return
            
            # Determine if we have PDFs or images
            pdf_files = [f for f in local_files if f.lower().endswith('.pdf')]
            image_files = [f for f in local_files if not f.lower().endswith('.pdf')]
            
            if pdf_files:
                # Use first PDF found
                temp_input_path = pdf_files[0]
                args.pdf = temp_input_path
                if len(pdf_files) > 1:
                    print(f"⚠️  Multiple PDFs found, using first: {Path(temp_input_path).name}")
            elif image_files:
                # Use temp directory as image folder
                temp_input_path = blob_manager.temp_dir
                args.images = temp_input_path
            else:
                print(f"❌ No supported files found")
                return
                
        except Exception as e:
            print(f"❌ Failed to download from blob storage: {e}")
            if blob_manager:
                blob_manager.cleanup_temp_files()
            return
    
    # Set output blob prefix if not specified
    if args.output_blob_container and not output_blob_prefix:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_blob_prefix = f"analysis-{timestamp}/"
    
    # Check o3-pro configuration
    if not os.getenv("AZURE_OPENAI_PRO_ENDPOINT") or not (os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")):
        print("❌ Error: AZURE_OPENAI_PRO_ENDPOINT and AZURE_OPENAI_API_KEY must be set for EDISON Pro")
        print("Please configure your .env file with o3-pro credentials")
        if blob_manager:
            blob_manager.cleanup_temp_files()
        return
    
    # Initialize enhanced orchestrator
    try:
        orchestrator = DiagramAnalysisOrchestratorPro(reasoning_effort=args.reasoning_effort)
        print(f"🚀 EDISON PRO initialized with {orchestrator.deployment_name}")
        print(f"   Reasoning Effort: {orchestrator.reasoning_effort}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Analyze input with o3-pro
    try:
        if args.pdf:
            print(f"📄 Analyzing PDF: {args.pdf}")
            result = await orchestrator.analyze_document(args.pdf, args.domain, auto_plan=args.auto_plan)
        elif args.images:
            print(f"📁 Analyzing images from folder: {args.images}")
            result = await orchestrator.analyze_images_from_folder(args.images, args.domain, auto_plan=args.auto_plan)
        
        # Show enhanced summary
        orchestrator.print_interpretations_summary_pro()
        
        # Enhanced interactive mode
        if args.interactive:
            # Safety check: commit any pending documents before starting Q&A
            if orchestrator.context_manager.pending_documents:
                print(f"\n⚠️  Found {len(orchestrator.context_manager.pending_documents)} uncommitted documents")
                print("💾 Committing to Azure Search before starting Q&A...")
                commit_count = orchestrator.context_manager.commit_to_search()
                if commit_count > 0:
                    print(f"   ✓ Successfully committed {commit_count} documents\n")
                else:
                    print("   ⚠️  Commit may have failed. Search results might be incomplete.\n")
            
            print("\n" + "="*70)
            print("🧠 EDISON PRO INTERACTIVE Q&A MODE")
            print("Enhanced with o3-pro Advanced Reasoning")
            print("="*70)
            print("Enter your questions (type 'exit' to quit)")
            print("Special commands: 'commit' to upload staged documents\n")
            
            while True:
                try:
                    question = input("Q: ").strip()
                    if question.lower() in ['exit', 'quit', 'q']:
                        break
                    
                    if not question:
                        continue
                    
                    # Handle special commands
                    if question.lower() == 'commit':
                        if orchestrator.context_manager.pending_documents:
                            print(f"💾 Committing {len(orchestrator.context_manager.pending_documents)} staged documents to Azure Search...")
                            commit_count = orchestrator.context_manager.commit_to_search()
                            if commit_count > 0:
                                print(f"   ✓ Successfully committed {commit_count} documents to search index\n")
                            else:
                                print(f"   ⚠️  Commit failed or no documents were uploaded\n")
                        else:
                            print("   ℹ️  No staged documents to commit. All documents are already in Azure Search.\n")
                        continue
                    
                    if question.lower() == 'status':
                        staged = len(orchestrator.context_manager.pending_documents)
                        total = len(orchestrator.context_manager.chunk_store)
                        print(f"📊 Status:")
                        print(f"   • Total chunks: {total}")
                        print(f"   • Staged (not uploaded): {staged}")
                        print(f"   • In Azure Search: {total - staged}\n")
                        continue
                    
                    answer = await orchestrator.ask_question_pro(question)

                    if answer.get('error') and not answer.get('answer'):
                        print(f"❌ {answer['error']}\n")
                        continue

                    print(f"\n🧠 Answer:\n{answer.get('answer', 'No answer generated')}\n")
                    
                    
                    if answer.get('confidence'):
                        print(f"📊 Confidence: {answer['confidence']:.1%}")
                    
                    if answer.get('reasoning_chain'):
                        print("\n🔍 Reasoning Chain:")
                        for i, step in enumerate(answer['reasoning_chain'][:3], 1):
                            print(f"   {i}. {step}")
                    
                    if answer.get('evidence'):
                        print("\n📋 Evidence:")
                        for i, ev in enumerate(answer['evidence'][:2], 1):
                            print(f"   {i}. Page {ev.get('page', 'N/A')}: {ev.get('quote', 'N/A')[:80]}...")
                    
                    print()
                    
                except KeyboardInterrupt:
                    print("\n\nExiting EDISON Pro...")
                    break
                except Exception as e:
                    print(f"❌ Error: {str(e)}\n")
        
        print(f"\n✨ EDISON Pro analysis complete using {orchestrator.deployment_name}")
        
        # Upload results to blob storage if configured
        if args.output_blob_container and orchestrator.preprocessor.intermediate_dir:
            print(f"\n📤 UPLOADING RESULTS TO BLOB STORAGE")
            print(f"   Container: {args.output_blob_container}")
            print(f"   Prefix: {output_blob_prefix}")
            
            try:
                # Create output blob manager if different from input
                output_blob_manager = blob_manager
                if args.output_blob_container != args.blob_container:
                    output_blob_manager = create_blob_manager_from_env(container_name=args.output_blob_container)
                    if not output_blob_manager:
                        print("   ⚠️  Could not initialize output blob storage")
                    else:
                        output_blob_manager.set_container(args.output_blob_container)
                
                if output_blob_manager:
                    # Upload intermediate files folder
                    intermediate_path = str(orchestrator.preprocessor.intermediate_dir)
                    blob_urls = output_blob_manager.upload_folder_to_blob(
                        intermediate_path,
                        output_blob_prefix,
                        max_workers=4
                    )
                    
                    print(f"   ✅ Uploaded {len(blob_urls)} files to blob storage")
                    
                    # Generate SAS URL for the analysis folder (if using connection string)
                    if not output_blob_manager.use_managed_identity and blob_urls:
                        # Get the first file to generate a sample URL
                        sample_blob = f"{output_blob_prefix}00_analysis_log.txt"
                        try:
                            sas_url = output_blob_manager.generate_sas_url(sample_blob, expiry_hours=168)  # 7 days
                            base_url = sas_url.split('?')[0].rsplit('/', 1)[0]
                            print(f"   🔗 Results available at: {base_url}/")
                        except Exception as e:
                            print(f"   ⚠️  Could not generate SAS URL: {e}")
                    
                    # Cleanup output blob manager if different
                    if output_blob_manager != blob_manager:
                        output_blob_manager.cleanup_temp_files()
                        
            except Exception as e:
                print(f"   ❌ Failed to upload results: {e}")
        
        # Cleanup temporary blob files
        if blob_manager:
            if args.keep_temp_files:
                print(f"\n📁 Temporary files kept at: {blob_manager.temp_dir}")
            else:
                blob_manager.cleanup_temp_files()
        
    except Exception as e:
        print(f"❌ Error during o3-pro analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Cleanup blob manager on error
        if blob_manager and not args.keep_temp_files:
            blob_manager.cleanup_temp_files()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    asyncio.run(cli_main_pro())