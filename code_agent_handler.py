"""
Author: Srikanth Bhakthan - Microsoft
Code Agent Handler for EDISON PRO
Uses Azure AI Agents with GPT-5, Code Interpreter, and Bing Search for data transformation

This module enables:
- Converting engineering diagram data into tables, charts, and downloadable files
- Performing calculations and analysis on extracted component data
- Generating visualizations from diagram information
- Exporting data in various formats (CSV, Excel, JSON)
- Web search augmentation with Bing Search for additional context
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
import logging
from dotenv import load_dotenv
load_dotenv(override=True)
logger = logging.getLogger(__name__)


class CodeAgentHandler:
    """
    Handles interaction with Azure AI Code Agent (GPT-5 with code interpreter)
    for data transformation and analysis tasks.
    """
    
    # Keywords that indicate code agent should be used
    DATA_TRANSFORMATION_KEYWORDS = {
        'table', 'csv', 'excel', 'spreadsheet', 'dataframe',
        'chart', 'plot', 'graph', 'visualize', 'visualization', 'diagram',
        'calculate', 'computation', 'sum', 'average', 'mean', 'total',
        'filter', 'sort', 'group', 'aggregate', 'count',
        'export', 'download', 'save', 'file',
        'bom', 'bill of materials', 'list all', 'show all',
        'statistics', 'analysis', 'distribution', 'histogram',
        'bar chart', 'pie chart', 'line chart', 'scatter plot', 'heatmap'
    }
    
    def __init__(
        self,
        project_endpoint: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize Code Agent Handler.
        
        Args:
            project_endpoint: Azure AI Project endpoint (from .env if not provided)
            agent_id: Agent ID (from .env if not provided)
            api_key: API key (from .env if not provided)
        """
        self.project_endpoint = project_endpoint or os.getenv("AZURE_OPENAI_AGENT_PROJECT_ENDPOINT")
        self.agent_id = agent_id or os.getenv("AZURE_OPENAI_AGENT_ID")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_AGENT_API_KEY")
        
        self.client = None
        self.agent = None
        self.thread_id = None
        self.available = False
        
        # Try to initialize
        self._initialize()
    
    def _initialize(self) -> bool:
        """
        Initialize the Azure AI Project client and agent.
        
        Note: Azure AI Projects SDK requires token-based authentication (TokenCredential).
        It does NOT support API key authentication directly.
        
        Authentication options:
        1. Azure CLI: Run 'az login' before starting the application
        2. VS Code: Sign in to Azure in VS Code
        3. Managed Identity: For production deployment
        4. Environment variables: Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
        """
        try:
            # Check if we have minimum required credentials
            if not self.project_endpoint or not self.agent_id:
                logger.warning("Code Agent credentials not configured in .env - feature disabled")
                logger.info("Required: AZURE_OPENAI_AGENT_ENDPOINT, AZURE_OPENAI_AGENT_PROJECT_ID")
                return False
            
            # Azure AI Projects SDK requires TokenCredential (not API key)
            # Use DefaultAzureCredential which tries multiple authentication methods:
            # 1. Environment variables (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID)
            # 2. Managed Identity (in Azure cloud)
            # 3. Azure CLI (if 'az login' was run)
            # 4. VS Code (if signed in to Azure)
            # 5. Interactive browser (last resort)
            
            logger.info("Initializing Code Agent with DefaultAzureCredential...")
            logger.info("Trying: Environment → Managed Identity → Azure CLI → VS Code → Browser")
            
            credential = DefaultAzureCredential()
            
            # Initialize client
            self.client = AIProjectClient(
                credential=credential,
                endpoint=self.project_endpoint
            )
            
            # Get the agent (now using GPT-5 with Code Interpreter)
            self.agent = self.client.agents.get_agent(self.agent_id)
            logger.info(f"✅ Code Agent initialized: {self.agent.name if hasattr(self.agent, 'name') else self.agent_id} (GPT-5)")
            
            self.available = True
            return True
            
        except Exception as e:
            logger.warning(f"Failed to initialize Code Agent: {e}")
            logger.info("")
            logger.info("💡 CODE AGENT AUTHENTICATION HELP:")
            logger.info("   Azure AI Projects requires token-based authentication (NOT API key)")
            logger.info("")
            logger.info("   Quick Fix Options:")
            logger.info("   1️⃣  Azure CLI:  Run 'az login' in terminal")
            logger.info("   2️⃣  VS Code:   Sign in to Azure (Ctrl+Shift+P → 'Azure: Sign In')")
            logger.info("   3️⃣  Env Vars:  Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
            logger.info("")
            logger.info("   Required .env variables:")
            logger.info("   - AZURE_OPENAI_AGENT_ENDPOINT=https://xxx.openai.azure.com")
            logger.info("   - AZURE_OPENAI_AGENT_PROJECT_ID=your-agent-id")
            logger.info("")
            self.available = False
            return False
    
    def create_thread(self) -> Optional[str]:
        """
        Create a new conversation thread.
        
        Returns:
            Thread ID if successful, None otherwise
        """
        if not self.available:
            return None
            
        try:
            thread = self.client.agents.threads.create()
            self.thread_id = thread.id
            logger.info(f"Created code agent thread: {self.thread_id}")
            return self.thread_id
        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            return None
    
    def should_use_code_agent(self, question: str) -> bool:
        """
        Determine if a question should be handled by the code agent.
        
        Args:
            question: User's question
            
        Returns:
            True if code agent should handle it, False otherwise
        """
        if not self.available:
            return False
        
        question_lower = question.lower()
        
        # Check for data transformation keywords
        for keyword in self.DATA_TRANSFORMATION_KEYWORDS:
            if keyword in question_lower:
                logger.info(f"Code agent triggered by keyword: {keyword}")
                return True
        
        # Check for question patterns that suggest data transformation
        patterns = [
            r'show .* (as|in) (a |an )?table',
            r'create (a |an )?(table|chart|graph|plot)',
            r'list all .*',
            r'give me .* in .* format',
            r'export .* to',
            r'calculate (the |total )?.*',
            r'how many .*',
            r'what (is|are) the (average|total|sum|count)'
        ]
        
        for pattern in patterns:
            if re.search(pattern, question_lower):
                logger.info(f"Code agent triggered by pattern: {pattern}")
                return True
        
        return False
    
    def process_data_query(
        self,
        question: str,
        context_data: Dict[str, Any],
        conversation_history: Optional[List] = None,
        enable_web_search: bool = False
    ) -> Dict[str, Any]:
        """
        Process a data transformation query using the code agent.
        
        Args:
            question: User's question
            context_data: Structured data from diagram analysis (interpretations, visual elements, etc.)
            conversation_history: Previous conversation for context (optional)
            enable_web_search: Enable Bing Search for additional context (default: False)
            
        Returns:
            Dictionary containing:
                - answer: Text response
                - code_executed: Whether code was executed
                - tables: List of dataframes/tables generated
                - files: List of files generated (for download)
                - charts: List of chart images generated
                - error: Error message if failed
        """
        if not self.available:
            return {
                'answer': 'Code Agent is not available. Please configure AZURE_OPENAI_AGENT_* variables in .env',
                'code_executed': False,
                'error': 'Code Agent not configured'
            }
        
        try:
            # Create thread if needed
            if not self.thread_id:
                self.create_thread()
            
            if not self.thread_id:
                return {
                    'answer': 'Failed to create conversation thread',
                    'code_executed': False,
                    'error': 'Thread creation failed'
                }
            
            # Prepare context message with structured data
            context_message = self._prepare_context_message(context_data)
            
            # Add conversation history if provided
            if conversation_history:
                history_text = "\n\n**Previous Conversation:**\n"
                for msg in conversation_history[-3:]:  # Last 3 messages for context
                    # Handle both tuple format (user, assistant) and dict format
                    if isinstance(msg, tuple) and len(msg) == 2:
                        user_msg, assistant_msg = msg
                        if user_msg:
                            history_text += f"user: {str(user_msg)[:200]}...\n"
                        if assistant_msg:
                            history_text += f"assistant: {str(assistant_msg)[:200]}...\n"
                    elif isinstance(msg, dict):
                        history_text += f"{msg['role']}: {msg['content'][:200]}...\n"
                context_message = history_text + "\n\n" + context_message
            
            # Send context and question
            web_search_note = "\n\n**Web Search Enabled:** You can use Bing Search to find additional context, standards, or technical information if needed." if enable_web_search else ""
            full_message = f"{context_message}\n\n**User Question:** {question}{web_search_note}"
            
            message = self.client.agents.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=full_message
            )
            
            # Configure tools based on web_search setting
            tool_resources = None
            connection_id = os.getenv("BING_CONNECTION_ID", "")
            
            if enable_web_search and connection_id:
                # Enable Bing Search tool for this run
                # Note: Requires Bing Search tool to be configured in the agent
                tool_resources = {"bing_grounding": {"connection_id": connection_id}}
                logger.info("Running code agent with Bing Search enabled")
            
            # Run the agent
            logger.info(f"Running code agent on thread {self.thread_id} (GPT-5 + Code Interpreter{' + Bing Search' if tool_resources else ''})")
            
            # Note: tool_resources parameter is used only if web search is enabled AND connection ID is valid
            if tool_resources:
                run = self.client.agents.runs.create_and_process(
                    thread_id=self.thread_id,
                    agent_id=self.agent.id,
                    tool_resources=tool_resources
                )
            else:
                run = self.client.agents.runs.create_and_process(
                    thread_id=self.thread_id,
                    agent_id=self.agent.id
                )
            
            # Check run status
            if run.status == "failed":
                error_msg = run.last_error if hasattr(run, 'last_error') else "Unknown error"
                logger.error(f"Code agent run failed: {error_msg}")
                return {
                    'answer': f'Code execution failed: {error_msg}',
                    'code_executed': True,
                    'error': str(error_msg)
                }
            
            # Get messages
            messages = self.client.agents.messages.list(
                thread_id=self.thread_id,
                order=ListSortOrder.ASCENDING
            )
            
            # Get run steps to extract file outputs from code interpreter
            run_steps = self.client.agents.run_steps.list(
                thread_id=self.thread_id,
                run_id=run.id
            )
            
            # Extract results
            result = self._extract_results(messages, run, run_steps)
            
            logger.info(f"Code agent completed. Generated {len(result.get('tables', []))} tables, "
                       f"{len(result.get('files', []))} files, {len(result.get('charts', []))} charts")
            
            return result
            
        except Exception as e:
            logger.error(f"Code agent error: {e}", exc_info=True)
            return {
                'answer': f'An error occurred: {str(e)}',
                'code_executed': False,
                'error': str(e)
            }
    
    def _prepare_context_message(self, context_data: Dict[str, Any]) -> str:
        """
        Prepare context message with engineering diagram data for the code agent.
        
        Args:
            context_data: Structured data from diagram analysis
            
        Returns:
            Formatted context string
        """
        context_parts = [
            "You are analyzing engineering diagram data. The following structured data has been extracted:",
            "",
            "**Available Data:**"
        ]
        
        # Add interpretations (component data)
        if 'interpretations' in context_data and context_data['interpretations']:
            context_parts.append("\n**Component Interpretations (JSON format):**")
            # Limit to avoid token overflow
            interpretations_json = json.dumps(context_data['interpretations'][:50], indent=2)
            if len(context_data['interpretations']) > 50:
                interpretations_json += f"\n... ({len(context_data['interpretations']) - 50} more components)"
            context_parts.append(f"```json\n{interpretations_json}\n```")
        
        # Add visual elements
        if 'visual_elements' in context_data and context_data['visual_elements']:
            context_parts.append("\n**Visual Elements Summary:**")
            ve_count = len(context_data['visual_elements'])
            context_parts.append(f"Total elements: {ve_count}")
            # Sample a few
            if ve_count > 0:
                sample = context_data['visual_elements'][:5]
                context_parts.append(f"Sample: {json.dumps(sample, indent=2)}")
        
        # Add metadata
        if 'metadata' in context_data:
            context_parts.append(f"\n**Metadata:** {json.dumps(context_data['metadata'], indent=2)}")
        
        context_parts.append("\n**Instructions:**")
        context_parts.append("- Use Python with pandas, plotly, or other libraries as needed")
        context_parts.append("- Generate tables, charts, or files based on the user's request")
        context_parts.append("- For tables: format as pandas DataFrame and show clearly")
        context_parts.append("- For exports: create CSV/Excel files with descriptive names")
        context_parts.append("- For charts: use plotly.express or plotly.graph_objects for interactive visualizations")
        context_parts.append("  * Save Plotly charts as HTML files to /mnt/data/ (e.g., /mnt/data/chart_name.html)")
        context_parts.append("  * Use fig.write_html('/mnt/data/filename.html') to save charts")
        context_parts.append("  * Files will be automatically downloaded to user's local machine")
        context_parts.append("  * Include clear labels, titles, and hover tooltips for engineering data")
        context_parts.append("  * Recommend: bar charts for component counts, line charts for trends, pie charts for distributions")
        context_parts.append("- Include engineering context (component IDs, specifications, ratings)")
        
        return "\n".join(context_parts)
    
    def _extract_results(self, messages, run, run_steps=None) -> Dict[str, Any]:
        """
        Extract results from agent messages.
        
        Args:
            messages: Agent messages
            run: Agent run object
            run_steps: Agent run steps (optional, for file extraction)
            
        Returns:
            Structured results dictionary
        """
        result = {
            'answer': '',
            'code_executed': False,
            'tables': [],
            'files': [],
            'charts': [],
            'raw_messages': []
        }
        
        # Extract file outputs from run steps (code interpreter outputs)
        if run_steps:
            logger.info(f"[DEBUG] Inspecting run_steps for file outputs...")
            logger.info(f"[DEBUG] run_steps type: {type(run_steps)}")
            for step in run_steps:
                logger.info(f"[DEBUG] Step type: {type(step)}, Step ID: {getattr(step, 'id', 'unknown')}")
                # Try attribute access first (for SDK objects), fallback to dict access
                try:
                    step_details = step.step_details if hasattr(step, 'step_details') else step.get('step_details', {})
                    tool_calls = step_details.tool_calls if hasattr(step_details, 'tool_calls') else step_details.get('tool_calls', [])
                    
                    if tool_calls:
                        for tool_call in tool_calls:
                            call_type = tool_call.type if hasattr(tool_call, 'type') else tool_call.get('type')
                            logger.info(f"[DEBUG] Tool call type: {call_type}")
                            
                            if call_type == 'code_interpreter':
                                result['code_executed'] = True
                                code_interp = tool_call.code_interpreter if hasattr(tool_call, 'code_interpreter') else tool_call.get('code_interpreter', {})
                                outputs = code_interp.outputs if hasattr(code_interp, 'outputs') else code_interp.get('outputs', [])
                                logger.info(f"[DEBUG] Code interpreter outputs: {len(outputs) if outputs else 0}")
                                
                                for output in outputs:
                                    output_type = output.type if hasattr(output, 'type') else output.get('type')
                                    logger.info(f"[DEBUG] Output type: {output_type}")
                                    
                                    if output_type == 'file':
                                        file_info = output.file if hasattr(output, 'file') else output.get('file', {})
                                        file_id = file_info.file_id if hasattr(file_info, 'file_id') else file_info.get('file_id')
                                        logger.info(f"[DEBUG] Found file output in run_steps: {file_id}")
                                        if file_id:
                                            result['files'].append(file_id)
                except Exception as e:
                    logger.error(f"[DEBUG] Error extracting from step: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        
        # Extract messages and file attachments
        import os
        for message in messages:
            if message.role == "assistant":
                # Extract text
                if message.text_messages:
                    text = message.text_messages[-1].text.value
                    result['raw_messages'].append(text)
                    
                    # Accumulate answer text
                    if result['answer']:
                        result['answer'] += "\n\n"
                    result['answer'] += text
                
                # Extract file attachments
                if hasattr(message, 'file_citations') and message.file_citations:
                    for citation in message.file_citations:
                        if hasattr(citation, 'file_id'):
                            result['files'].append(citation.file_id)
                
                # Check for attachments in message
                if hasattr(message, 'attachments') and message.attachments:
                    for attachment in message.attachments:
                        if hasattr(attachment, 'file_id'):
                            result['files'].append(attachment.file_id)
        
        # Check if code was executed (look for code interpreter tool in run)
        if hasattr(run, 'tools') and run.tools:
            for tool in run.tools:
                if hasattr(tool, 'type') and tool.type == 'code_interpreter':
                    result['code_executed'] = True
                    break
        
        # Download generated files to local 'out' folder
        if result['files']:
            # Create absolute path to 'out' folder in current working directory
            out_folder = os.path.abspath('out')
            os.makedirs(out_folder, exist_ok=True)
            downloaded_files = []
            logger.info(f"[DEBUG] Attempting to download files: {result['files']}")
            logger.info(f"[DEBUG] Output folder: {out_folder}")
            for file_id in result['files']:
                try:
                    # Get file info to determine name
                    file_name = f"code_agent_output_{file_id[:8]}.txt"  # Default name
                    # Try to extract filename from answer text (support multiple file types)
                    import re
                    filename_match = re.search(r'/mnt/data/(\S+\.(html|csv|xlsx|json|txt|pdf|png|jpg))', result['answer'])
                    if filename_match:
                        file_name = filename_match.group(1)
                    # Use absolute path
                    output_path = os.path.join(out_folder, file_name)
                    logger.info(f"[DEBUG] Downloading file_id {file_id} to {output_path}")
                    # Download file
                    if self.download_file(file_id, output_path):
                        downloaded_files.append(output_path)
                        logger.info(f"[DEBUG] Downloaded {file_name} to out/ folder")
                        # Update answer text to reference local file
                        result['answer'] = result['answer'].replace(
                            f'/mnt/data/{file_name}',
                            f'out/{file_name}'
                        )
                    else:
                        logger.error(f"[DEBUG] download_file returned False for {file_id}")
                except Exception as e:
                    logger.error(f"[DEBUG] Failed to download file {file_id}: {e}")
            logger.info(f"[DEBUG] Downloaded files: {downloaded_files}")
            result['files'] = downloaded_files  # Replace file IDs with local paths
        
        # Look for table-like content in markdown
        if '|' in result['answer'] and result['answer'].count('|') > 5:
            # Likely contains a markdown table
            result['tables'].append({
                'type': 'markdown',
                'content': result['answer']
            })
        
        # Extract Plotly charts (look for HTML containing Plotly divs)
        # Plotly charts output as HTML with <div id="..." class="plotly-graph-div">
        if '<div' in result['answer'] and ('plotly' in result['answer'].lower() or 'class="plotly-graph-div"' in result['answer']):
            # Extract all Plotly HTML sections
            import re
            # Find complete HTML charts (from opening <html> or <div> to closing tag)
            plotly_pattern = r'(<(?:html|div)[^>]*>.*?</(?:html|div)>)'
            matches = re.findall(plotly_pattern, result['answer'], re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                if 'plotly' in match.lower():
                    result['charts'].append({
                        'type': 'plotly',
                        'html': match
                    })
                    logger.info(f"Extracted Plotly chart ({len(match)} chars)")
        
        return result
    
    def download_file(self, file_id: str, output_path: str) -> bool:
        """
        Download a file generated by the code agent.
        
        Args:
            file_id: File ID from agent response
            output_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False
        
        try:
            logger.info(f"[DEBUG] download_file called for {file_id} -> {output_path}")
            
            # Always use manual download to ensure correct path
            # The .save() method doesn't respect absolute paths correctly
            file_content_stream = self.client.agents.files.get_content(file_id)
            logger.info(f"[DEBUG] Got file_content_stream for {file_id}")
            
            # Collect all chunks from the generator
            chunks = []
            for chunk in file_content_stream:
                logger.info(f"[DEBUG] Got chunk of size {len(chunk)} for {file_id}")
                if isinstance(chunk, (bytes, bytearray)):
                    chunks.append(chunk)
            
            # Write collected content to file using absolute path
            with open(output_path, 'wb') as f:
                for chunk in chunks:
                    f.write(chunk)
            
            logger.info(f"[DEBUG] Wrote file {output_path} with {len(chunks)} chunks")
            logger.info(f"[DEBUG] File size: {sum(len(c) for c in chunks)} bytes")
            
            # Verify file was created
            import os
            if os.path.exists(output_path):
                logger.info(f"[DEBUG] ✓ Verified file exists at {output_path}")
                return True
            else:
                logger.error(f"[DEBUG] ✗ File not found after write: {output_path}")
                return False
        except Exception as e:
            logger.error(f"[DEBUG] Failed to download file {file_id}: {e}")
            return False
    
    def reset_thread(self):
        """Reset the conversation thread."""
        self.thread_id = None
        logger.info("Code agent thread reset")


# Singleton instance
_code_agent_instance = None

def get_code_agent() -> CodeAgentHandler:
    """Get or create the singleton code agent instance."""
    global _code_agent_instance
    if _code_agent_instance is None:
        _code_agent_instance = CodeAgentHandler()
    return _code_agent_instance
