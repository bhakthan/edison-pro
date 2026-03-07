"""
FastAPI REST API for EDISON PRO
Provides HTTP endpoints for the TypeScript frontend
"""
import os
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from pathlib import Path

# Import your existing handlers
# Note: Adjust these imports based on your actual module structure
try:
    from analysis_templates import get_template_library, TemplateLibrary, AnalysisTemplate as Template, TemplateCategory
except ImportError:
    # Fallback
    get_template_library = lambda: None
    TemplateLibrary = None
    Template = None
    TemplateCategory = None

try:
    from edisonpro import DiagramAnalysisOrchestratorPro as Orchestrator
except ImportError:
    try:
        from edisonpro import EdisonProOrchestrator as Orchestrator
    except ImportError:
        try:
            from edisonpro import EdisonPro as Orchestrator
        except ImportError:
            # Fallback - create a dummy class
            class Orchestrator:
                def __init__(self):
                    self.context_manager = type('obj', (object,), {
                        'search_client': None, 
                        'chunk_store': {},
                        'retrieve_relevant_context': lambda *args, **kwargs: []
                    })()
                
                async def ask_question_pro(self, question):
                    return {"answer": "Orchestrator not properly configured"}
                
                def process_document(self, file_path):
                    return {"chunks": 0}

try:
    from code_agent_handler import get_code_agent
except ImportError:
    # Fallback
    def get_code_agent():
        return type('obj', (object,), {'available': False})()

try:
    from results_generator import generate_results_page
except ImportError:
    generate_results_page = None

try:
    from agents import FlickeringSystem
except ImportError:
    FlickeringSystem = None

try:
    from agents.dynamic_meta_agent import get_dynamic_registry
    DYNAMIC_META_AGENT_AVAILABLE = True
except ImportError:
    get_dynamic_registry = None
    DYNAMIC_META_AGENT_AVAILABLE = False

# Innovative Feature Agents (Phase 1 & Phase 2)
try:
    from agents import (
        AnomalyPredictorAgent, 
        RevisionAnalyzerAgent, 
        QuerySuggestionAgent,
        ExpertNetworkAgent,
        CounterfactualSimulator,
        create_anomaly_predictor,
        create_revision_analyzer,
        create_query_suggestion_agent,
        create_expert_network,
        create_counterfactual_simulator
    )
    INNOVATIVE_FEATURES_AVAILABLE = True
except ImportError:
    AnomalyPredictorAgent = None
    RevisionAnalyzerAgent = None
    QuerySuggestionAgent = None
    ExpertNetworkAgent = None
    CounterfactualSimulator = None
    INNOVATIVE_FEATURES_AVAILABLE = False

# Phase 3 Enhancement Modules (Feedback & Visualization)
try:
    from agents.feedback_tracker import (
        FeedbackTracker,
        FeedbackEvent,
        FeatureUsageStats,
        create_feedback_tracker
    )
    from agents.results_visualizer import (
        ResultsVisualizer,
        ReportGenerator,
        create_visualizer,
        create_report_generator
    )
    PHASE3_ENHANCEMENTS_AVAILABLE = True
except ImportError:
    FeedbackTracker = None
    FeedbackEvent = None
    FeatureUsageStats = None
    ResultsVisualizer = None
    ReportGenerator = None
    PHASE3_ENHANCEMENTS_AVAILABLE = False


