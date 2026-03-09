"""
Upload handler for EDISON PRO.
Handles file uploads and indexing into Azure AI Search.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

try:
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential
    HAS_AZURE_SEARCH = True
except ImportError:
    HAS_AZURE_SEARCH = False


def _get_search_client() -> Optional["SearchClient"]:
    """Return a SearchClient if Azure AI Search is configured, else None."""
    if not HAS_AZURE_SEARCH:
        return None
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    api_key = os.getenv("AZURE_SEARCH_API_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "edison-diagrams")
    if not endpoint or not api_key:
        return None
    try:
        return SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(api_key),
        )
    except Exception as e:
        print(f"[UPLOAD] Azure Search client init failed: {e}")
        return None


def process_uploaded_file(file_path: str) -> Dict:
    """
    Process an uploaded file and index it into Azure AI Search.
    
    Args:
        file_path: Path to the uploaded file
        
    Returns:
        Dictionary with processing status
    """
    try:
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        print(f"[UPLOAD] Processing file: {filename} ({file_size} bytes)")
        
        # TODO: Implement actual indexing logic
        # This should:
        # 1. Read the file (CSV, Excel, etc.)
        # 2. Parse the data
        # 3. Create chunks for Azure AI Search
        # 4. Upload to search index
        
        result = {
            "status": "success",
            "filename": filename,
            "file_size": file_size,
            "upload_time": datetime.now().isoformat(),
            "indexed": False  # Change to True after implementing indexing
        }
        
        print(f"[UPLOAD] File processed successfully")
        return result
        
    except Exception as e:
        print(f"[UPLOAD ERROR] Failed to process file: {str(e)}")
        raise


def list_indexed_documents() -> List[Dict]:
    """
    List all indexed documents by querying the Azure AI Search index.
    Falls back to scanning the local uploads/ folder when Search is unavailable.
    """
    results: Dict[str, Dict] = {}

    # ── 1. Query Azure AI Search for indexed source files ──────────────────
    search_client = _get_search_client()
    if search_client:
        try:
            # Use facets to collect distinct source_file values efficiently
            response = search_client.search(
                search_text="*",
                facets=["source_file,count:1000"],
                select=["source_file", "timestamp"],
                top=0,
            )
            facet_data = response.get_facets() or {}
            for facet in facet_data.get("source_file", []):
                filename = facet.get("value", "")
                if filename:
                    results[filename] = {
                        "filename": filename,
                        "upload_date": None,
                        "file_size": None,
                        "indexed": True,
                    }
            print(f"[UPLOAD] Azure Search returned {len(results)} indexed source file(s)")
        except Exception as e:
            print(f"[UPLOAD] Azure Search facet query failed: {e}")

    # ── 2. Merge with local uploads/ folder (catches files not yet committed) ──
    try:
        from config import UPLOAD_FOLDER
        upload_path = Path(UPLOAD_FOLDER)
        if upload_path.exists():
            for file in upload_path.iterdir():
                if file.is_file():
                    name = file.name
                    stat = file.stat()
                    if name not in results:
                        results[name] = {
                            "filename": name,
                            "upload_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "file_size": stat.st_size,
                            "indexed": False,
                        }
                    else:
                        # Enrich Search entry with local file metadata
                        results[name]["upload_date"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                        results[name]["file_size"] = stat.st_size
    except Exception as e:
        print(f"[UPLOAD] Local folder scan failed: {e}")

    print(f"[UPLOAD] Total documents available: {len(results)}")
    return list(results.values())


def delete_document(filename: str) -> bool:
    """
    Delete a document from the upload folder and search index.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from config import UPLOAD_FOLDER
        
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[UPLOAD] Deleted file: {filename}")
            
            # TODO: Also remove from Azure AI Search index
            
            return True
        else:
            print(f"[UPLOAD] File not found: {filename}")
            return False
            
    except Exception as e:
        print(f"[UPLOAD ERROR] Failed to delete file: {str(e)}")
        return False
