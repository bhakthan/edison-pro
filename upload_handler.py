"""
Upload handler for EDISON PRO.
Handles file uploads and indexing into Azure AI Search.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


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
    List all indexed documents in the system.
    
    Returns:
        List of document metadata dictionaries
    """
    try:
        # TODO: Query Azure AI Search for indexed documents
        # This should return actual documents from the search index
        
        # For now, return files from upload folder
        from config import UPLOAD_FOLDER
        
        if not os.path.exists(UPLOAD_FOLDER):
            return []
        
        documents = []
        for file in Path(UPLOAD_FOLDER).iterdir():
            if file.is_file():
                documents.append({
                    "filename": file.name,
                    "upload_date": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                    "file_size": file.stat().st_size,
                    "indexed": False  # Update when implementing actual indexing
                })
        
        print(f"[UPLOAD] Found {len(documents)} documents")
        return documents
        
    except Exception as e:
        print(f"[UPLOAD ERROR] Failed to list documents: {str(e)}")
        return []


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