# Initialize FastAPI app
app = FastAPI(
    title="EDISON PRO API",
    description="Engineering Diagram Analysis with o3-pro and Code Agent",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Rolling Conversation Summarizer
# Maintains a compressed session summary so every ask_question_pro call
# has access to the full prior conversation context without blowing token budgets.
# ============================================================================
class ConversationSummarizer:
    """
    Maintains a compressed rolling summary of the Q&A session.
    When the raw exchange log grows beyond max_raw_pairs, it summarises the
    oldest entries into a compact paragraph and retains only the most recent
    exchanges verbatim.
    """
    MAX_RAW_PAIRS = 6   # keep last N exchanges verbatim
    SUMMARY_TRIGGER = 8  # summarise when we exceed this many pairs

    def __init__(self):
        self.summary: str = ""
        self.recent_exchanges: list = []  # List of (question, answer) tuples

    def add_exchange(self, question: str, answer: str):
        self.recent_exchanges.append((question, answer))
        if len(self.recent_exchanges) > self.SUMMARY_TRIGGER:
            # Compress the oldest entries; keep the most recent verbatim
            to_compress = self.recent_exchanges[:-self.MAX_RAW_PAIRS]
            self.recent_exchanges = self.recent_exchanges[-self.MAX_RAW_PAIRS:]
            compressed = self._compress(to_compress)
            self.summary = (self.summary + "\n" + compressed).strip() if self.summary else compressed

    def _compress(self, exchanges: list) -> str:
        """Build a concise bullet summary of the given exchanges."""
        lines = ["Prior session findings (compressed):"]
        for q, a in exchanges:
            answer_snippet = a[:300].replace("\n", " ") if a else ""
            lines.append(f"• Q: {q[:120]} → {answer_snippet}")
        return "\n".join(lines)

    def get_context_block(self) -> str:
        """Return the context string to prepend to new prompts."""
        if not self.summary and not self.recent_exchanges:
            return ""
        parts = []
        if self.summary:
            parts.append(self.summary)
        if self.recent_exchanges:
            parts.append("Most recent Q&A exchanges:")
            for q, a in self.recent_exchanges[-3:]:
                parts.append(f"Q: {q}\nA: {a[:400]}\n---")
        return "\nSESSION CONTEXT:\n" + "\n".join(parts) + "\n"

    def reset(self):
        self.summary = ""
        self.recent_exchanges = []


# Initialize orchestrator (singleton)
orchestrator = None
code_agent = None
flickering_system = None  # Flickering cognitive architecture
conversation_history = []  # Track Q&A for results page
generated_files = []  # Track generated files
conversation_summarizer = ConversationSummarizer()  # Rolling session summary

def get_orchestrator():
    """Get or create orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        orchestrator = Orchestrator()
    return orchestrator

def get_agent():
    """Get or create code agent instance"""
    global code_agent
    if code_agent is None:
        code_agent = get_code_agent()
    return code_agent

def get_flickering():
    """Get or create flickering system instance"""
    global flickering_system
    if flickering_system is None and FlickeringSystem:
        flickering_system = FlickeringSystem(
            storage_path="./memory_atlas",
            theta_frequency=8.0,
            mismatch_threshold=0.3,
            enable_background_simulation=False
        )
    return flickering_system


def get_dynamic_registry_instance():
    if not DYNAMIC_META_AGENT_AVAILABLE or get_dynamic_registry is None:
        return None
    return get_dynamic_registry()

# ============================================================================
# Request/Response Models
# ============================================================================

class QuestionRequest(BaseModel):
    question: str
    use_code_agent: Optional[bool] = None
    use_web_search: Optional[bool] = False
    history: Optional[List[List[str]]] = []

class QuestionResponse(BaseModel):
    answer: str
    tables: Optional[List[Dict[str, Any]]] = None
    files: Optional[List[str]] = None
    charts: Optional[List[Dict[str, Any]]] = None
    code_executed: Optional[bool] = False
    web_search_used: Optional[bool] = False
    web_sources: Optional[List[Dict[str, str]]] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    orchestrator_ready: bool
    code_agent_ready: bool
    azure_search_ready: bool
    documents_count: int

class TemplateExecutionRequest(BaseModel):
    template_id: str
    use_web_search: Optional[bool] = False
    skip_questions: Optional[List[int]] = []

class TemplateSearchRequest(BaseModel):
    keywords: List[str]

class FlickeringAnalysisRequest(BaseModel):
    """Request model for flickering analysis"""
    diagram: str  # Base64 encoded image or file path
    num_cycles: Optional[int] = 100
    theta_frequency: Optional[float] = 8.0
    domain: Optional[str] = None
    return_trace: Optional[bool] = True
    generate_alternatives: Optional[bool] = True

class FlickeringAnalysisResponse(BaseModel):
    """Response model for flickering analysis"""
    interpretation: Dict[str, Any]
    mismatch_events: List[Dict[str, Any]]
    alternatives: List[Dict[str, Any]]
    attention_trace: Optional[List[Dict[str, Any]]] = None
    system_info: Dict[str, Any]
    learning_events: List[Dict[str, Any]]
    num_cycles: int
    num_mismatches: int
    theta_frequency: float
    latency_ms: int
    confidence: Optional[Dict[str, Any]] = None  # Probabilistic confidence metrics

class TemplateQuestionResult(BaseModel):
    question_index: int
    question: str
    answer: str
    tables: Optional[List[Dict[str, Any]]] = None
    files: Optional[List[str]] = None
    charts: Optional[List[Dict[str, Any]]] = None
    code_executed: Optional[bool] = False
    execution_time_seconds: Optional[float] = None

class TemplateExecutionResponse(BaseModel):
    template: Dict[str, Any]
    results: List[TemplateQuestionResult]
    total_execution_time_seconds: float
    summary: str


class DynamicAgentEnsureRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = None
    allow_create: bool = True


class DynamicAgentRunRequest(BaseModel):
    agent_id: str
    prompt: str
    session_id: Optional[str] = None
    task: Optional[str] = None
    auto_refine: bool = True
    min_score: float = 0.72
    max_refinement_rounds: int = 1

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "service": "EDISON PRO API"}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status"""
    orch = get_orchestrator()
    agent = get_agent()
    
    return StatusResponse(
        status="ready",
        orchestrator_ready=orch is not None,
        code_agent_ready=agent.available if agent else False,
        azure_search_ready=orch.context_manager.search_client is not None if orch else False,
        documents_count=len(orch.context_manager.chunk_store) if orch else 0
    )

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and analyze an engineering document"""
    try:
        # Save uploaded file temporarily
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process document with orchestrator
        orch = get_orchestrator()
        
        # Run analysis asynchronously
        result = await asyncio.to_thread(
            orch.process_document,
            str(file_path)
        )
        
        return {
            "success": True,
            "filename": file.filename,
            "message": "Document processed successfully",
            "chunks": result.get("chunks", 0) if result else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about analyzed documents"""
    global conversation_history, generated_files
    try:
        print(f"[API] Received request - use_web_search: {request.use_web_search}, type: {type(request.use_web_search)}")
        
        orch = get_orchestrator()
        agent = get_agent()
        
        # Determine which agent to use
        use_code_agent = request.use_code_agent
        if use_code_agent is None:
            # Auto-detect based on keywords
            try:
                from edisonpro_ui import DATA_TRANSFORMATION_KEYWORDS
                keywords = DATA_TRANSFORMATION_KEYWORDS
            except ImportError:
                # Fallback keywords
                keywords = ['chart', 'graph', 'plot', 'table', 'export', 'csv', 
                           'excel', 'visualize', 'bar chart', 'pie chart', 'line graph']
            
            use_code_agent = any(
                keyword in request.question.lower() 
                for keyword in keywords
            )
        
        if use_code_agent and agent.available:
            # Use Code Agent
            # Prepare context
            context_data = {
                'interpretations': [],
                'visual_elements': [],
                'metadata': {}
            }
            
            # Try to get from local cache first
            if hasattr(orch, 'interpretations_by_chunk'):
                for chunk_id, interpretations in orch.interpretations_by_chunk.items():
                    for interp in interpretations:
                        context_data['interpretations'].append({
                            'chunk_id': chunk_id,
                            'component_id': interp.get('component_id'),
                            'type': interp.get('component_type'),
                            'specifications': interp.get('specifications', {}),
                        })
            
            # If no local cache, retrieve from Azure Search
            if not context_data['interpretations'] and orch.context_manager.search_client:
                chunks = await asyncio.to_thread(
                    orch.context_manager.retrieve_relevant_context,
                    "transformers circuit breakers motors components",
                    50
                )
                for chunk in chunks:
                    metadata = chunk.get('metadata')
                    if metadata and hasattr(metadata, 'components'):
                        for component in metadata.components:
                            context_data['interpretations'].append({
                                'chunk_id': metadata.chunk_id,
                                'component_id': component,
                                'content': chunk.get('content', '')[:500]
                            })
            
            # Call code agent with web search if enabled
            print(f"[API] Calling code agent with enable_web_search: {request.use_web_search}")
            result = await asyncio.to_thread(
                agent.process_data_query,
                request.question,
                context_data,
                [],
                bool(request.use_web_search) if request.use_web_search is not None else False
            )
            
            # Track conversation and files
            answer = result.get('answer', '')
            conversation_history.append((request.question, answer))
            if result.get('files'):
                generated_files.extend(result.get('files', []))
            
            return QuestionResponse(
                answer=answer,
                tables=result.get('tables', []),
                files=result.get('files', []),
                charts=result.get('charts', []),
                code_executed=result.get('code_executed', False),
                web_search_used=request.use_web_search
            )
        else:
            # Use o3-pro — inject rolling session context then call
            global conversation_summarizer
            session_ctx = conversation_summarizer.get_context_block()
            enriched_question = f"{session_ctx}{request.question}" if session_ctx else request.question
            result = await orch.ask_question_pro(enriched_question)
            answer = result.get('answer', '')
            
            # Track conversation in both history list and rolling summarizer
            conversation_history.append((request.question, answer))
            conversation_summarizer.add_exchange(request.question, answer)
            
            return QuestionResponse(
                answer=answer,
                confidence=result.get('confidence'),
                reasoning=result.get('reasoning')
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/files/{file_path:path}")
async def get_file(file_path: str):
    """Download a generated file"""
    try:
        full_path = Path(file_path)
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(full_path),
            filename=full_path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/charts/{filename}")
async def get_chart(filename: str):
    """Get a generated chart HTML file"""
    try:
        chart_path = Path("out") / filename
        if not chart_path.exists():
            raise HTTPException(status_code=404, detail="Chart not found")
        
        return FileResponse(
            path=str(chart_path),
            media_type="text/html"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-results")
async def generate_results():
    """Generate comprehensive HTML results page from conversation history"""
    global conversation_history, generated_files
    try:
        if not generate_results_page:
            raise HTTPException(status_code=501, detail="Results generator not available")
        
        if not conversation_history and not generated_files:
            raise HTTPException(status_code=400, detail="No analysis data available to generate results")
        
        # Collect all files from out directory
        out_dir = Path("out")
        all_files = []
        if out_dir.exists():
            all_files = [str(f) for f in out_dir.iterdir() if f.is_file() and not f.name.startswith('analysis_results')]
        
        # Merge with tracked generated files
        all_files = list(set(all_files + generated_files))
        
        # Generate the results page
        results_path = await asyncio.to_thread(
            generate_results_page,
            conversation_history,
            all_files,
            {
                'total_questions': len(conversation_history),
                'total_files': len(all_files),
                'csv_files': len([f for f in all_files if f.endswith('.csv')]),
                'charts': len([f for f in all_files if f.endswith('.html')]),
            }
        )
        
        return JSONResponse({
            "status": "success",
            "results_path": results_path,
            "message": f"Results page generated with {len(conversation_history)} Q&A pairs and {len(all_files)} files"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/results/latest")
async def get_latest_results():
    """Get the latest generated results page"""
    try:
        out_dir = Path("out")
        if not out_dir.exists():
            raise HTTPException(status_code=404, detail="No results available")
        
        # Find most recent analysis_results file
        results_files = list(out_dir.glob("analysis_results_*.html"))
        if not results_files:
            raise HTTPException(status_code=404, detail="No results page found")
        
        latest_file = max(results_files, key=lambda f: f.stat().st_mtime)
        
        return FileResponse(
            path=str(latest_file),
            media_type="text/html",
            filename=latest_file.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Template Endpoints
# ============================================================================

@app.get("/templates")
async def get_templates(category: Optional[str] = None):
    """Get all available analysis templates"""
    try:
        library = get_template_library()
        if not library:
            return []
        
        if category:
            try:
                cat_enum = TemplateCategory(category)
                templates = library.list_templates(cat_enum)
            except ValueError:
                templates = library.list_templates()
        else:
            templates = library.list_templates()
        
        # Convert to dict for JSON serialization
        result = []
        for t in templates:
            template_dict = {
                'template_id': t.template_id,
                'name': t.name,
                'description': t.description,
                'category': t.category.value if hasattr(t.category, 'value') else str(t.category),
                'use_case': t.use_case,
                'recommended_domain': t.recommended_domain,
                'recommended_reasoning': t.recommended_reasoning,
                'questions': [
                    {
                        'question': q.question,
                        'purpose': q.purpose,
                        'expected_format': q.expected_format,
                        'requires_code_agent': q.requires_code_agent,
                        'priority': q.priority
                    } for q in t.questions
                ],
                'expected_outputs': t.output_formats,
                'quality_checks': t.quality_checks,
                'estimated_time_minutes': t.estimated_time_minutes,
                'requires_web_search': False,  # Default to False since attribute doesn't exist
                'tags': t.tags
            }
            result.append(template_dict)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific analysis template"""
    try:
        library = get_template_library()
        if not library:
            raise HTTPException(status_code=404, detail="Template library not available")
        
        template = library.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        return {
            'template_id': template.template_id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value if hasattr(template.category, 'value') else str(template.category),
            'use_case': template.use_case,
            'recommended_domain': template.recommended_domain,
            'recommended_reasoning': template.recommended_reasoning,
            'questions': [
                {
                    'question': q.question,
                    'purpose': q.purpose,
                    'expected_format': q.expected_format,
                    'requires_code_agent': q.requires_code_agent,
                    'priority': q.priority
                } for q in template.questions
            ],
            'expected_outputs': template.output_formats,
            'quality_checks': template.quality_checks,
            'estimated_time_minutes': template.estimated_time_minutes,
            'requires_web_search': False,  # Default to False since attribute doesn't exist
            'tags': template.tags
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/templates/search")
async def search_templates(request: TemplateSearchRequest):
    """Search templates by keywords"""
    try:
        library = get_template_library()
        if not library:
            return []
        
        templates = library.search_templates(request.keywords)
        
        return [
            {
                'template_id': t.template_id,
                'name': t.name,
                'description': t.description,
                'category': t.category.value if hasattr(t.category, 'value') else str(t.category),
                'use_case': t.use_case,
                'recommended_domain': t.recommended_domain,
                'recommended_reasoning': t.recommended_reasoning,
                'questions': [
                    {
                        'question': q.question,
                        'purpose': q.purpose,
                        'expected_format': q.expected_format,
                        'requires_code_agent': q.requires_code_agent,
                        'priority': q.priority
                    } for q in t.questions
                ],
                'expected_outputs': t.output_formats,
                'quality_checks': t.quality_checks,
                'estimated_time_minutes': t.estimated_time_minutes,
                'requires_web_search': False,  # Default to False since attribute doesn't exist
                'tags': t.tags
            } for t in templates
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/templates/execute", response_model=TemplateExecutionResponse)
async def execute_template(request: TemplateExecutionRequest):
    """Execute an analysis template"""
    try:
        import time
        start_time = time.time()
        
        library = get_template_library()
        if not library:
            raise HTTPException(status_code=404, detail="Template library not available")
        
        template = library.get_template(request.template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        orch = get_orchestrator()
        agent = get_agent()
        results = []
        
        # Execute each question in the template
        for i, question_obj in enumerate(template.questions):
            if i in request.skip_questions:
                continue
                
            question_start = time.time()
            
            # Determine if this question needs code agent
            use_code_agent = question_obj.requires_code_agent
            use_web_search = request.use_web_search  # Use the request parameter instead
            
            try:
                if use_code_agent and agent.available:
                    # Prepare context data
                    context_data = {
                        'interpretations': [],
                        'visual_elements': [],
                        'metadata': {}
                    }
                    
                    # Get context from Azure Search if available
                    if orch.context_manager.search_client:
                        chunks = await asyncio.to_thread(
                            orch.context_manager.retrieve_relevant_context,
                            question_obj.question,
                            10
                        )
                        for chunk in chunks:
                            metadata = chunk.get('metadata')
                            if metadata and hasattr(metadata, 'components'):
                                for component in metadata.components:
                                    context_data['interpretations'].append({
                                        'chunk_id': metadata.chunk_id,
                                        'component_id': component,
                                        'content': chunk.get('content', '')[:500]
                                    })
                    
                    # Execute with code agent
                    result = await asyncio.to_thread(
                        agent.process_data_query,
                        question_obj.question,
                        context_data,
                        [],
                        use_web_search
                    )
                    
                    results.append(TemplateQuestionResult(
                        question_index=i,
                        question=question_obj.question,
                        answer=result.get('answer', ''),
                        tables=result.get('tables', []),
                        files=result.get('files', []),
                        charts=result.get('charts', []),
                        code_executed=result.get('code_executed', False),
                        execution_time_seconds=time.time() - question_start
                    ))
                else:
                    # Use o3-pro
                    result = await orch.ask_question_pro(question_obj.question)
                    
                    results.append(TemplateQuestionResult(
                        question_index=i,
                        question=question_obj.question,
                        answer=result.get('answer', ''),
                        execution_time_seconds=time.time() - question_start
                    ))
                    
            except Exception as e:
                print(f"Error executing question {i}: {e}")
                results.append(TemplateQuestionResult(
                    question_index=i,
                    question=question_obj.question,
                    answer=f"Error: {str(e)}",
                    execution_time_seconds=time.time() - question_start
                ))
        
        total_time = time.time() - start_time
        
        # Generate summary
        successful_questions = len([r for r in results if not r.answer.startswith("Error:")])
        summary = f"Executed {successful_questions}/{len(results)} questions successfully in {total_time:.1f} seconds."
        
        return TemplateExecutionResponse(
            template={
                'template_id': template.template_id,
                'name': template.name,
                'description': template.description,
                'category': template.category.value if hasattr(template.category, 'value') else str(template.category),
                'use_case': template.use_case,
                'recommended_domain': template.recommended_domain,
                'recommended_reasoning': template.recommended_reasoning,
                'questions': [
                    {
                        'question': q.question,
                        'purpose': q.purpose,
                        'expected_format': q.expected_format,
                        'requires_code_agent': q.requires_code_agent,
                        'priority': q.priority
                    } for q in template.questions
                ],
                'expected_outputs': template.output_formats,
                'quality_checks': template.quality_checks,
                'estimated_time_minutes': template.estimated_time_minutes,
                'requires_web_search': False,  # Default to False since attribute doesn't exist
                'tags': template.tags
            },
            results=results,
            total_execution_time_seconds=total_time,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/flickering", response_model=FlickeringAnalysisResponse)
async def analyze_flickering(request: FlickeringAnalysisRequest):
    """
    Perform flickering cognitive analysis on diagram
    
    Uses 6-agent architecture inspired by hippocampal navigation:
    - Reality Anchor: Extract current features
    - Memory Atlas: Retrieve historical patterns
    - Theta Oscillator: Rhythmic flickering between reality and memory
    - Anticipatory Simulation: Pre-computed strategies
    - Map Integration: Compositional learning from novelty
    - Pathway Generator: Alternative interpretation hypotheses
    """
    try:
        flickering = get_flickering()
        
        if not flickering:
            raise HTTPException(
                status_code=501, 
                detail="Flickering system not available. Please install required dependencies."
            )
        
        # Perform flickering analysis
        results = await asyncio.to_thread(
            flickering.analyze,
            diagram=request.diagram,
            num_cycles=request.num_cycles,
            domain=request.domain,
            theta_frequency=request.theta_frequency,
            return_trace=request.return_trace,
            generate_alternatives=request.generate_alternatives
        )
        
        return FlickeringAnalysisResponse(**results)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flickering/status")
async def get_flickering_status():
    """Get flickering system status"""
    try:
        flickering = get_flickering()
        
        if not flickering:
            return JSONResponse({
                "available": False,
                "message": "Flickering system not initialized"
            })
        
        status = await asyncio.to_thread(flickering.get_system_status)
        return JSONResponse({
            "available": True,
            **status
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dynamic-agents/status")
async def get_dynamic_agents_status():
    registry = get_dynamic_registry_instance()
    if not registry:
        return JSONResponse({
            "available": False,
            "provider_available": False,
            "metrics": {},
        })

    snapshot = registry.status_snapshot()
    return JSONResponse({
        "available": True,
        "provider_available": snapshot.get("provider_available", False),
        "metrics": snapshot,
    })


@app.get("/dynamic-agents")
async def list_dynamic_agents():
    registry = get_dynamic_registry_instance()
    if not registry:
        raise HTTPException(status_code=501, detail="Dynamic meta-agent registry not available")
    return registry.list_agents()


@app.post("/dynamic-agents/ensure")
async def ensure_dynamic_agent(request: DynamicAgentEnsureRequest):
    registry = get_dynamic_registry_instance()
    if not registry:
        raise HTTPException(status_code=501, detail="Dynamic meta-agent registry not available")
    return await registry.ensure_agent_for_task(
        task=request.task,
        context=request.context or {},
        allow_create=request.allow_create,
    )


@app.post("/dynamic-agents/run")
async def run_dynamic_agent(request: DynamicAgentRunRequest):
    registry = get_dynamic_registry_instance()
    if not registry:
        raise HTTPException(status_code=501, detail="Dynamic meta-agent registry not available")
    return await registry.run_agent(
        agent_id=request.agent_id,
        prompt=request.prompt,
        session_id=request.session_id,
        task=request.task,
        auto_refine=request.auto_refine,
        min_score=request.min_score,
        max_refinement_rounds=request.max_refinement_rounds,
    )


@app.post("/dynamic-agents/reload")
async def reload_dynamic_agents():
    registry = get_dynamic_registry_instance()
    if not registry:
        raise HTTPException(status_code=501, detail="Dynamic meta-agent registry not available")
    return {
        "status": "reloaded",
        "metrics": registry.reload_from_persistence(),
    }


@app.get("/dynamic-agents/last-run")
async def get_dynamic_agents_last_run(agent_id: Optional[str] = None):
    registry = get_dynamic_registry_instance()
    if not registry:
        raise HTTPException(status_code=501, detail="Dynamic meta-agent registry not available")
    return registry.get_last_run_diagnostics(agent_id)


@app.get("/dynamic-agents/{agent_id}/lineage")
async def get_dynamic_agent_lineage(agent_id: str):
    registry = get_dynamic_registry_instance()
    if not registry:
        raise HTTPException(status_code=501, detail="Dynamic meta-agent registry not available")
    return registry.get_agent_lineage(agent_id)

# ============================================================================
# Innovative Feature Endpoints
# ============================================================================

class AnomalyPredictionRequest(BaseModel):
    diagram_path: str
    domain: str
    context: Optional[Dict[str, Any]] = None

class AnomalyPredictionResponse(BaseModel):
    has_anomalies: bool
    anomalies: List[Dict[str, Any]]
    risk_score: float
    confidence: float
    recommendations: List[str]
    similar_failures: List[Dict[str, Any]]
    prevention_cost: Optional[float] = None
    failure_cost: Optional[float] = None

@app.post("/predict-anomalies", response_model=AnomalyPredictionResponse)
async def predict_anomalies(request: AnomalyPredictionRequest):
    """
    Predict potential failures in diagram using historical patterns
    
    Returns risk assessment with recommendations and cost estimates
    """
    if not INNOVATIVE_FEATURES_AVAILABLE:
        raise HTTPException(status_code=501, detail="Innovative features not available")
    
    try:
        orch = get_orchestrator()
        flickering = get_flickering()
        
        if not flickering:
            raise HTTPException(status_code=500, detail="Flickering system required")
        
        # Create anomaly predictor
        predictor = create_anomaly_predictor(
            memory_atlas=flickering.memory_atlas,
            reality_anchor=flickering.reality_anchor,
            similarity_threshold=0.75
        )
        
        # Run prediction
        result = await asyncio.to_thread(
            predictor.predict_anomalies,
            diagram=request.diagram_path,
            domain=request.domain,
            context=request.context
        )
        
        return AnomalyPredictionResponse(
            has_anomalies=result.has_anomalies,
            anomalies=result.anomalies,
            risk_score=result.risk_score,
            confidence=result.confidence,
            recommendations=result.recommendations,
            similar_failures=result.similar_failures,
            prevention_cost=result.prevention_cost_estimate,
            failure_cost=result.failure_cost_estimate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class RevisionComparisonRequest(BaseModel):
    revision_a_path: str
    revision_b_path: str
    revision_a_label: str = "Rev A"
    revision_b_label: str = "Rev B"
    domain: str

class RevisionComparisonResponse(BaseModel):
    revision_a: str
    revision_b: str
    total_changes: int
    changes: List[Dict[str, Any]]
    summary: str
    critical_changes: List[str]
    requires_review: bool
    change_categories: Dict[str, int]

@app.post("/compare-revisions", response_model=RevisionComparisonResponse)
async def compare_revisions(request: RevisionComparisonRequest):
    """
    Compare two diagram revisions and identify changes
    
    Returns detailed change analysis with engineering significance
    """
    if not INNOVATIVE_FEATURES_AVAILABLE:
        raise HTTPException(status_code=501, detail="Innovative features not available")
    
    try:
        orch = get_orchestrator()
        flickering = get_flickering()
        
        if not flickering:
            raise HTTPException(status_code=500, detail="Flickering system required")
        
        # Create revision analyzer
        analyzer = create_revision_analyzer(
            reality_anchor=flickering.reality_anchor,
            orchestrator=orch,
            sensitivity=0.05
        )
        
        # Run comparison
        result = await analyzer.analyze_revisions(
            revision_a=request.revision_a_path,
            revision_b=request.revision_b_path,
            revision_a_label=request.revision_a_label,
            revision_b_label=request.revision_b_label,
            domain=request.domain
        )
        
        return RevisionComparisonResponse(
            revision_a=result.revision_a,
            revision_b=result.revision_b,
            total_changes=result.total_changes,
            changes=[c.to_dict() for c in result.changes],
            summary=result.summary,
            critical_changes=result.critical_changes,
            requires_review=result.requires_review,
            change_categories=result.change_categories
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class QuestionSuggestionRequest(BaseModel):
    diagram_path: str
    domain: str
    context: Optional[Dict[str, Any]] = None
    questions_asked: Optional[List[str]] = []

class QuestionSuggestionResponse(BaseModel):
    suggested_questions: List[Dict[str, Any]]
    categories: Dict[str, int]
    critical_count: int
    reasoning: str

@app.post("/suggest-questions", response_model=QuestionSuggestionResponse)
async def suggest_questions(request: QuestionSuggestionRequest):
    """
    Generate suggested verification questions for diagram
    
    Returns prioritized questions with rationale
    """
    if not INNOVATIVE_FEATURES_AVAILABLE:
        raise HTTPException(status_code=501, detail="Innovative features not available")
    
    try:
        orch = get_orchestrator()
        flickering = get_flickering()
        
        if not flickering:
            raise HTTPException(status_code=500, detail="Flickering system required")
        
        # Create query suggester
        suggester = create_query_suggestion_agent(
            reality_anchor=flickering.reality_anchor,
            memory_atlas=flickering.memory_atlas,
            orchestrator=orch
        )
        
        # Get suggestions
        result = await suggester.suggest_questions(
            diagram=request.diagram_path,
            domain=request.domain,
            context=request.context,
            user_questions_asked=request.questions_asked
        )
        
        return QuestionSuggestionResponse(
            suggested_questions=[q.to_dict() for q in result.suggested_questions],
            categories=result.categories,
            critical_count=result.critical_count,
            reasoning=result.reasoning
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class QuestionFeedbackRequest(BaseModel):
    question_id: str
    was_helpful: bool
    found_issue: bool = False

@app.post("/question-feedback")
async def record_question_feedback(request: QuestionFeedbackRequest):
    """
    Record feedback on suggested question to improve future suggestions
    """
    if not INNOVATIVE_FEATURES_AVAILABLE:
        raise HTTPException(status_code=501, detail="Innovative features not available")
    
    try:
        # In production, would persist this to database/Memory Atlas
        return JSONResponse({
            "status": "success",
            "message": "Feedback recorded",
            "question_id": request.question_id
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 2 Innovative Feature Endpoints
# ============================================================================

class ExpertReviewRequest(BaseModel):
    diagram_path: str
    domain: str
    context: Optional[Dict[str, Any]] = None
    design_phase: str = "preliminary"
    expert_count: Optional[int] = 6

class ExpertReviewResponse(BaseModel):
    overall_recommendation: str
    consensus_level: float
    expert_opinions: List[Dict[str, Any]]
    critical_issues: List[str]
    debate_points: List[str]
    action_items: List[str]
    risk_assessment: Dict[str, Any]

@app.post("/expert-review", response_model=ExpertReviewResponse)
async def conduct_expert_review(request: ExpertReviewRequest):
    """
    Conduct multi-disciplinary expert panel review of design
    
    Simulates 6 domain experts analyzing the design:
    - Electrical Engineer
    - Safety Engineer
    - Mechanical Engineer
    - Compliance Officer
    - Cost Estimator
    - Constructability Expert
    
    Returns consensus recommendation with debate points
    """
    if not INNOVATIVE_FEATURES_AVAILABLE:
        raise HTTPException(status_code=501, detail="Innovative features not available")
    
    try:
        orch = get_orchestrator()
        flickering = get_flickering()
        
        if not flickering:
            raise HTTPException(status_code=500, detail="Flickering system required")
        
        # Create expert network
        expert_network = create_expert_network(
            orchestrator=orch,
            memory_atlas=flickering.memory_atlas
        )
        
        # Conduct expert review
        result = await expert_network.conduct_expert_review(
            diagram=request.diagram_path,
            domain=request.domain,
            context=request.context,
            design_phase=request.design_phase
        )
        
        return ExpertReviewResponse(
            overall_recommendation=result.overall_recommendation,
            consensus_level=result.consensus_level,
            expert_opinions=[op.to_dict() for op in result.expert_opinions],
            critical_issues=result.critical_issues,
            debate_points=result.debate_points,
            action_items=result.action_items,
            risk_assessment=result.risk_assessment
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class CounterfactualSimulationRequest(BaseModel):
    diagram_path: str
    domain: str
    context: Optional[Dict[str, Any]] = None
    parameters_to_vary: Optional[List[str]] = None
    optimization_goal: str = "balanced"  # 'cost', 'performance', 'safety', 'balanced'
    max_scenarios: Optional[int] = 10

class CounterfactualSimulationResponse(BaseModel):
    baseline_scenario: Dict[str, Any]
    alternative_scenarios: List[Dict[str, Any]]
    recommended_scenario: Optional[Dict[str, Any]]
    comparison_matrix: Dict[str, List[float]]
    optimization_insights: List[str]
    tradeoff_analysis: str

@app.post("/simulate-scenarios", response_model=CounterfactualSimulationResponse)
async def simulate_counterfactual_scenarios(request: CounterfactualSimulationRequest):
    """
    Simulate "what-if" scenarios for design optimization
    
    Explores alternative design parameters and predicts outcomes:
    - Generates multiple scenarios by varying key parameters
    - Predicts impact on cost, performance, safety, feasibility
    - Compares scenarios across dimensions
    - Recommends optimal design based on goal
    
    Returns comprehensive tradeoff analysis
    """
    if not INNOVATIVE_FEATURES_AVAILABLE:
        raise HTTPException(status_code=501, detail="Innovative features not available")
    
    try:
        orch = get_orchestrator()
        flickering = get_flickering()
        
        if not flickering:
            raise HTTPException(status_code=500, detail="Flickering system required")
        
        # Create counterfactual simulator
        simulator = create_counterfactual_simulator(
            orchestrator=orch,
            anticipatory_agent=flickering.anticipatory_agent if hasattr(flickering, 'anticipatory_agent') else None,
            memory_atlas=flickering.memory_atlas,
            max_scenarios=request.max_scenarios or 10
        )
        
        # Run simulation
        result = await simulator.simulate_scenarios(
            diagram=request.diagram_path,
            domain=request.domain,
            context=request.context,
            parameters_to_vary=request.parameters_to_vary,
            optimization_goal=request.optimization_goal
        )
        
        return CounterfactualSimulationResponse(
            baseline_scenario=result.baseline_scenario,
            alternative_scenarios=[s.to_dict() for s in result.alternative_scenarios],
            recommended_scenario=result.recommended_scenario.to_dict() if result.recommended_scenario else None,
            comparison_matrix=result.comparison_matrix,
            optimization_insights=result.optimization_insights,
            tradeoff_analysis=result.tradeoff_analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/innovative-features/status")
async def get_innovative_features_status():
    """Get status of innovative features"""
    return JSONResponse({
        "available": INNOVATIVE_FEATURES_AVAILABLE,
        "features": {
            "phase_1": {
                "anomaly_prediction": INNOVATIVE_FEATURES_AVAILABLE,
                "revision_analysis": INNOVATIVE_FEATURES_AVAILABLE,
                "query_suggestion": INNOVATIVE_FEATURES_AVAILABLE
            },
            "phase_2": {
                "expert_network": INNOVATIVE_FEATURES_AVAILABLE,
                "counterfactual_simulator": INNOVATIVE_FEATURES_AVAILABLE
            },
            "phase_3": {
                "feedback_tracking": PHASE3_ENHANCEMENTS_AVAILABLE,
                "visualization": PHASE3_ENHANCEMENTS_AVAILABLE,
                "report_generation": PHASE3_ENHANCEMENTS_AVAILABLE
            }
        },
        "message": "All innovative features available" if INNOVATIVE_FEATURES_AVAILABLE else "Agents not imported"
    })


# ============================================================================
# Phase 3 Enhancement Endpoints (Feedback & Visualization)
# ============================================================================

# Global instances
_feedback_tracker: Optional[FeedbackTracker] = None
_visualizer: Optional[ResultsVisualizer] = None
_report_generator: Optional[ReportGenerator] = None

def get_feedback_tracker() -> FeedbackTracker:
    """Get or create feedback tracker instance"""
    global _feedback_tracker
    if _feedback_tracker is None:
        if not PHASE3_ENHANCEMENTS_AVAILABLE:
            raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
        _feedback_tracker = create_feedback_tracker()
    return _feedback_tracker

def get_visualizer() -> ResultsVisualizer:
    """Get or create visualizer instance"""
    global _visualizer
    if _visualizer is None:
        if not PHASE3_ENHANCEMENTS_AVAILABLE:
            raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
        _visualizer = create_visualizer()
    return _visualizer

def get_report_generator() -> ReportGenerator:
    """Get or create report generator instance"""
    global _report_generator
    if _report_generator is None:
        if not PHASE3_ENHANCEMENTS_AVAILABLE:
            raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
        _report_generator = create_report_generator(get_visualizer())
    return _report_generator


class FeedbackRequest(BaseModel):
    """User feedback on feature results"""
    feature_type: str  # 'anomaly_prediction', 'query_suggestion', etc.
    diagram_id: str
    domain: str
    feedback_type: str  # 'helpful', 'not_helpful', 'found_issue', 'accepted', 'rejected'
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = "anonymous"

class FeedbackResponse(BaseModel):
    success: bool
    message: str
    event_id: str

@app.post("/feedback", response_model=FeedbackResponse)
async def record_user_feedback(request: FeedbackRequest):
    """
    Record user feedback on innovative feature results
    
    Phase 3 Enhancement: Learning system
    - Tracks helpful/not helpful feedback
    - Records issue discoveries
    - Accepts/rejects recommendations
    - Enables continuous learning
    """
    if not PHASE3_ENHANCEMENTS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
    
    try:
        tracker = get_feedback_tracker()
        
        # Create feedback event
        from datetime import datetime
        event = FeedbackEvent(
            event_id=f"{request.feature_type}_{datetime.now().timestamp()}",
            feature_type=request.feature_type,
            timestamp=datetime.now().isoformat(),
            diagram_id=request.diagram_id,
            domain=request.domain,
            feedback_type=request.feedback_type,
            context=request.context,
            user_id=request.user_id
        )
        
        # Record feedback
        tracker.record_feedback(event)
        
        return FeedbackResponse(
            success=True,
            message="Feedback recorded successfully",
            event_id=event.event_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AnalyticsRequest(BaseModel):
    """Request for analytics data"""
    feature_type: Optional[str] = None  # None = all features
    domain: Optional[str] = None

class AnalyticsResponse(BaseModel):
    feature_stats: Dict[str, Any]
    top_questions: Optional[List[Dict[str, Any]]] = None
    report: str

@app.get("/analytics", response_model=AnalyticsResponse)
async def get_feature_analytics(feature_type: Optional[str] = None, domain: Optional[str] = None):
    """
    Get analytics and effectiveness metrics
    
    Phase 3 Enhancement: Data-driven insights
    - Feature usage statistics
    - Effectiveness scores
    - Top-performing questions
    - Learning trends
    """
    if not PHASE3_ENHANCEMENTS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
    
    try:
        tracker = get_feedback_tracker()
        
        # Get feature statistics
        if feature_type:
            stats = tracker.get_feature_stats(feature_type)
            feature_stats = {feature_type: stats.to_dict() if stats else None}
        else:
            # Get all features
            feature_types = [
                'anomaly_prediction',
                'revision_analysis',
                'query_suggestion',
                'expert_review',
                'scenario_simulation'
            ]
            feature_stats = {}
            for ft in feature_types:
                stats = tracker.get_feature_stats(ft)
                feature_stats[ft] = stats.to_dict() if stats else None
        
        # Get top questions for domain
        top_questions = None
        if domain:
            questions = tracker.get_top_questions(domain=domain, limit=10)
            top_questions = [
                {
                    'question_id': q[0],
                    'text': q[1],
                    'effectiveness_score': q[2],
                    'times_suggested': q[3],
                    'times_asked': q[4]
                }
                for q in questions
            ]
        
        # Generate analytics report
        report = tracker.generate_analytics_report()
        
        return AnalyticsResponse(
            feature_stats=feature_stats,
            top_questions=top_questions,
            report=report
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class VisualizationRequest(BaseModel):
    """Request for visualization generation"""
    visualization_type: str  # 'risk_gauge', 'consensus_chart', 'scenario_comparison', 'trend'
    data: Dict[str, Any]

class VisualizationResponse(BaseModel):
    html: str
    chart_id: str

@app.post("/visualize", response_model=VisualizationResponse)
async def generate_visualization(request: VisualizationRequest):
    """
    Generate interactive visualization
    
    Phase 3 Enhancement: Rich visual feedback
    - Risk gauges
    - Consensus charts
    - Scenario comparisons
    - Trend analysis
    """
    if not PHASE3_ENHANCEMENTS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
    
    try:
        visualizer = get_visualizer()
        
        html = ""
        if request.visualization_type == "risk_gauge":
            html = visualizer.create_risk_gauge(
                risk_score=request.data.get('risk_score', 0.0),
                title=request.data.get('title', 'Risk Assessment')
            )
        elif request.visualization_type == "consensus_chart":
            html = visualizer.create_consensus_chart(
                expert_opinions=request.data.get('expert_opinions', []),
                consensus_level=request.data.get('consensus_level', 0.0)
            )
        elif request.visualization_type == "scenario_comparison":
            html = visualizer.create_scenario_comparison(
                scenarios=request.data.get('scenarios', []),
                comparison_matrix=request.data.get('comparison_matrix', {})
            )
        elif request.visualization_type == "trend":
            html = visualizer.create_trend_chart(
                data=request.data.get('data', []),
                metric_key=request.data.get('metric_key', 'value'),
                title=request.data.get('title', 'Trend Analysis')
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown visualization type: {request.visualization_type}")
        
        from datetime import datetime
        chart_id = f"{request.visualization_type}_{datetime.now().timestamp()}"
        
        return VisualizationResponse(
            html=html,
            chart_id=chart_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ReportRequest(BaseModel):
    """Request for report generation"""
    report_type: str  # 'anomaly', 'expert_review', 'scenario'
    result: Dict[str, Any]
    diagram_path: str
    domain: str

@app.post("/generate-report")
async def generate_html_report(request: ReportRequest):
    """
    Generate comprehensive HTML report
    
    Phase 3 Enhancement: Professional reports
    - Anomaly prediction reports with risk gauges
    - Expert review reports with consensus charts
    - Scenario simulation reports with comparisons
    - Downloadable HTML format
    """
    if not PHASE3_ENHANCEMENTS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Phase 3 enhancements not available")
    
    try:
        report_gen = get_report_generator()
        
        if request.report_type == "anomaly":
            html = report_gen.generate_anomaly_report(
                result=request.result,
                diagram_path=request.diagram_path,
                domain=request.domain
            )
        elif request.report_type == "expert_review":
            html = report_gen.generate_expert_review_report(
                result=request.result,
                diagram_path=request.diagram_path,
                domain=request.domain
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown report type: {request.report_type}")
        
        # Save report temporarily
        from datetime import datetime
        report_filename = f"{request.report_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = Path("reports") / report_filename
        report_gen.save_report(html, str(report_path))
        
        return FileResponse(
            path=str(report_path),
            media_type="text/html",
            filename=report_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Run server
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
