"""
Author: Srikanth Bhakthan - Microsoft
EDISON PRO - Gradio Web UI
Professional Q&A Interface for Engineering Diagram Analysis

Simple, clean interface for interacting with analyzed diagrams.
Assumes analysis has already been completed via edisonpro.py
"""

import os
import asyncio
from typing import List, Tuple
from pathlib import Path
import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import EDISON PRO orchestrator
from edisonpro import DiagramAnalysisOrchestratorPro

# Import blob storage
try:
    from blob_storage import BlobStorageManager, create_blob_manager_from_env
    HAS_BLOB_STORAGE = True
except ImportError:
    HAS_BLOB_STORAGE = False
    print("⚠️  Blob storage not available")

# Import code agent handler
try:
    from code_agent_handler import get_code_agent
    import pandas as pd
    HAS_CODE_AGENT = True
except ImportError:
    HAS_CODE_AGENT = False
    print("⚠️  Code Agent not available (install: pip install azure-ai-projects pandas)")

# Import analysis templates
try:
    from analysis_templates import get_template_library, AnalysisTemplate, TemplateCategory
    HAS_TEMPLATES = True
except ImportError:
    HAS_TEMPLATES = False
    print("⚠️  Analysis templates not available")

# Import flickering system
try:
    from agents import FlickeringSystem
    HAS_FLICKERING = True
except ImportError:
    HAS_FLICKERING = False
    print("⚠️  Flickering system not available")

# Import innovative feature agents
try:
    from agents import (
        create_anomaly_predictor,
        create_revision_analyzer,
        create_query_suggestion_agent,
        create_expert_network,
        create_counterfactual_simulator
    )
    INNOVATIVE_FEATURES_AVAILABLE = True
except ImportError:
    INNOVATIVE_FEATURES_AVAILABLE = False
    print("⚠️  Innovative feature agents not available")

# Import Phase 3 enhancement modules
try:
    from agents import (
        create_feedback_tracker,
        create_visualizer,
        create_report_generator
    )
    PHASE3_ENHANCEMENTS_AVAILABLE = True
except ImportError:
    PHASE3_ENHANCEMENTS_AVAILABLE = False
    print("⚠️  Phase 3 enhancements not available")


