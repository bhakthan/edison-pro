"""
FastAPI REST API wrapper for EDISON PRO frontend.
Exposes REST endpoints that communicate with the existing Gradio backend.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

# Import your existing handlers
from code_agent_handler import get_code_agent
from upload_handler import process_uploaded_file, list_indexed_documents

# Define folders
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = FastAPI(
    title="EDISON PRO API",
    description="REST API for EDISON PRO transformer data analysis",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str
    history: List[List[str]] = []  # List of [question, answer] pairs


class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[dict]] = None
    tables: Optional[List[dict]] = None
    files: Optional[List[str]] = None
    charts: Optional[List[str]] = None
    code_executed: Optional[bool] = None
    analysis_status: Optional[str] = None


class UploadResponse(BaseModel):
    status: str
    message: str
    filename: Optional[str] = None


class SystemStatus(BaseModel):
    status: str
    indexing_status: str
    document_count: int


@app.get("/")
async def root():
    """API health check endpoint."""
    return {
        "service": "EDISON PRO API",
        "status": "operational",
        "version": "1.0.0"
    }


@app.post("/ask", response_model=ChatResponse)
async def ask_question(request: QuestionRequest):
    """
    Ask a question about transformer data.
    
    Uses Code Agent (Phase 3) for advanced queries with chart generation.
    """
    try:
        print(f"\n[API] Received question: {request.question}")
        print(f"[API] History length: {len(request.history)}")
        
        # Get the code agent instance
        code_agent = get_code_agent()
        
        # Check if code agent is available
        if not code_agent.available:
            # Return a mock response if code agent is not configured
            return ChatResponse(
                answer=f"Code agent not configured. Your question was: {request.question}\n\nTo enable full functionality, configure Azure AI Agent credentials in .env file.",
                sources=[],
                tables=[],
                files=[],
                charts=[],
                code_executed=None,
                analysis_status="Code Agent Not Configured"
            )
        
        # Prepare context data (mock data for now - in production, get from search index)
        context_data: Dict[str, Any] = {
            "interpretations": [],
            "visual_elements": [],
            "metadata": {"source": "user_query"}
        }
        
        # Convert history to format expected by backend
        # Frontend sends: [["q1", "a1"], ["q2", "a2"]]
        history_tuples = [tuple(pair) for pair in request.history]
        
        # Call Code Agent handler
        result = code_agent.process_data_query(
            question=request.question,
            context_data=context_data,
            conversation_history=history_tuples,
            enable_web_search=False
        )
        
        print(f"[API] Result keys: {result.keys()}")
        print(f"[API] Files returned: {result.get('files', [])}")
        
        # Convert result to response format
        response = ChatResponse(
            answer=result.get("answer", "No answer available"),
            sources=result.get("sources", []),
            tables=result.get("tables", []),
            files=result.get("files", []),
            charts=result.get("charts", []),
            code_executed=result.get("code_executed"),
            analysis_status=result.get("analysis_status", "Success" if not result.get("error") else "Error")
        )
        
        return response
        
    except Exception as e:
        print(f"[API ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process transformer data files.
    
    Supports CSV, Excel, and text files.
    """
    try:
        print(f"\n[API] Uploading file: {file.filename}")
        
        # Save uploaded file
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"[API] Saved to: {file_path}")
        
        # Process the file (index it)
        process_result = process_uploaded_file(file_path)
        
        return UploadResponse(
            status="success",
            message=f"File '{file.filename}' uploaded and indexed successfully",
            filename=file.filename
        )
        
    except Exception as e:
        print(f"[API ERROR] Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.get("/status", response_model=SystemStatus)
async def get_status():
    """
    Get system health and status information.
    """
    try:
        # Get document count
        documents = list_indexed_documents()
        doc_count = len(documents) if documents else 0
        
        return SystemStatus(
            status="operational",
            indexing_status="idle",
            document_count=doc_count
        )
        
    except Exception as e:
        print(f"[API ERROR] Status check failed: {str(e)}")
        return SystemStatus(
            status="error",
            indexing_status="unknown",
            document_count=0
        )


@app.get("/documents")
async def list_documents():
    """
    List all indexed documents.
    """
    try:
        documents = list_indexed_documents()
        return {"documents": documents or []}
        
    except Exception as e:
        print(f"[API ERROR] Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


@app.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """
    Download a generated file (chart, report, etc.).
    
    Files are typically in the 'out/' folder.
    """
    try:
        # Construct full path
        full_path = Path(OUTPUT_FOLDER) / file_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        return FileResponse(
            path=str(full_path),
            filename=full_path.name,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 EDISON PRO API Server")
    print("="*60)
    print(f"📍 API: http://localhost:7861")
    print(f"📖 Docs: http://localhost:7861/docs")
    print(f"🔗 Frontend: http://localhost:5173")
    print("="*60 + "\n")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=7861,
        log_level="info"
    )