class EdisonProUI:
    """Gradio UI wrapper for EDISON PRO Q&A"""
    
    def __init__(self):
        self.orchestrator = None
        self.initialized = False
        self.error_message = None
        self.code_agent = None
        self.generated_files = {}  # Store generated files for download
        self.template_library = None  # Analysis templates
        self.current_template = None  # Currently selected template
        self.template_progress = []  # Track answered questions
        self.flickering_system = None  # Flickering cognitive architecture
        
        # Phase 3: Feedback & Visualization
        self.feedback_tracker = None
        self.visualizer = None
        self.report_generator = None
        self.last_feature_result = {}  # Store last result for feedback
        self.last_diagram_id = None
        
    def initialize(self):
        """Initialize EDISON PRO orchestrator"""
        try:
            self.orchestrator = DiagramAnalysisOrchestratorPro()
            
            # Check if Azure Search is available and has documents
            has_azure_search = self.orchestrator.context_manager.search_client is not None
            has_local_docs = len(self.orchestrator.context_manager.chunk_store) > 0
            
            if not has_azure_search and not has_local_docs:
                self.error_message = "⚠️ No analyzed documents found. Please run analysis first:\n\n" \
                                   "```\npython edisonpro.py --images ./input\n```\n\n" \
                                   "or\n\n" \
                                   "```\npython edisonpro.py --pdf document.pdf\n```"
                return False
            
            # If Azure Search is configured, we can query documents directly
            # No need for local chunk_store - it will be populated on first query
            if has_azure_search:
                print(f"✅ Connected to Azure Search - documents available for querying")
            
            # Commit any pending documents
            if self.orchestrator.context_manager.pending_documents:
                print(f"💾 Committing {len(self.orchestrator.context_manager.pending_documents)} pending documents...")
                self.orchestrator.context_manager.commit_to_search()
            
            # Initialize code agent if available
            if HAS_CODE_AGENT:
                self.code_agent = get_code_agent()
                if self.code_agent.available:
                    print("✅ Code Agent initialized - Data transformation enabled")
                else:
                    print("⚠️  Code Agent not configured (set AZURE_OPENAI_AGENT_* in .env)")
            
            # Initialize analysis templates if available
            if HAS_TEMPLATES:
                self.template_library = get_template_library()
                print(f"✅ Analysis Templates loaded - {len(self.template_library.templates)} templates available")
            
            # Initialize Phase 3 enhancements if available
            if PHASE3_ENHANCEMENTS_AVAILABLE:
                try:
                    self.feedback_tracker = create_feedback_tracker()
                    self.visualizer = create_visualizer()
                    self.report_generator = create_report_generator(self.visualizer)
                    print("✅ Phase 3 Enhancements initialized - Feedback & Visualization enabled")
                except Exception as e:
                    print(f"⚠️  Phase 3 initialization warning: {e}")
            
            self.initialized = True
            return True
            
        except Exception as e:
            self.error_message = f"❌ Initialization Error: {str(e)}\n\n" \
                               "Please check your .env configuration:\n" \
                               "- AZURE_OPENAI_PRO_ENDPOINT\n" \
                               "- AZURE_OPENAI_API_KEY\n" \
                               "- AZURE_OPENAI_PRO_DEPLOYMENT_NAME"
            return False
    
    async def ask_question_async(self, question: str, history: List[Tuple[str, str]], enable_web_search: bool = False) -> Tuple[str, str, str, str]:
        """
        Process question asynchronously with hybrid agent support.
        
        Args:
            question: User's question
            history: Conversation history
            enable_web_search: Enable Bing Search tool for web research (Code Agent only)
            
        Returns: (answer_text, table_html, download_files_html, chart_html)
        """
        if not self.initialized:
            return (self.error_message or "System not initialized", "", "", "")
        
        if not question or not question.strip():
            return ("Please enter a question.", "", "", "")
        
        try:
            print(f"\n🔍 Processing question: {question}")
            
            # Step 1: Check if code agent should handle this
            use_code_agent = False
            if HAS_CODE_AGENT and self.code_agent and self.code_agent.available:
                use_code_agent = self.code_agent.should_use_code_agent(question)
                print(f"   Code Agent decision: {'YES' if use_code_agent else 'NO'}")
            
            table_html = ""
            download_html = ""
            chart_html = ""
            
            if use_code_agent:
                # Step 2a: Use Code Agent for data transformation
                print("   🤖 Using Code Agent (GPT-5.4 + Code Interpreter + Meta-Agent fallback)")
                
                # Get context data for code agent
                context_data = self._prepare_code_agent_context()
                
                # Process with code agent (with optional web search)
                result = self.code_agent.process_data_query(
                    question=question,
                    context_data=context_data,
                    conversation_history=history,
                    enable_web_search=enable_web_search
                )
                
                # Format code agent response
                answer = result.get('answer', 'No response generated')
                response_parts = ["🤖 **Code Agent Response:**\n\n" + answer]
                
                if result.get('code_executed'):
                    response_parts.append("\n\n✓ *Code executed successfully*")
                
                # Check for tables (display after answer)
                if result.get('tables'):
                    table_html = self._format_tables(result['tables'])
                    response_parts.append("\n\n📊 **Generated Table:**\n(See table output below)")
                
                # Check for generated files (display after table)
                if result.get('files'):
                    print(f"[DEBUG] UI received result['files']: {result['files']}")
                    download_html = self._format_download_links(result['files'])
                    response_parts.append("\n\n📁 **Generated Files:**\n(See download buttons below)")
                
                # Check for charts (Phase 3 - Plotly) - display last
                if result.get('charts'):
                    chart_html = self._format_charts(result['charts'])
                    response_parts.append(f"\n\n📈 **Generated {len(result['charts'])} interactive chart(s)**\n(See chart output below)")
                
                return ("\n".join(response_parts), table_html, download_html, chart_html)
            
            else:
                # Step 2b: Use o3-pro for understanding
                print("   🧠 Using o3-pro (Deep Reasoning)")
                print(f"   Azure Search available: {self.orchestrator.context_manager.search_client is not None}")
                
                result = await self.orchestrator.ask_question_pro(
                    question,
                    max_chunks=8,
                    max_context_chars=6000,
                    max_output_tokens=2500,
                    timeout_seconds=180,
                    reasoning_effort="high",
                )
                print(f"   ✓ Got result from o3-pro")
                
                # Format response
                answer = result.get('answer', 'No answer generated')
                if not answer or answer == 'No answer generated':
                    raw_output = result.get('raw_output')
                    if raw_output:
                        answer = f"[Raw Output]\n{raw_output}"
                
                response_parts = [answer]

                if result.get('confidence'):
                    confidence = result['confidence']
                    conf_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                    response_parts.append(f"\n\n{conf_emoji} **Confidence:** {confidence:.1%}")

                # Add reasoning chain if available
                if result.get('reasoning_chain'):
                    response_parts.append("\n\n**🔍 Reasoning:**")
                    for i, step in enumerate(result['reasoning_chain'][:3], 1):
                        response_parts.append(f"{i}. {step}")

                # Add evidence if available
                if result.get('evidence'):
                    response_parts.append("\n\n**📋 Evidence:**")
                    for i, ev in enumerate(result['evidence'][:3], 1):
                        page = ev.get('page', 'N/A')
                        quote = ev.get('quote', 'N/A')
                        response_parts.append(f"{i}. *Page {page}:* \"{quote[:150]}...\"")
                
                # Add follow-up suggestion for data transformation
                if self._can_suggest_code_agent(answer):
                    response_parts.append("\n\n💡 **Tip:** Try asking for a table, chart, or CSV export for better visualization!")

                return ("\n".join(response_parts), "", "", "")

        except asyncio.TimeoutError:
            timeout_msg = (
                "⏱️ The model did not respond within the Gradio UI timeout window. "
                "Try a narrower question, reduce the amount of indexed content, or use the CLI for long-form analysis."
            )
            print(f"❌ UI timeout while processing question: {question}")
            return (timeout_msg, "", "", "")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Error processing question: {e}")
            print(f"   Details: {error_details}")
            error_msg = f"❌ Error processing question: {str(e)}\n\n**Details:**\n```\n{error_details}\n```"
            return (error_msg, "", "", "")
    
    def ask_question_sync(self, question: str, history: List[Tuple[str, str]], enable_web_search: bool = False) -> Tuple[str, str, str, str]:
        """Synchronous wrapper for Gradio"""
        return asyncio.run(self.ask_question_async(question, history, enable_web_search))
    
    def get_system_status(self) -> str:
        """Get current system status"""
        if not self.initialized:
            return self.error_message or "System not initialized"
        
        try:
            total_chunks = len(self.orchestrator.context_manager.chunk_store)
            staged_docs = len(self.orchestrator.context_manager.pending_documents)
            has_azure_search = self.orchestrator.context_manager.search_client is not None
            
            status = f"""
### 📊 System Status

- **Model:** {self.orchestrator.deployment_name}
- **Reasoning Effort:** HIGH
- **Azure Search:** {"✅ Connected" if has_azure_search else "❌ Not configured"}
- **Local Chunks:** {total_chunks}
- **Staged (pending):** {staged_docs}

**Status:** {"✅ Ready - Documents in Azure Search" if has_azure_search else "✅ Ready - Using local storage"}

💡 **Tip:** Documents are retrieved dynamically from Azure Search when you ask questions.
"""
            return status
        except Exception as e:
            return f"❌ Error getting status: {str(e)}"
    
    def _prepare_code_agent_context(self) -> dict:
        """Prepare context data for code agent from orchestrator."""
        context_data = {
            'interpretations': [],
            'visual_elements': [],
            'metadata': {}
        }
        
        try:
            # Get interpretations from orchestrator's local cache
            if hasattr(self.orchestrator, 'interpretations_by_chunk'):
                all_interpretations = []
                for chunk_id, interpretations in self.orchestrator.interpretations_by_chunk.items():
                    for interp in interpretations:
                        all_interpretations.append({
                            'chunk_id': chunk_id,
                            'component_id': interp.get('component_id'),
                            'type': interp.get('component_type'),
                            'specifications': interp.get('specifications', {}),
                            'function': interp.get('function'),
                            'page': interp.get('page'),
                            'confidence': interp.get('confidence', 0.0)
                        })
                context_data['interpretations'] = all_interpretations
            
            # If no local interpretations, try to retrieve from Azure Search
            if not context_data['interpretations'] and self.orchestrator.context_manager.search_client:
                print("   📥 Retrieving component data from Azure Search...")
                try:
                    # Query Azure Search for all engineering components
                    relevant_chunks = self.orchestrator.context_manager.retrieve_relevant_context(
                        "transformers circuit breakers motors components voltage ratings specifications",
                        max_chunks=50  # Get more documents for data transformation
                    )
                    
                    # Extract component data from chunks
                    for chunk in relevant_chunks:
                        metadata = chunk.get('metadata')
                        if metadata and hasattr(metadata, 'components') and metadata.components:
                            # Extract each component from the metadata
                            for component in metadata.components:
                                context_data['interpretations'].append({
                                    'chunk_id': metadata.chunk_id,
                                    'component_id': component,
                                    'page': metadata.page_numbers[0] if metadata.page_numbers else None,
                                    'content': chunk.get('content', '')[:500]  # Include snippet for context
                                })
                        else:
                            # Fallback: include content snippet
                            chunk_id = metadata.chunk_id if metadata else 'unknown'
                            context_data['interpretations'].append({
                                'chunk_id': chunk_id,
                                'content': chunk.get('content', '')[:800],  # More context
                                'page': metadata.page_numbers[0] if metadata and metadata.page_numbers else None
                            })
                    
                    print(f"   ✓ Retrieved {len(context_data['interpretations'])} component records from Azure Search")
                    
                except Exception as search_error:
                    print(f"   ⚠️ Azure Search retrieval failed: {search_error}")
            
            # Get visual elements if available
            if hasattr(self.orchestrator, 'visual_elements_by_chunk'):
                all_visual = []
                for chunk_id, elements in self.orchestrator.visual_elements_by_chunk.items():
                    if isinstance(elements, dict) and 'elements' in elements:
                        all_visual.extend(elements['elements'])
                context_data['visual_elements'] = all_visual
            
            # Add metadata
            context_data['metadata'] = {
                'total_chunks': len(self.orchestrator.context_manager.chunk_store),
                'has_azure_search': self.orchestrator.context_manager.search_client is not None,
                'data_source': 'azure_search' if self.orchestrator.context_manager.search_client else 'local_cache',
                'component_count': len(context_data['interpretations'])
            }
            
            print(f"   📊 Code Agent context: {len(context_data['interpretations'])} components, {len(context_data['visual_elements'])} visual elements")
            
        except Exception as e:
            print(f"⚠️ Error preparing context: {e}")
            import traceback
            traceback.print_exc()
        
        return context_data
    
    def _format_tables(self, tables: list) -> str:
        """Format tables as HTML for display."""
        if not tables:
            return ""
        
        html_parts = []
        for i, table in enumerate(tables):
            if table.get('type') == 'markdown':
                # Convert markdown table to HTML
                content = table.get('content', '')
                html_parts.append(f"<div style='overflow-x: auto;'><pre>{content}</pre></div>")
            elif table.get('type') == 'dataframe' and HAS_CODE_AGENT:
                # Convert pandas DataFrame to HTML
                try:
                    df = table.get('content')
                    if isinstance(df, pd.DataFrame):
                        html = df.to_html(index=False, classes='dataframe', border=1)
                        html_parts.append(f"<div style='overflow-x: auto;'>{html}</div>")
                except Exception as e:
                    html_parts.append(f"<p>Error displaying table: {e}</p>")
        
        return "\n".join(html_parts)
    
    def _format_charts(self, charts: list) -> str:
        """Format Plotly charts as HTML for display (Phase 3)."""
        if not charts:
            return ""
        
        html_parts = []
        for i, chart in enumerate(charts):
            if chart.get('type') == 'plotly':
                # Extract Plotly HTML
                chart_html = chart.get('html', '')
                # Wrap in responsive container
                html_parts.append(
                    f"<div style='width: 100%; margin: 10px 0;'>" 
                    f"{chart_html}"
                    f"</div>"
                )
            elif chart.get('type') == 'matplotlib':
                # Handle matplotlib images (base64 encoded)
                img_data = chart.get('image_data', '')
                if img_data:
                    html_parts.append(
                        f"<div style='text-align: center; margin: 10px 0;'>"
                        f"<img src='data:image/png;base64,{img_data}' style='max-width: 100%; height: auto;' />"
                        f"</div>"
                    )
        
        return "\n".join(html_parts)
    
    def _format_charts(self, charts: list) -> str:
        """Format Plotly charts as HTML for display (Phase 3)."""
        if not charts:
            return ""
        
        html_parts = []
        for i, chart in enumerate(charts):
            if chart.get('type') == 'plotly':
                # Extract Plotly HTML
                chart_html = chart.get('html', '')
                # Wrap in responsive container
                html_parts.append(
                    f"<div style='width: 100%; margin: 10px 0;'>" 
                    f"{chart_html}"
                    f"</div>"
                )
            elif chart.get('type') == 'matplotlib':
                # Handle matplotlib images (base64 encoded)
                img_data = chart.get('image_data', '')
                if img_data:
                    html_parts.append(
                        f"<div style='text-align: center; margin: 10px 0;'>"
                        f"<img src='data:image/png;base64,{img_data}' style='max-width: 100%; height: auto;' />"
                        f"</div>"
                    )
        
        return "\n".join(html_parts)
    
    def _format_download_links(self, file_paths: list) -> str:
        """Format download links for generated files.
        
        Args:
            file_paths: List of local file paths (e.g., ['out/chart.html'])
        """
        if not file_paths:
            return ""
        
        import os
        html_parts = ["<div style='margin-top: 15px; padding: 10px; background: #f5f5f5; border-radius: 5px;'>"]
        html_parts.append("<p style='font-weight: 600; margin-bottom: 10px;'>📥 Generated Files Ready for Download:</p>")
        
        for file_path in file_paths:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                abs_path = os.path.abspath(file_path)
                file_size = os.path.getsize(file_path)
                size_kb = file_size / 1024
                
                # Create a clickable link with the absolute path
                # Users can copy the path and open the file directly
                html_parts.append(f"""
                <div style='margin: 8px 0; padding: 10px; background: white; border: 1px solid #ddd; border-radius: 4px;'>
                    <div style='display: flex; align-items: center; justify-content: space-between;'>
                        <div>
                            <span style='font-weight: 500; color: #2196F3;'>📄 {file_name}</span>
                            <span style='color: #666; font-size: 0.9em; margin-left: 10px;'>({size_kb:.1f} KB)</span>
                        </div>
                    </div>
                    <div style='margin-top: 5px; font-family: monospace; font-size: 0.85em; color: #666;'>
                        � Location: <code style='background: #f5f5f5; padding: 2px 6px; border-radius: 3px;'>{abs_path}</code>
                    </div>
                    <div style='margin-top: 8px;'>
                        <button onclick='navigator.clipboard.writeText("{abs_path.replace(chr(92), chr(92)+chr(92))}"); this.textContent="✓ Copied!"; setTimeout(() => this.textContent="📋 Copy Path", 2000);' 
                                style='background: #2196F3; color: white; border: none; padding: 6px 12px; border-radius: 3px; cursor: pointer; font-size: 0.9em;'>
                            📋 Copy Path
                        </button>
                        <a href='file:///{abs_path.replace(chr(92), "/")}' target='_blank' 
                           style='margin-left: 8px; padding: 6px 12px; background: #4CAF50; color: white; text-decoration: none; border-radius: 3px; font-size: 0.9em; display: inline-block;'>
                            🔗 Open in Browser
                        </a>
                    </div>
                </div>
                """)
            else:
                html_parts.append(f"<p style='color: #f44336;'>⚠️ File not found: {file_path}</p>")
        
        html_parts.append("</div>")
        return "".join(html_parts)
    
    def _can_suggest_code_agent(self, answer: str) -> bool:
        """Check if we should suggest using code agent for this answer."""
        if not HAS_CODE_AGENT or not self.code_agent or not self.code_agent.available:
            return False
        
        # Suggest if answer contains lists of components
        indicators = [
            'components:', 'equipment:', 'transformers:', 'motors:',
            'list of', 'following', 'include:', 'contains:'
        ]
        return any(ind in answer.lower() for ind in indicators)
    
    def list_blob_files(self, container_name: str, prefix: str = "") -> str:
        """List files in blob storage"""
        if not HAS_BLOB_STORAGE:
            return "❌ Blob storage not available. Install: pip install azure-storage-blob azure-identity"
        
        try:
            blob_manager = create_blob_manager_from_env(container_name=container_name)
            if not blob_manager:
                return "❌ Could not connect to blob storage. Check .env configuration:\n" \
                       "- AZURE_STORAGE_CONNECTION_STRING or\n" \
                       "- AZURE_STORAGE_ACCOUNT_URL + AZURE_STORAGE_USE_MANAGED_IDENTITY"
            
            blobs = blob_manager.list_blobs(
                prefix=prefix,
                file_extensions=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
            )
            
            if not blobs:
                return f"📋 No files found in container '{container_name}' with prefix '{prefix}'"
            
            result = [f"📦 **Container:** {container_name}"]
            result.append(f"📁 **Prefix:** {prefix or '(root)'}")
            result.append(f"📋 **Found {len(blobs)} file(s):**\n")
            
            for i, blob in enumerate(blobs[:20], 1):  # Show first 20
                name = blob['name']
                size_mb = blob['size'] / (1024 * 1024)
                result.append(f"{i}. `{name}` ({size_mb:.2f} MB)")
            
            if len(blobs) > 20:
                result.append(f"\n... and {len(blobs) - 20} more files")
            
            blob_manager.cleanup_temp_files()
            return "\n".join(result)
            
        except Exception as e:
            return f"❌ Error listing blobs: {str(e)}"
    
    async def analyze_from_blob_async(
        self, 
        container_name: str, 
        prefix: str,
        output_container: str = "",
        progress=gr.Progress()
    ) -> str:
        """Analyze documents from blob storage"""
        if not HAS_BLOB_STORAGE:
            return "❌ Blob storage not available"
        
        try:
            progress(0.1, desc="Initializing blob storage...")
            
            blob_manager = create_blob_manager_from_env(container_name=container_name)
            if not blob_manager:
                return "❌ Could not connect to blob storage"
            
            progress(0.2, desc="Downloading files from blob...")
            
            # Download files
            local_files = blob_manager.download_blobs_to_temp(
                prefix=prefix,
                file_extensions=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"],
                max_workers=4
            )
            
            if not local_files:
                return "❌ No files found to analyze"
            
            progress(0.4, desc=f"Processing {len(local_files)} file(s)...")
            
            # Determine input type
            pdf_files = [f for f in local_files if f.lower().endswith('.pdf')]
            
            # Analyze
            if pdf_files:
                result = await self.orchestrator.analyze_document(pdf_files[0], "general", auto_plan=True)
            else:
                result = await self.orchestrator.analyze_images_from_folder(blob_manager.temp_dir, "general", auto_plan=True)
            
            progress(0.8, desc="Uploading results...")
            
            # Upload results if output container specified
            output_info = ""
            if output_container and self.orchestrator.preprocessor.intermediate_dir:
                try:
                    output_manager = create_blob_manager_from_env(container_name=output_container)
                    if output_manager:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_prefix = f"analysis-{timestamp}/"
                        
                        blob_urls = output_manager.upload_folder_to_blob(
                            str(self.orchestrator.preprocessor.intermediate_dir),
                            output_prefix,
                            max_workers=4
                        )
                        
                        output_info = f"\n\n✅ Uploaded {len(blob_urls)} result files to '{output_container}/{output_prefix}'"
                        output_manager.cleanup_temp_files()
                except Exception as e:
                    output_info = f"\n\n⚠️ Failed to upload results: {e}"
            
            # Cleanup
            blob_manager.cleanup_temp_files()
            
            progress(1.0, desc="Complete!")
            
            # Reinitialize to pick up new documents
            self.initialized = False
            self.initialize()

            routing_summary = ""
            if isinstance(result, dict) and result.get("pdf_classification"):
                reasons = result.get("pdf_routing_reasons", [])
                reason_line = f"\n📝 Router note: {reasons[0]}" if reasons else ""
                routing_summary = (
                    f"\n📄 PDF class: {result.get('pdf_classification', 'unknown')}"
                    f"\n🧭 Route: {result.get('pdf_routing_primary', 'pymupdf')}"
                    f" (fallback: {result.get('pdf_routing_fallback', 'none')})"
                    f"\n🔍 Extraction quality: {result.get('extraction_quality', 'unknown')}"
                    f"{reason_line}"
                )
            
            return f"✅ Analysis complete!\n" \
                   f"📊 Processed {len(local_files)} file(s)\n" \
                   f"💾 Results saved locally{output_info}{routing_summary}\n\n" \
                   f"🔄 System reinitialized - you can now ask questions!"
            
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
    
    def analyze_from_blob_sync(self, container_name: str, prefix: str, output_container: str = "") -> str:
        """Synchronous wrapper"""
        return asyncio.run(self.analyze_from_blob_async(container_name, prefix, output_container))
    
    # ========== Template Methods ==========
    
    def get_template_list(self, category_filter: str = "All") -> str:
        """Get formatted list of available templates"""
        if not HAS_TEMPLATES or not self.template_library:
            return "❌ Templates not available"
        
        try:
            # Filter by category
            if category_filter == "All":
                templates = self.template_library.list_templates()
            else:
                cat = TemplateCategory(category_filter.lower())
                templates = self.template_library.list_templates(category=cat)
            
            if not templates:
                return f"No templates found for category: {category_filter}"
            
            result = [f"## 📚 Available Analysis Templates ({len(templates)})\n"]
            
            for template in sorted(templates, key=lambda t: (t.category.value, t.name)):
                emoji = {
                    'electrical': '⚡',
                    'mechanical': '⚙️',
                    'pid': '🔬',
                    'civil': '🏗️',
                    'structural': '🏢',
                    'safety': '🛡️',
                    'compliance': '✅',
                    'general': '📋'
                }.get(template.category.value, '📄')
                
                result.append(f"### {emoji} {template.name}")
                result.append(f"**Category:** {template.category.value.title()} | "
                            f"**Domain:** {template.recommended_domain} | "
                            f"**Time:** ~{template.estimated_time_minutes} min")
                result.append(f"\n{template.description}\n")
                result.append(f"**Questions:** {len(template.questions)} "
                            f"({len([q for q in template.questions if q.priority == 1])} critical, "
                            f"{len([q for q in template.questions if q.requires_code_agent])} data transformation)")
                result.append(f"**Outputs:** {', '.join(template.output_formats)}")
                result.append(f"**Use Case:** {template.use_case}\n")
                result.append("---\n")
            
            return "\n".join(result)
        
        except Exception as e:
            return f"❌ Error loading templates: {str(e)}"
    
    def select_template(self, template_id: str) -> str:
        """Select and load a template"""
        if not HAS_TEMPLATES or not self.template_library:
            return "❌ Templates not available"
        
        try:
            template = self.template_library.get_template(template_id)
            if not template:
                return f"❌ Template not found: {template_id}"
            
            self.current_template = template
            self.template_progress = []
            
            summary = self.template_library.get_template_summary(template)
            
            # Add analysis sequence
            summary += "\n\n### 📋 Analysis Sequence\n\n"
            for i, question in enumerate(template.questions, 1):
                priority_stars = "⭐" * question.priority
                agent = "🤖 Code Agent" if question.requires_code_agent else "🧠 o3-pro"
                summary += f"**{i}.** {priority_stars} [{agent}] {question.question}\n"
                summary += f"   *Purpose:* {question.purpose} | *Format:* {question.expected_format}\n\n"
            
            # Add quality checks
            summary += "\n### ✅ Quality Checks\n\n"
            for check in template.quality_checks:
                summary += f"- {check}\n"
            
            summary += "\n\n💡 **Tip:** Click 'Start Template Analysis' to begin the guided workflow!"
            
            return summary
        
        except Exception as e:
            return f"❌ Error selecting template: {str(e)}"
    
    def get_next_template_question(self) -> Tuple[str, str, int, int]:
        """
        Get the next question in the current template
        
        Returns: (question_text, purpose, current_index, total_questions)
        """
        if not self.current_template:
            return ("No template selected", "", 0, 0)
        
        current_idx = len(self.template_progress)
        total = len(self.current_template.questions)
        
        if current_idx >= total:
            return ("Template complete! Review the analysis results above.", "", total, total)
        
        question = self.current_template.questions[current_idx]
        priority_emoji = "🔴 Critical" if question.priority == 1 else "🟡 Important" if question.priority == 2 else "🟢 Optional"
        agent_emoji = "🤖 Code Agent" if question.requires_code_agent else "🧠 o3-pro"
        
        formatted_question = f"{agent_emoji} {priority_emoji}\n\n**Question {current_idx + 1}/{total}:**\n\n{question.question}"
        
        return (formatted_question, question.purpose, current_idx + 1, total)
    
    async def process_template_question_async(self, answer_or_auto: str, history: List[Tuple[str, str]]) -> Tuple[str, str, str, str, str]:
        """
        Process current template question and get answer
        
        Args:
            answer_or_auto: User's custom question or "AUTO" to use template question
            history: Conversation history
            
        Returns: (answer, table_html, download_html, chart_html, next_question_prompt)
        """
        if not self.current_template:
            return ("❌ No template selected", "", "", "", "")
        
        current_idx = len(self.template_progress)
        if current_idx >= len(self.current_template.questions):
            # Template complete
            summary = self._generate_template_completion_summary()
            return (summary, "", "", "", "")
        
        question_obj = self.current_template.questions[current_idx]
        
        # Use template question or user's custom question
        if answer_or_auto == "AUTO" or not answer_or_auto.strip():
            question_to_ask = question_obj.question
        else:
            question_to_ask = answer_or_auto
        
        # Process the question
        answer, table_html, download_html, chart_html = await self.ask_question_async(
            question_to_ask, 
            history, 
            enable_web_search=False
        )
        
        # Record progress
        self.template_progress.append({
            'question': question_to_ask,
            'answer': answer,
            'has_table': bool(table_html),
            'has_download': bool(download_html),
            'has_chart': bool(chart_html)
        })
        
        # Get next question
        next_q, next_purpose, next_idx, total = self.get_next_template_question()
        
        if next_idx <= total:
            next_prompt = f"\n\n---\n\n### Next Question ({next_idx}/{total})\n\n{next_q}\n\n**Purpose:** {next_purpose}"
        else:
            next_prompt = "\n\n---\n\n### 🎉 Template Analysis Complete!\n\nAll questions have been answered. Review the results above."
        
        return (answer, table_html, download_html, chart_html, next_prompt)
    
    def process_template_question_sync(self, answer_or_auto: str, history: List[Tuple[str, str]]) -> Tuple[str, str, str, str, str]:
        """Synchronous wrapper"""
        return asyncio.run(self.process_template_question_async(answer_or_auto, history))
    
    def _generate_template_completion_summary(self) -> str:
        """Generate summary when template is complete"""
        if not self.current_template:
            return ""
        
        summary = [f"## 🎉 Template Analysis Complete: {self.current_template.name}\n"]
        summary.append(f"**Questions Answered:** {len(self.template_progress)}/{len(self.current_template.questions)}\n")
        
        # Count outputs generated
        tables_generated = sum(1 for p in self.template_progress if p.get('has_table'))
        downloads_generated = sum(1 for p in self.template_progress if p.get('has_download'))
        charts_generated = sum(1 for p in self.template_progress if p.get('has_chart'))
        
        summary.append(f"**Outputs Generated:**")
        summary.append(f"- 📊 Tables: {tables_generated}")
        summary.append(f"- 📥 Downloads: {downloads_generated}")
        summary.append(f"- 📈 Charts: {charts_generated}\n")
        
        # Quality checks reminder
        summary.append(f"### ✅ Quality Verification Checklist\n")
        summary.append(f"Review these items based on your analysis:\n")
        for i, check in enumerate(self.current_template.quality_checks, 1):
            summary.append(f"{i}. ☐ {check}")
        
        summary.append(f"\n\n### 📁 Recommended Outputs\n")
        summary.append(f"Generate these deliverables from your analysis:\n")
        for output_fmt in self.current_template.output_formats:
            summary.append(f"- {output_fmt}")
        
        summary.append(f"\n\n💡 **Next Steps:** Export your results and review against project requirements!")
        
        return "\n".join(summary)
    
    def reset_template(self) -> str:
        """Reset current template progress"""
        if self.current_template:
            template_name = self.current_template.name
            self.template_progress = []
            return f"✅ Template '{template_name}' reset. You can start over from question 1."
        return "No template currently selected."
    
    # ============================================================================
    # Phase 1 & Phase 2 Innovative Feature Handlers
    # ============================================================================
    
    def predict_anomalies_sync(self, image_path: str, domain: str) -> str:
        """Predict potential failures in diagram (Phase 1)"""
        return asyncio.run(self.predict_anomalies_async(image_path, domain))
    
    async def predict_anomalies_async(self, image_path: str, domain: str) -> str:
        """Predict potential failures using anomaly predictor"""
        if not INNOVATIVE_FEATURES_AVAILABLE:
            return "❌ Innovative features not available. Please check agent imports."
        
        if not image_path:
            return "Please upload a diagram image."
        
        try:
            from agents import create_anomaly_predictor
            
            # Get flickering system
            if self.flickering_system is None:
                self.flickering_system = FlickeringSystem(
                    storage_path="./memory_atlas",
                    theta_frequency=8.0,
                    mismatch_threshold=0.3
                )
            
            # Create predictor
            predictor = create_anomaly_predictor(
                memory_atlas=self.flickering_system.memory_atlas,
                reality_anchor=self.flickering_system.reality_anchor,
                similarity_threshold=0.75
            )
            
            # Run prediction
            result = await asyncio.to_thread(
                predictor.predict_anomalies,
                diagram=image_path,
                domain=domain,
                context={}
            )
            
            # Store result for feedback (Phase 3)
            from datetime import datetime
            self.last_feature_result = {
                'type': 'anomaly_prediction',
                'result': result,
                'domain': domain,
                'timestamp': datetime.now().isoformat()
            }
            self.last_diagram_id = f"anomaly_{datetime.now().timestamp()}"
            
            # Record feature usage (Phase 3)
            if self.feedback_tracker:
                try:
                    self.feedback_tracker.record_feature_usage(
                        feature_type='anomaly_prediction',
                        domain=domain,
                        success=True,
                        confidence=result.confidence,
                        processing_time_ms=0,  # TODO: track actual time
                        result_summary=f"{len(result.anomalies)} anomalies, risk {result.risk_score:.0%}"
                    )
                except Exception as e:
                    print(f"Warning: Failed to record usage: {e}")
            
            # Format result
            output = f"""### ⚠️ Anomaly Prediction Results

**Risk Score**: {result.risk_score:.0%} {'🔴 HIGH' if result.risk_score > 0.7 else '🟡 MEDIUM' if result.risk_score > 0.4 else '🟢 LOW'}  
**Confidence**: {result.confidence:.0%}  
**Anomalies Found**: {len(result.anomalies)}

"""
            
            if result.has_anomalies:
                output += "### 🚨 Detected Anomalies\n\n"
                for i, anomaly in enumerate(result.anomalies[:5], 1):
                    output += f"**{i}. {anomaly.get('pattern_name', 'Unknown')}**\n"
                    output += f"- Similarity: {anomaly.get('similarity', 0):.0%}\n"
                    output += f"- Risk: {anomaly.get('risk_level', 'unknown')}\n"
                    output += f"- Description: {anomaly.get('description', 'N/A')}\n\n"
                
                output += "\n### 💡 Recommendations\n\n"
                for i, rec in enumerate(result.recommendations[:5], 1):
                    output += f"{i}. {rec}\n"
                
                if result.prevention_cost_estimate and result.failure_cost_estimate:
                    output += f"\n### 💰 Cost-Benefit Analysis\n\n"
                    output += f"- **Prevention Cost**: ${result.prevention_cost_estimate:,.0f}\n"
                    output += f"- **Failure Cost**: ${result.failure_cost_estimate:,.0f}\n"
                    output += f"- **Potential Savings**: ${result.failure_cost_estimate - result.prevention_cost_estimate:,.0f}\n"
            else:
                output += "✅ No significant anomalies detected. Design appears to follow standard patterns.\n"
            
            return output
            
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
    
    def compare_revisions_sync(self, rev_a: str, rev_b: str, domain: str) -> str:
        """Compare two diagram revisions (Phase 1)"""
        return asyncio.run(self.compare_revisions_async(rev_a, rev_b, domain))
    
    async def compare_revisions_async(self, rev_a: str, rev_b: str, domain: str) -> str:
        """Compare diagram revisions using revision analyzer"""
        if not INNOVATIVE_FEATURES_AVAILABLE:
            return "❌ Innovative features not available. Please check agent imports."
        
        if not rev_a or not rev_b:
            return "Please upload both diagram revisions."
        
        try:
            from agents import create_revision_analyzer
            
            # Get flickering system and orchestrator
            if self.flickering_system is None:
                self.flickering_system = FlickeringSystem(
                    storage_path="./memory_atlas",
                    theta_frequency=8.0,
                    mismatch_threshold=0.3
                )
            
            # Create analyzer
            analyzer = create_revision_analyzer(
                reality_anchor=self.flickering_system.reality_anchor,
                orchestrator=self.orchestrator,
                sensitivity=0.05
            )
            
            # Run comparison
            result = await analyzer.analyze_revisions(
                revision_a=rev_a,
                revision_b=rev_b,
                revision_a_label="Rev A",
                revision_b_label="Rev B",
                domain=domain
            )
            
            # Format result
            output = f"""### 📊 Revision Comparison Results

**Total Changes**: {result.total_changes}  
**Critical Changes**: {len(result.critical_changes)}  
**Requires Review**: {'⚠️ YES' if result.requires_review else '✅ NO'}

### 📝 Summary

{result.summary}

"""
            
            if result.change_categories:
                output += "### 📂 Change Categories\n\n"
                for category, count in result.change_categories.items():
                    output += f"- **{category}**: {count}\n"
                output += "\n"
            
            if result.critical_changes:
                output += "### 🚨 Critical Changes\n\n"
                for i, change in enumerate(result.critical_changes[:5], 1):
                    output += f"{i}. {change}\n"
                output += "\n"
            
            if result.changes:
                output += "### 🔍 Detailed Changes\n\n"
                for i, change in enumerate(result.changes[:10], 1):
                    change_dict = change.to_dict() if hasattr(change, 'to_dict') else change
                    output += f"**{i}. {change_dict.get('type', 'Unknown')}**\n"
                    output += f"- Location: {change_dict.get('location', 'N/A')}\n"
                    output += f"- Description: {change_dict.get('description', 'N/A')}\n"
                    output += f"- Significance: {change_dict.get('significance', 'unknown')}\n\n"
            
            return output
            
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
    
    def suggest_questions_sync(self, image_path: str, domain: str) -> str:
        """Suggest verification questions (Phase 1)"""
        return asyncio.run(self.suggest_questions_async(image_path, domain))
    
    async def suggest_questions_async(self, image_path: str, domain: str) -> str:
        """Suggest questions using query suggestion agent"""
        if not INNOVATIVE_FEATURES_AVAILABLE:
            return "❌ Innovative features not available. Please check agent imports."
        
        if not image_path:
            return "Please upload a diagram image."
        
        try:
            from agents import create_query_suggestion_agent
            
            # Get flickering system
            if self.flickering_system is None:
                self.flickering_system = FlickeringSystem(
                    storage_path="./memory_atlas",
                    theta_frequency=8.0,
                    mismatch_threshold=0.3
                )
            
            # Create suggester
            suggester = create_query_suggestion_agent(
                reality_anchor=self.flickering_system.reality_anchor,
                memory_atlas=self.flickering_system.memory_atlas,
                orchestrator=self.orchestrator
            )
            
            # Get suggestions
            result = await suggester.suggest_questions(
                diagram=image_path,
                domain=domain,
                context={},
                user_questions_asked=[]
            )
            
            # Store result for feedback (Phase 3)
            from datetime import datetime
            self.last_feature_result = {
                'type': 'query_suggestion',
                'result': result,
                'domain': domain,
                'timestamp': datetime.now().isoformat()
            }
            self.last_diagram_id = f"query_{datetime.now().timestamp()}"
            
            # Record feature usage (Phase 3)
            if self.feedback_tracker:
                try:
                    self.feedback_tracker.record_feature_usage(
                        feature_type='query_suggestion',
                        domain=domain,
                        success=True,
                        confidence=0.85,  # Default confidence for suggestions
                        processing_time_ms=0,
                        result_summary=f"{len(result.suggested_questions)} questions, {result.critical_count} critical"
                    )
                    # Update question effectiveness
                    for q in result.suggested_questions:
                        q_dict = q.to_dict() if hasattr(q, 'to_dict') else q
                        self.feedback_tracker.update_question_effectiveness(
                            question_id=f"q_{hash(q_dict.get('question', ''))}_{domain}",
                            question_text=q_dict.get('question', ''),
                            domain=domain,
                            category=q_dict.get('category', 'general'),
                            was_asked=False,  # Just suggested
                            was_helpful=False,
                            found_issue=False
                        )
                except Exception as e:
                    print(f"Warning: Failed to record usage: {e}")
            
            # Format result
            output = f"""### 💡 Suggested Verification Questions

**Total Suggestions**: {len(result.suggested_questions)}  
**Critical Questions**: {result.critical_count}

### 🎯 Reasoning

{result.reasoning}

"""
            
            if result.categories:
                output += "### 📂 Question Categories\n\n"
                for category, count in result.categories.items():
                    output += f"- **{category}**: {count}\n"
                output += "\n"
            
            output += "### 💬 Recommended Questions\n\n"
            for i, q in enumerate(result.suggested_questions[:15], 1):
                q_dict = q.to_dict() if hasattr(q, 'to_dict') else q
                priority_emoji = "🔴" if q_dict.get('priority') == 'critical' else "🟡" if q_dict.get('priority') == 'high' else "🟢"
                output += f"{priority_emoji} **{i}. {q_dict.get('question', 'N/A')}**\n"
                output += f"   - Category: {q_dict.get('category', 'N/A')}\n"
                output += f"   - Rationale: {q_dict.get('rationale', 'N/A')}\n\n"
            
            return output
            
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
    
    def conduct_expert_review_sync(self, image_path: str, domain: str, design_phase: str) -> str:
        """Conduct multi-disciplinary expert review (Phase 2)"""
        return asyncio.run(self.conduct_expert_review_async(image_path, domain, design_phase))
    
    async def conduct_expert_review_async(self, image_path: str, domain: str, design_phase: str) -> str:
        """Conduct expert panel review using expert network"""
        if not INNOVATIVE_FEATURES_AVAILABLE:
            return "❌ Innovative features not available. Please check agent imports."
        
        if not image_path:
            return "Please upload a diagram image."
        
        try:
            from agents import create_expert_network
            
            # Get flickering system
            if self.flickering_system is None:
                self.flickering_system = FlickeringSystem(
                    storage_path="./memory_atlas",
                    theta_frequency=8.0,
                    mismatch_threshold=0.3
                )
            
            # Create expert network
            network = create_expert_network(
                orchestrator=self.orchestrator,
                memory_atlas=self.flickering_system.memory_atlas
            )
            
            # Conduct review
            result = await network.conduct_expert_review(
                diagram=image_path,
                domain=domain,
                context={},
                design_phase=design_phase
            )
            
            # Format result
            output = f"""### 👥 Expert Panel Review Results

**Overall Recommendation**: {result.overall_recommendation}  
**Consensus Level**: {result.consensus_level:.0%} {'✅' if result.consensus_level >= 0.75 else '⚠️'}  
**Expert Opinions**: {len(result.expert_opinions)}

"""
            
            if result.critical_issues:
                output += "### 🚨 Critical Issues\n\n"
                for i, issue in enumerate(result.critical_issues, 1):
                    output += f"{i}. {issue}\n"
                output += "\n"
            
            if result.action_items:
                output += "### ✅ Action Items\n\n"
                for i, item in enumerate(result.action_items, 1):
                    output += f"{i}. {item}\n"
                output += "\n"
            
            output += "### 🗣️ Expert Opinions\n\n"
            for opinion in result.expert_opinions:
                op_dict = opinion.to_dict() if hasattr(opinion, 'to_dict') else opinion
                approval_emoji = "✅" if op_dict.get('approval_status') == 'approved' else "⚠️" if op_dict.get('approval_status') == 'conditional' else "❌"
                output += f"{approval_emoji} **{op_dict.get('domain', 'Unknown').title()} Expert**\n"
                output += f"- Approval: {op_dict.get('approval_status', 'N/A')}\n"
                output += f"- Confidence: {op_dict.get('confidence', 0):.0%}\n"
                output += f"- Assessment: {op_dict.get('assessment', 'N/A')[:200]}...\n\n"
            
            if result.debate_points:
                output += "### 💬 Debate Points\n\n"
                for i, point in enumerate(result.debate_points[:5], 1):
                    output += f"{i}. {point}\n"
            
            return output
            
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
    
    def simulate_scenarios_sync(self, image_path: str, domain: str, goal: str, max_scenarios: int) -> str:
        """Simulate what-if scenarios (Phase 2)"""
        return asyncio.run(self.simulate_scenarios_async(image_path, domain, goal, max_scenarios))
    
    async def simulate_scenarios_async(self, image_path: str, domain: str, goal: str, max_scenarios: int) -> str:
        """Simulate counterfactual scenarios"""
        if not INNOVATIVE_FEATURES_AVAILABLE:
            return "❌ Innovative features not available. Please check agent imports."
        
        if not image_path:
            return "Please upload a diagram image."
        
        try:
            from agents import create_counterfactual_simulator
            
            # Get flickering system
            if self.flickering_system is None:
                self.flickering_system = FlickeringSystem(
                    storage_path="./memory_atlas",
                    theta_frequency=8.0,
                    mismatch_threshold=0.3
                )
            
            # Create simulator
            simulator = create_counterfactual_simulator(
                orchestrator=self.orchestrator,
                anticipatory_agent=None,
                memory_atlas=self.flickering_system.memory_atlas,
                max_scenarios=int(max_scenarios)
            )
            
            # Run simulation
            result = await simulator.simulate_scenarios(
                diagram=image_path,
                domain=domain,
                context={},
                parameters_to_vary=None,
                optimization_goal=goal
            )
            
            # Format result
            output = f"""### 🎲 Counterfactual Simulation Results

**Optimization Goal**: {goal.upper()}  
**Scenarios Evaluated**: {len(result.alternative_scenarios)}  
**Baseline**: {result.baseline_scenario.get('description', 'Current Design')}

"""
            
            if result.recommended_scenario:
                rec = result.recommended_scenario.to_dict() if hasattr(result.recommended_scenario, 'to_dict') else result.recommended_scenario
                output += f"""### 🎯 Recommended Scenario

**{rec.get('description', 'N/A')}**

- **Feasibility**: {rec.get('feasibility_score', 0):.0%}
- **Confidence**: {rec.get('confidence', 0):.0%}
- **Cost Change**: {rec.get('cost_delta', 0):+.1%}

{rec.get('rationale', 'N/A')[:300]}...

"""
            
            if result.optimization_insights:
                output += "### 💡 Key Insights\n\n"
                for insight in result.optimization_insights[:5]:
                    output += f"- {insight}\n"
                output += "\n"
            
            output += "### 📊 Scenario Comparison\n\n"
            for i, scenario in enumerate(result.alternative_scenarios[:5], 1):
                sc_dict = scenario.to_dict() if hasattr(scenario, 'to_dict') else scenario
                output += f"**{i}. {sc_dict.get('description', 'N/A')}**\n"
                metrics = sc_dict.get('performance_metrics', {})
                output += f"- Cost: {metrics.get('cost_multiplier', 1.0):.2f}x baseline\n"
                output += f"- Performance: {metrics.get('performance_score', 0.5):.0%}\n"
                output += f"- Safety: {metrics.get('safety_score', 0.5):.0%}\n"
                output += f"- Feasibility: {sc_dict.get('feasibility_score', 0.5):.0%}\n\n"
            
            if result.tradeoff_analysis:
                output += f"\n### ⚖️ Tradeoff Analysis\n\n```\n{result.tradeoff_analysis[:1000]}\n```\n"
            
            return output
            
        except Exception as e:
            import traceback
            return f"❌ Error: {str(e)}\n\n```\n{traceback.format_exc()}\n```"
    
    def analyze_flickering(self, image_path: str, num_cycles: int = 100, theta_frequency: float = 8.0, domain: str = "") -> Tuple[str, str, str]:
        """
        Perform flickering cognitive analysis on diagram
        Returns: (summary_html, trace_html, events_html)
        """
        if not HAS_FLICKERING:
            return "❌ Flickering system not available. Install with: pip install pillow numpy", "", ""
        
        try:
            # Initialize flickering system if not already done
            if self.flickering_system is None:
                self.flickering_system = FlickeringSystem(
                    storage_path="./memory_atlas",
                    theta_frequency=theta_frequency,
                    mismatch_threshold=0.3,
                    enable_background_simulation=False
                )
            
            # Run analysis
            results = self.flickering_system.analyze(
                diagram=image_path,
                num_cycles=num_cycles,
                theta_frequency=theta_frequency,
                domain=domain if domain else None,
                return_trace=True,
                generate_alternatives=True
            )
            
            # Format summary
            interp = results.get('interpretation', {})
            sys_info = results.get('system_info', {})
            
            summary_html = f"""
### 📊 Flickering Analysis Summary

**Confidence**: {interp.get('confidence', 0)*100:.1f}%  
**Total Cycles**: {results.get('num_cycles', 0)}  
**Mismatches Detected**: {results.get('num_mismatches', 0)}  
**Average Mismatch**: {interp.get('avg_mismatch', 0):.3f}  
**Latency**: {sys_info.get('total_latency_ms', 0)/1000:.2f}s  
**Memory Patterns**: {sys_info.get('memory_patterns', 0)}  

### 🔮 Interpretation

{interp.get('explanation', 'No explanation available')}
            """
            
            # Format attention trace
            trace = results.get('attention_trace', [])
            if trace:
                trace_html = "### 🎯 Attention Trace (Flickering Pattern)\n\n"
                trace_html += "```\n"
                for i, state in enumerate(trace[:50]):  # Show first 50 cycles
                    source = state.get('source', 'unknown')
                    alpha = state.get('alpha', 0)
                    mismatch = state.get('mismatch')
                    
                    bar_char = "█" if source == 'reality' else "░"
                    bar = bar_char * int(alpha * 20)
                    
                    mismatch_marker = f" [Δ={mismatch:.3f}]" if mismatch and mismatch > 0.3 else ""
                    
                    trace_html += f"Cycle {i:3d}: {bar:20s} ({source:7s}, α={alpha:.2f}){mismatch_marker}\n"
                
                trace_html += "```\n"
            else:
                trace_html = "No attention trace available"
            
            # Format mismatch events
            events = results.get('mismatch_events', [])
            if events:
                events_html = "### ⚡ Novelty Detection Events\n\n"
                for event in events:
                    level = event.get('novelty_level', 'unknown')
                    cycle = event.get('cycle', 0)
                    score = event.get('mismatch_score', 0)
                    
                    emoji = "🟢" if level == 'low' else "🟡" if level == 'medium' else "🟠" if level == 'high' else "🔴"
                    
                    events_html += f"{emoji} **Cycle {cycle}**: {level.upper()} novelty (Δ={score:.3f})\n\n"
            else:
                events_html = "No novelty events detected - diagram matched expected patterns"
            
            return summary_html, trace_html, events_html
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return f"❌ Error in flickering analysis: {str(e)}\n\n```\n{error_detail}\n```", "", ""
    
    # ============================================================================
    # Phase 3: Feedback & Analytics Methods
    # ============================================================================
    
    def record_feedback(self, feature_type: str, feedback_type: str, domain: str = None) -> str:
        """Record user feedback on last feature result"""
        if not PHASE3_ENHANCEMENTS_AVAILABLE or not self.feedback_tracker:
            return "⚠️ Phase 3 enhancements not available"
        
        if not self.last_diagram_id:
            return "⚠️ No recent feature result to provide feedback on"
        
        try:
            from agents import FeedbackEvent
            from datetime import datetime
            
            # Create feedback event
            event = FeedbackEvent(
                event_id=f"{feature_type}_{datetime.now().timestamp()}",
                feature_type=feature_type,
                timestamp=datetime.now().isoformat(),
                diagram_id=self.last_diagram_id,
                domain=domain or "unknown",
                feedback_type=feedback_type,
                context=self.last_feature_result.get(feature_type, {}),
                user_id="gradio_user"
            )
            
            # Record feedback
            self.feedback_tracker.record_feedback(event)
            
            feedback_emoji = {"helpful": "👍", "not_helpful": "👎", "found_issue": "✅"}.get(feedback_type, "📝")
            return f"{feedback_emoji} Feedback recorded! Thank you for helping improve the system."
            
        except Exception as e:
            return f"❌ Error recording feedback: {str(e)}"
    
    def get_analytics_dashboard(self) -> str:
        """Get analytics dashboard HTML"""
        if not PHASE3_ENHANCEMENTS_AVAILABLE or not self.feedback_tracker:
            return "⚠️ Phase 3 enhancements not available"
        
        try:
            # Generate analytics report
            report = self.feedback_tracker.generate_analytics_report()
            
            # Format as Markdown
            output = "### 📊 Feature Usage Analytics\n\n"
            output += report
            
            return output
            
        except Exception as e:
            return f"❌ Error generating analytics: {str(e)}"
    
    def get_top_questions(self, domain: str) -> str:
        """Get top performing questions for domain"""
        if not PHASE3_ENHANCEMENTS_AVAILABLE or not self.feedback_tracker:
            return "⚠️ Phase 3 enhancements not available"
        
        try:
            questions = self.feedback_tracker.get_top_questions(domain=domain, limit=10, min_score=0.6)
            
            if not questions:
                return f"📭 No questions available for {domain} domain yet. Start using the Query Suggestion feature!"
            
            output = f"### 💡 Top Questions for {domain.title()} Domain\n\n"
            for i, (q_id, text, score, times_suggested, times_asked) in enumerate(questions, 1):
                output += f"**{i}. {text}**\n"
                output += f"   - Effectiveness: {score:.0%}\n"
                output += f"   - Asked: {times_asked}/{times_suggested} times\n\n"
            
            return output
            
        except Exception as e:
            return f"❌ Error retrieving questions: {str(e)}"


def create_ui():
    """Create and configure Gradio interface"""
    
    # Initialize EDISON PRO
    app = EdisonProUI()
    init_success = app.initialize()
    
    # Custom CSS for professional look
    custom_css = """
    .gradio-container {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .header {
        text-align: center;
        padding: 24px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .header img {
        width: 64px;
        height: 64px;
        margin-bottom: 12px;
    }
    .header h1 {
        margin: 0 0 8px;
        font-size: 30px;
        letter-spacing: 1px;
    }
    .header p {
        margin: 4px 0;
        font-size: 16px;
        opacity: 0.9;
    }
    .status-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        color: #2d3436 !important;
    }
    .status-box * {
        color: #2d3436 !important;
    }
    .markdown-text {
        color: #2d3436 !important;
    }
    """
    
    # Create Gradio interface
    with gr.Blocks(css=custom_css, title="EDISON PRO - Engineering Diagram Q&A", theme=gr.themes.Soft()) as demo:
        
        # Header
        gr.HTML("""
        <div class="header">
            <img src="https://img.icons8.com/color/96/engineering.png" alt="Engineering Icon" />
            <h1>EDISON PRO</h1>
            <p>Engineering Diagram Analysis with o3-pro</p>
            <p>Intelligent Q&A Interface</p>
        </div>
        """)
        
        # Tabbed interface
        with gr.Tabs():
            # Tab 1: Q&A Chat
            with gr.Tab("💬 Q&A Chat"):
                with gr.Row():
                    # Left column - Chat interface
                    with gr.Column(scale=2):
                        gr.Markdown("### Ask Questions About Your Diagrams")
                        
                        chatbot = gr.Chatbot(
                            label="Conversation",
                            height=500,
                            show_label=False,
                            avatar_images=(None, "https://img.icons8.com/color/96/technical-support.png"),
                            bubble_full_width=False
                        )
                        
                        with gr.Row():
                            msg = gr.Textbox(
                                label="Your Question",
                                placeholder="e.g., What transformers are shown in the diagram? What is the voltage rating?",
                                lines=2,
                                scale=4
                            )
                            submit_btn = gr.Button("Ask", variant="primary", scale=1)
                        
                        with gr.Row():
                            enable_web_search = gr.Checkbox(
                                label="🌐 Enable Web Search (Bing)",
                                value=False,
                                info="Allow Code Agent to search the web for additional context and standards",
                                scale=3
                            )
                            clear_btn = gr.Button("Clear Chat", variant="secondary", size="sm", scale=1)
                        
                        sample_questions = [
                            "What type of diagram is this?",
                            "List all transformers and their ratings",
                            "What are the clearance requirements?",
                            "Explain the grounding system",
                            "What standards are referenced?",
                            "Describe the primary distribution layout"
                        ]

                        gr.Markdown("#### 💡 Example Questions (click to copy):")
                        with gr.Row():
                            for question in sample_questions[:3]:
                                btn = gr.Button(question, size="sm", variant="secondary")
                                btn.click(lambda q=question: q, None, msg)
                        with gr.Row():
                            for question in sample_questions[3:]:
                                btn = gr.Button(question, size="sm", variant="secondary")
                                btn.click(lambda q=question: q, None, msg)
                    
                    # Right column - Status and Info
                    with gr.Column(scale=1):
                        gr.Markdown("### ℹ️ System Information")
                        
                        status_display = gr.Markdown(
                            app.get_system_status(),
                            elem_classes=["status-box", "markdown-text"]
                        )
                        
                        refresh_btn = gr.Button("🔄 Refresh Status", variant="secondary", size="sm")
                        
                        # Code Agent status
                        if HAS_CODE_AGENT:
                            code_agent_status = "✅ Available" if app.code_agent and app.code_agent.available else "⚠️ Not configured"
                            gr.Markdown(f"""
                            ---
                            ### 🤖 Code Agent (GPT-5.4)
                            
                            **Status:** {code_agent_status}
                            
                            Enables data transformation:
                            - 📊 Generate tables
                            - 📥 Export CSV/Excel
                            - 📈 Create interactive charts (Phase 3)
                            - 🔢 Perform calculations
                            
                            **Try asking:**
                            - "Show all transformers as a table"
                            - "Plot voltage distribution"
                            - "Calculate total power load"
                            - "Export components to CSV"
                            """)
                        
                        gr.Markdown("""
                        ---
                        ### 🔧 How It Works
                        
                        1. **Context Retrieval**: Hybrid vector + keyword search
                        2. **o3-pro Reasoning**: Advanced analysis with reasoning chains
                        3. **Code Agent**: Data transformation & exports
                        4. **Evidence-Based**: Answers with source citations
                        
                        ---
                        ### 📝 Tips
                        
                        - Ask specific questions about components
                        - Request explanations of symbols or standards
                        - Inquire about design requirements
                        - Ask for cross-sheet references
                        - Try "show as table" for structured data
                        """)
                
                # Data output area (for tables, charts, and downloads from Code Agent)
                with gr.Row(visible=False) as data_output_row:
                    with gr.Column():
                        gr.Markdown("### 📊 Generated Data")
                        table_output = gr.HTML(label="Table Output")
                        chart_output = gr.HTML(label="Interactive Charts (Phase 3)")
                        download_output = gr.HTML(label="Download Links")
            
            # Tab 2: Blob Storage (if available)
            if HAS_BLOB_STORAGE:
                with gr.Tab("📦 Blob Storage"):
                    gr.Markdown("### Azure Blob Storage Integration")
                    gr.Markdown("Read engineering diagrams from blob storage and write analysis results back to blob.")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 📥 Browse Blob Container")
                            browse_container = gr.Textbox(
                                label="Container Name",
                                placeholder="engineering-diagrams",
                                value=os.getenv("AZURE_STORAGE_INPUT_CONTAINER", "")
                            )
                            browse_prefix = gr.Textbox(
                                label="Prefix (folder path)",
                                placeholder="drawings/2024/",
                                value=""
                            )
                            browse_btn = gr.Button("📋 List Files", variant="primary")
                            
                            browse_output = gr.Markdown("Click 'List Files' to see available documents")
            
            # Tab 3: Analysis Templates (if available)
            if HAS_TEMPLATES:
                with gr.Tab("📋 Analysis Templates"):
                    gr.Markdown("""
                    ### 📚 Predefined Analysis Workflows
                    
                    Use ready-made templates for common engineering analysis scenarios. Each template provides:
                    - ✅ Structured question sequence
                    - 🎯 Recommended domain and reasoning settings
                    - 📊 Expected output formats
                    - ✅ Quality checklists
                    - ⏱️ Estimated completion time
                    """)
                    
                    with gr.Row():
                        # Left column - Template browser
                        with gr.Column(scale=1):
                            gr.Markdown("#### 🔍 Browse Templates")
                            
                            category_filter = gr.Dropdown(
                                choices=["All", "Electrical", "Mechanical", "PID", "Civil", "Structural", "Safety", "Compliance", "General"],
                                value="All",
                                label="Filter by Category",
                                interactive=True
                            )
                            
                            template_list = gr.Markdown(
                                app.get_template_list("All") if app.initialized and HAS_TEMPLATES else "Initializing templates..."
                            )
                            
                            category_filter.change(
                                fn=app.get_template_list,
                                inputs=[category_filter],
                                outputs=[template_list]
                            )
                        
                        # Right column - Template details
                        with gr.Column(scale=2):
                            gr.Markdown("#### 📖 Template Details")
                            
                            template_selector = gr.Dropdown(
                                choices=[
                                    ("Electrical Load Study", "electrical_load_study"),
                                    ("P&ID Safety Review", "pid_safety_review"),
                                    ("Civil Site Plan Analysis", "civil_site_analysis"),
                                    ("Mechanical Equipment Schedule", "mechanical_equipment_schedule"),
                                    ("Quick Compliance Check", "compliance_check"),
                                    ("Bill of Materials Generation", "bom_generation"),
                                    ("Structural Design Review", "structural_design_review"),
                                ],
                                label="Select Template",
                                value=None,
                                interactive=True
                            )
                            
                            template_details = gr.Markdown("Select a template to view details...")
                            
                            load_template_btn = gr.Button("✅ Load This Template", variant="primary", size="lg")
                            
                            template_selector.change(
                                fn=app.select_template,
                                inputs=[template_selector],
                                outputs=[template_details]
                            )
                    
                    gr.Markdown("---")
                    
                    # Template execution area
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 🚀 Guided Template Analysis")
                            
                            template_status = gr.Markdown("Load a template above to begin guided analysis.")
                            
                            with gr.Row():
                                start_template_btn = gr.Button("▶️ Start Template Analysis", variant="primary")
                                reset_template_btn = gr.Button("🔄 Reset Progress", variant="secondary")
                            
                            gr.Markdown("#### Current Question")
                            
                            template_question_display = gr.Markdown("*No template loaded*")
                            
                            template_answer_input = gr.Textbox(
                                label="Your Answer (or leave blank to use template question as-is)",
                                placeholder="Press 'Answer Question' to use the template question automatically, or type a custom question here",
                                lines=3
                            )
                            
                            with gr.Row():
                                answer_template_q_btn = gr.Button("✅ Answer Question", variant="primary")
                                skip_q_btn = gr.Button("⏭️ Skip (Optional Only)", variant="secondary")
                            
                            # Template chat output
                            template_chatbot = gr.Chatbot(
                                label="Template Analysis Progress",
                                height=400,
                                show_label=True
                            )
                            
                            # Template data outputs
                            template_table_output = gr.HTML(label="Generated Tables")
                            template_chart_output = gr.HTML(label="Generated Charts")
                            template_download_output = gr.HTML(label="Download Links")
                            
                            # Wire up template execution
                            def start_template_analysis():
                                """Initialize template analysis"""
                                if not app.current_template:
                                    return (
                                        "⚠️ Please load a template first using the 'Load This Template' button above.",
                                        "No template loaded",
                                        []
                                    )
                                
                                q_text, q_purpose, idx, total = app.get_next_template_question()
                                status = f"✅ **Template Loaded:** {app.current_template.name}\n\n**Progress:** Question {idx}/{total}"
                                question_display = f"{q_text}\n\n**Purpose:** {q_purpose}"
                                
                                return (status, question_display, [])
                            
                            def answer_template_question(custom_answer, history):
                                """Process template question"""
                                answer, table, download, chart, next_q = app.process_template_question_sync(
                                    custom_answer if custom_answer else "AUTO",
                                    history
                                )
                                
                                # Get current question for display
                                q_text, q_purpose, idx, total = app.get_next_template_question()
                                
                                # Update history
                                current_q = app.current_template.questions[len(app.template_progress) - 1] if app.template_progress else None
                                displayed_q = current_q.question if current_q else custom_answer
                                new_history = history + [(displayed_q, answer)]
                                
                                # Update question display for next question
                                if idx <= total:
                                    question_display = f"{q_text}\n\n**Purpose:** {q_purpose}"
                                    status = f"✅ **Progress:** Question {idx}/{total}"
                                else:
                                    question_display = "🎉 **All questions complete!** Review your analysis above."
                                    status = f"✅ **Complete:** {len(app.template_progress)}/{total} questions answered"
                                
                                return (new_history, table, download, chart, question_display, status, "")
                            
                            def reset_template_analysis():
                                """Reset template progress"""
                                msg = app.reset_template()
                                q_text, q_purpose, idx, total = app.get_next_template_question()
                                question_display = f"{q_text}\n\n**Purpose:** {q_purpose}" if idx <= total else "No template loaded"
                                status = f"🔄 {msg}\n\n**Progress:** Question {idx}/{total}"
                                return ([], "", "", "", question_display, status)
                            
                            start_template_btn.click(
                                fn=start_template_analysis,
                                inputs=[],
                                outputs=[template_status, template_question_display, template_chatbot]
                            )
                            
                            answer_template_q_btn.click(
                                fn=answer_template_question,
                                inputs=[template_answer_input, template_chatbot],
                                outputs=[
                                    template_chatbot,
                                    template_table_output,
                                    template_download_output,
                                    template_chart_output,
                                    template_question_display,
                                    template_status,
                                    template_answer_input
                                ]
                            )
                            
                            reset_template_btn.click(
                                fn=reset_template_analysis,
                                inputs=[],
                                outputs=[
                                    template_chatbot,
                                    template_table_output,
                                    template_download_output,
                                    template_chart_output,
                                    template_question_display,
                                    template_status
                                ]
                            )
                        
                        with gr.Column():
                            gr.Markdown("#### 🚀 Analyze from Blob")
                            analyze_container = gr.Textbox(
                                label="Input Container",
                                placeholder="engineering-diagrams",
                                value=os.getenv("AZURE_STORAGE_INPUT_CONTAINER", "")
                            )
                            analyze_prefix = gr.Textbox(
                                label="Input Prefix",
                                placeholder="drawings/2024/project-x/",
                                value=""
                            )
                            output_container = gr.Textbox(
                                label="Output Container (optional)",
                                placeholder="edison-analysis-results",
                                value=os.getenv("AZURE_STORAGE_OUTPUT_CONTAINER", "")
                            )
                            analyze_btn = gr.Button("🚀 Start Analysis", variant="primary")
                            
                            analyze_output = gr.Markdown("Configure parameters and click 'Start Analysis'")
                    
                    gr.Markdown("""
                    ---
                    ### 💡 Blob Storage Tips
                    
                    - **Container**: Top-level blob storage container
                    - **Prefix**: Folder path within container (e.g., `drawings/2024/`)
                    - **Supported**: PDF, PNG, JPG, JPEG, TIFF, BMP
                    - **Output**: Results automatically uploaded to output container
                    - **Cost**: ~$0.004 per 10,000 read/write operations
                    
                    ### 🔐 Configuration
                    Set in `.env` file:
                    ```
                    AZURE_STORAGE_CONNECTION_STRING=your-connection-string
                    AZURE_STORAGE_INPUT_CONTAINER=engineering-diagrams
                    AZURE_STORAGE_OUTPUT_CONTAINER=edison-results
                    ```
                    """)
        
        # Chat interaction logic
        def respond(message, chat_history, enable_web_search=False):
            if not init_success:
                bot_message = app.error_message or "System not initialized"
                chat_history.append((message, bot_message))
                return "", chat_history, "", "", ""
            
            # Show "thinking" indicator
            thinking_msg = "🤔 Analyzing with o3-pro"
            if enable_web_search:
                thinking_msg += " + 🌐 Web Search"
            thinking_msg += "..."
            chat_history.append((message, thinking_msg))
            
            # Get answer (returns tuple: answer, table_html, download_html, chart_html)
            try:
                answer, table_html, download_html, chart_html = app.ask_question_sync(
                    message, chat_history, enable_web_search=enable_web_search
                )
            except Exception as e:
                answer = f"❌ Error: {str(e)}"
                table_html = ""
                download_html = ""
                chart_html = ""
            
            # Update with real answer
            chat_history[-1] = (message, answer)
            return "", chat_history, table_html, chart_html, download_html
        
        def clear_chat():
            return None
        
        def refresh_status():
            return app.get_system_status()
        
        # Connect events for Q&A tab
        msg.submit(respond, [msg, chatbot, enable_web_search], [msg, chatbot, table_output, chart_output, download_output])
        submit_btn.click(respond, [msg, chatbot, enable_web_search], [msg, chatbot, table_output, chart_output, download_output])
        clear_btn.click(clear_chat, None, chatbot, queue=False)
        refresh_btn.click(refresh_status, None, status_display)
        
        # Connect events for Blob Storage tab (if available)
        if HAS_BLOB_STORAGE:
            browse_btn.click(
                app.list_blob_files,
                inputs=[browse_container, browse_prefix],
                outputs=browse_output
            )
            
            analyze_btn.click(
                app.analyze_from_blob_sync,
                inputs=[analyze_container, analyze_prefix, output_container],
                outputs=analyze_output
            )
        
        # Tab 4: Innovative Features - Phase 1
        if INNOVATIVE_FEATURES_AVAILABLE:
            with gr.Tab("🔮 Innovative Features"):
                gr.Markdown("""
                ### 🚀 Proactive AI Features
                
                **Phase 1 Features:**
                - **Anomaly Prediction**: Detect potential failures before they occur
                - **Revision Analysis**: Automate diagram change tracking
                - **Query Suggestions**: Get intelligent question recommendations
                
                **Phase 2 Features:**
                - **Expert Network**: Multi-disciplinary panel review simulation
                - **Counterfactual Simulator**: "What-if" design optimization
                """)
                
                with gr.Tabs():
                    # Phase 1: Anomaly Prediction
                    with gr.Tab("⚠️ Anomaly Prediction"):
                        gr.Markdown("""
                        **Predict potential failures** before they occur by comparing against historical failure patterns.
                        Provides risk assessment, recommendations, and cost-benefit analysis.
                        """)
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                anomaly_image = gr.Image(label="Diagram Image", type="filepath", height=250)
                                anomaly_domain = gr.Dropdown(
                                    choices=["electrical", "mechanical", "pid", "civil", "structural"],
                                    value="electrical",
                                    label="Engineering Domain"
                                )
                                anomaly_btn = gr.Button("🔍 Predict Anomalies", variant="primary")
                            
                            with gr.Column(scale=2):
                                anomaly_result = gr.Markdown("Upload a diagram and click 'Predict Anomalies'")
                        
                        anomaly_btn.click(
                            fn=app.predict_anomalies_sync,
                            inputs=[anomaly_image, anomaly_domain],
                            outputs=anomaly_result
                        )
                    
                    # Phase 1: Revision Analysis
                    with gr.Tab("📊 Revision Analysis"):
                        gr.Markdown("""
                        **Compare diagram revisions** automatically with computer vision + AI interpretation.
                        Identifies changes, assesses significance, and highlights critical modifications.
                        """)
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                rev_a = gr.Image(label="Revision A (Original)", type="filepath", height=200)
                                rev_b = gr.Image(label="Revision B (Modified)", type="filepath", height=200)
                                rev_domain = gr.Dropdown(
                                    choices=["electrical", "mechanical", "pid", "civil", "structural"],
                                    value="electrical",
                                    label="Engineering Domain"
                                )
                                rev_btn = gr.Button("🔄 Compare Revisions", variant="primary")
                            
                            with gr.Column(scale=2):
                                rev_result = gr.Markdown("Upload two diagram revisions and click 'Compare Revisions'")
                        
                        rev_btn.click(
                            fn=app.compare_revisions_sync,
                            inputs=[rev_a, rev_b, rev_domain],
                            outputs=rev_result
                        )
                    
                    # Phase 1: Query Suggestions
                    with gr.Tab("💡 Query Suggestions"):
                        gr.Markdown("""
                        **Get intelligent question recommendations** tailored to your diagram.
                        Helps ensure comprehensive review by suggesting critical verification questions.
                        """)
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                query_image = gr.Image(label="Diagram Image", type="filepath", height=250)
                                query_domain = gr.Dropdown(
                                    choices=["electrical", "mechanical", "pid", "civil", "structural"],
                                    value="electrical",
                                    label="Engineering Domain"
                                )
                                query_btn = gr.Button("💬 Suggest Questions", variant="primary")
                            
                            with gr.Column(scale=2):
                                query_result = gr.Markdown("Upload a diagram and click 'Suggest Questions'")
                        
                        query_btn.click(
                            fn=app.suggest_questions_sync,
                            inputs=[query_image, query_domain],
                            outputs=query_result
                        )
                    
                    # Phase 2: Expert Network
                    with gr.Tab("👥 Expert Panel Review"):
                        gr.Markdown("""
                        **Multi-disciplinary expert panel simulation** with 6 specialized personas:
                        - Electrical Engineer, Safety Engineer, Mechanical Engineer
                        - Compliance Officer, Cost Estimator, Constructability Expert
                        
                        Provides consensus recommendation with debate analysis.
                        """)
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                expert_image = gr.Image(label="Diagram Image", type="filepath", height=250)
                                expert_domain = gr.Dropdown(
                                    choices=["electrical", "mechanical", "pid", "civil", "structural"],
                                    value="electrical",
                                    label="Engineering Domain"
                                )
                                expert_phase = gr.Dropdown(
                                    choices=["preliminary", "design_development", "construction_documents", "final"],
                                    value="preliminary",
                                    label="Design Phase"
                                )
                                expert_btn = gr.Button("👥 Conduct Expert Review", variant="primary")
                            
                            with gr.Column(scale=2):
                                expert_result = gr.Markdown("Upload a diagram and click 'Conduct Expert Review'")
                        
                        expert_btn.click(
                            fn=app.conduct_expert_review_sync,
                            inputs=[expert_image, expert_domain, expert_phase],
                            outputs=expert_result
                        )
                    
                    # Phase 2: Counterfactual Simulator
                    with gr.Tab("🎲 What-If Scenarios"):
                        gr.Markdown("""
                        **Design optimization through scenario exploration**:
                        - Vary key design parameters
                        - Predict outcomes (cost, performance, safety)
                        - Compare alternatives
                        - Get optimal recommendation
                        """)
                        
                        with gr.Row():
                            with gr.Column(scale=1):
                                cf_image = gr.Image(label="Diagram Image", type="filepath", height=250)
                                cf_domain = gr.Dropdown(
                                    choices=["electrical", "mechanical", "pid", "civil"],
                                    value="electrical",
                                    label="Engineering Domain"
                                )
                                cf_goal = gr.Dropdown(
                                    choices=["balanced", "cost", "performance", "safety"],
                                    value="balanced",
                                    label="Optimization Goal"
                                )
                                cf_scenarios = gr.Slider(
                                    minimum=3,
                                    maximum=15,
                                    value=10,
                                    step=1,
                                    label="Max Scenarios"
                                )
                                cf_btn = gr.Button("🎯 Simulate Scenarios", variant="primary")
                            
                            with gr.Column(scale=2):
                                cf_result = gr.Markdown("Upload a diagram and click 'Simulate Scenarios'")
                        
                        cf_btn.click(
                            fn=app.simulate_scenarios_sync,
                            inputs=[cf_image, cf_domain, cf_goal, cf_scenarios],
                            outputs=cf_result
                        )
        
        # Tab 5: Flickering Analysis (if available)
        if HAS_FLICKERING:
            with gr.Tab("🌊 Flickering Analysis"):
                gr.Markdown("""
                ### 🧠 Flickering Cognitive Architecture
                
                Advanced multi-agent analysis inspired by hippocampal navigation:
                - **Reality Anchor**: Extract current diagram features
                - **Memory Atlas**: Retrieve historical patterns
                - **Theta Oscillator**: Rhythmic flickering between reality and memory
                - **Anticipatory Simulation**: Pre-computed strategies
                - **Map Integration**: Compositional learning from novelty
                - **Pathway Generator**: Alternative interpretation hypotheses
                
                The system "flickers" between current perception and historical patterns
                to detect novelty and learn continuously.
                """)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### 📤 Upload Diagram")
                        flick_image = gr.Image(
                            label="Diagram Image",
                            type="filepath",
                            height=300
                        )
                        
                        gr.Markdown("#### ⚙️ Parameters")
                        flick_cycles = gr.Slider(
                            minimum=10,
                            maximum=200,
                            value=100,
                            step=10,
                            label="Number of Cycles",
                            info="More cycles = deeper analysis"
                        )
                        
                        flick_frequency = gr.Slider(
                            minimum=4.0,
                            maximum=10.0,
                            value=8.0,
                            step=0.5,
                            label="Theta Frequency (Hz)",
                            info="Oscillation speed (default: 8 Hz)"
                        )
                        
                        flick_domain = gr.Dropdown(
                            choices=["", "electrical", "mechanical", "pid", "civil", "structural"],
                            value="",
                            label="Domain (Optional)",
                            info="Leave empty for auto-detect"
                        )
                        
                        flick_analyze_btn = gr.Button("⚡ Start Flickering Analysis", variant="primary", size="lg")
                    
                    with gr.Column(scale=2):
                        gr.Markdown("#### 📊 Analysis Results")
                        flick_summary = gr.Markdown("Upload a diagram and click 'Start Flickering Analysis'")
                        flick_trace = gr.Markdown("")
                        flick_events = gr.Markdown("")
                
                # Wire up flickering analysis
                flick_analyze_btn.click(
                    fn=app.analyze_flickering,
                    inputs=[flick_image, flick_cycles, flick_frequency, flick_domain],
                    outputs=[flick_summary, flick_trace, flick_events]
                )
        
        # Tab 6: Analytics Dashboard (Phase 3)
        if PHASE3_ENHANCEMENTS_AVAILABLE:
            with gr.Tab("📊 Analytics Dashboard"):
                gr.Markdown("""
                ### 📈 Phase 3: Learning & Analytics
                
                Track feature usage, effectiveness scores, and system learning over time.
                Provides data-driven insights into which features and recommendations are most helpful.
                """)
                
                with gr.Tabs():
                    # Overall Analytics
                    with gr.Tab("📊 Overall Statistics"):
                        gr.Markdown("**Feature Usage Analytics**")
                        
                        analytics_refresh_btn = gr.Button("🔄 Refresh Analytics", variant="primary")
                        analytics_output = gr.Markdown("Click 'Refresh Analytics' to view statistics")
                        
                        analytics_refresh_btn.click(
                            fn=app.get_analytics_dashboard,
                            inputs=[],
                            outputs=analytics_output
                        )
                    
                    # Top Questions by Domain
                    with gr.Tab("💡 Top Questions"):
                        gr.Markdown("""
                        **Most Effective Questions by Domain**
                        
                        Questions are ranked by effectiveness score based on:
                        - How often users select them (Ask Rate: 30%)
                        - User feedback on helpfulness (Helpful Rate: 40%)
                        - Issue discovery rate (Issue Rate: 30%)
                        """)
                        
                        with gr.Row():
                            questions_domain = gr.Dropdown(
                                choices=["electrical", "mechanical", "pid", "civil", "structural"],
                                value="electrical",
                                label="Engineering Domain"
                            )
                            questions_btn = gr.Button("🔍 Get Top Questions", variant="primary")
                        
                        questions_output = gr.Markdown("Select a domain and click 'Get Top Questions'")
                        
                        questions_btn.click(
                            fn=app.get_top_questions,
                            inputs=[questions_domain],
                            outputs=questions_output
                        )
                    
                    # Feedback Guide
                    with gr.Tab("ℹ️ About Feedback"):
                        gr.Markdown("""
                        ### 🎯 How Feedback Improves EDISON PRO
                        
                        #### Feedback Types:
                        - **👍 Helpful**: Result was useful and accurate
                        - **👎 Not Helpful**: Result wasn't useful or had issues
                        - **✅ Found Issue**: Result helped identify a problem
                        
                        #### Learning Algorithm:
                        ```
                        Effectiveness Score = 
                            0.3 × Ask Rate + 
                            0.4 × Helpful Rate + 
                            0.3 × Issue Discovery Rate
                        ```
                        
                        The system uses **Exponential Moving Average** to smooth scores:
                        ```
                        New Score = 0.7 × Current Feedback + 0.3 × Historical Score
                        ```
                        
                        #### What Gets Better:
                        - **Query Suggestions**: Top questions rise to the top
                        - **Anomaly Patterns**: Patterns with better accuracy get prioritized
                        - **Expert Consensus**: Learn which expert combinations work best
                        - **Scenario Quality**: Optimize scenario generation parameters
                        
                        #### Privacy:
                        - Feedback is stored locally in SQLite
                        - User ID is anonymized ("gradio_user")
                        - Only effectiveness metrics are tracked
                        """)
        
        # Footer
        gr.HTML("""
        <div style="text-align: center; margin-top: 20px; padding: 10px; color: #666; font-size: 12px;">
            <p>EDISON PRO - Enhanced with Azure OpenAI o3-pro | Advanced Reasoning for Engineering Diagrams</p>
        </div>
        """)
    
    return demo


if __name__ == "__main__":
    print("🚀 Starting EDISON PRO Web UI...")
    print("📋 Initializing system...")
    
    demo = create_ui()
    
    print("\n" + "="*70)
    print("✅ EDISON PRO UI Ready!")
    print("🌐 Access the interface at: http://localhost:7860")
    print("="*70 + "\n")
    
    # Launch with configuration
    demo.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Change to an unused port
        share=False,
        show_error=True,
        inbrowser=True
    )