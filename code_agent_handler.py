"""
Author: Srikanth Bhakthan - Microsoft
Code Agent Handler for EDISON PRO
Uses Azure AI Agents with GPT-5.4, Code Interpreter, and Copilot-backed meta-agent fallback for data transformation

This module enables:
- Converting engineering diagram data into tables, charts, and downloadable files
- Performing calculations and analysis on extracted component data
- Generating visualizations from diagram information
- Exporting data in various formats (CSV, Excel, JSON)
- Web search augmentation with Bing Search for additional context
"""

import os
import asyncio
import json
import re
import threading
from typing import Dict, List, Any, Optional, Tuple
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import PromptAgentDefinition, CodeInterpreterTool
import logging
from dotenv import load_dotenv
load_dotenv(override=True)
logger = logging.getLogger(__name__)

try:
    from agents.dynamic_meta_agent import get_dynamic_registry
    DYNAMIC_META_AGENT_AVAILABLE = True
except Exception:
    get_dynamic_registry = None
    DYNAMIC_META_AGENT_AVAILABLE = False


class CodeAgentHandler:
    """
    Handles interaction with the managed EDISON code agent (GPT-5.4 with code interpreter)
    and falls back to the Copilot-backed dynamic meta-agent for more agentic tasks.
    """

    AGENTIC_KEYWORDS = {
        'agentic', 'autonomous', 'delegate', 'delegation', 'workflow', 'orchestrate',
        'orchestration', 'multi-step', 'multi step', 'plan and execute', 'investigate',
        'research and compare', 'iterate', 'refine', 'specialist agent', 'meta-agent',
        'meta agent', 'generate an agent', 'create an agent'
    }

    VALID_AGENT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$')
    
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
        raw_agent_name = (
            agent_id
            or os.getenv("AZURE_OPENAI_AGENT_NAME")
            or os.getenv("AZURE_OPENAI_AGENT_ID")
            or "edison-code-agent"
        )
        self.agent_name = self._normalize_agent_name(raw_agent_name)
        self.api_key = api_key or os.getenv("AZURE_OPENAI_AGENT_API_KEY")
        self.agent_model = os.getenv("AZURE_OPENAI_AGENT_MODEL", "gpt-5.4")
        self.enable_dynamic_fallback = os.getenv("CODE_AGENT_ENABLE_DYNAMIC_FALLBACK", "true").lower() not in {"0", "false", "no"}
        
        self.client = None
        self.openai_client = None
        self.agent = None
        self.thread_id = None
        self.available = False
        self.dynamic_registry = None

        if self.enable_dynamic_fallback and DYNAMIC_META_AGENT_AVAILABLE and get_dynamic_registry is not None:
            try:
                self.dynamic_registry = get_dynamic_registry()
            except Exception as exc:
                logger.warning(f"Dynamic meta-agent registry unavailable: {exc}")
        
        # Try to initialize
        self._initialize()

    def _default_agent_instructions(self) -> str:
        return (
            "You are EDISON PRO's code agent for engineering-diagram data work. "
            "Use code interpreter to transform extracted engineering data into tables, charts, "
            "counts, calculations, CSV/Excel outputs, and concise analytical summaries. "
            "Prefer structured outputs, cite assumptions, and preserve engineering identifiers, ratings, and page references."
        )

    def _normalize_agent_name(self, candidate: Optional[str]) -> str:
        candidate = (candidate or "edison-code-agent").strip()
        if self.VALID_AGENT_NAME_PATTERN.match(candidate):
            return candidate

        normalized = re.sub(r'[^a-zA-Z0-9-]+', '-', candidate).strip('-').lower()
        normalized = re.sub(r'-{2,}', '-', normalized)
        if len(normalized) > 63:
            normalized = normalized[:63].rstrip('-')
        if not normalized or not self.VALID_AGENT_NAME_PATTERN.match(normalized):
            normalized = "edison-code-agent"

        logger.warning(
            f"Configured agent identifier '{candidate}' is not a valid Foundry agent name; using managed agent name '{normalized}' instead."
        )
        return normalized

    def _has_dynamic_fallback(self) -> bool:
        return self.dynamic_registry is not None

    def _requires_agentic_approach(self, question: str) -> bool:
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in self.AGENTIC_KEYWORDS)

    def _ensure_project_agent(self):
        definition = PromptAgentDefinition(
            model=self.agent_model,
            instructions=self._default_agent_instructions(),
            tools=[CodeInterpreterTool()],
        )
        description = "EDISON PRO managed code agent for structured data transformation and analysis."
        metadata = {
            "managed_by": "edison-pro",
            "runtime": "azure-ai-projects",
            "model": self.agent_model,
        }

        try:
            existing = self.client.agents.get(self.agent_name)
            logger.info(f"Found configured code agent '{self.agent_name}', syncing definition to model {self.agent_model}.")
            return self.client.agents.update(
                self.agent_name,
                definition=definition,
                description=description,
                metadata=metadata,
            )
        except Exception:
            logger.info(f"Creating managed code agent '{self.agent_name}' with model {self.agent_model}.")
            return self.client.agents.create(
                name=self.agent_name,
                definition=definition,
                description=description,
                metadata=metadata,
            )

    def _run_coro_sync(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        result_box: Dict[str, Any] = {}
        error_box: Dict[str, BaseException] = {}

        def runner() -> None:
            try:
                result_box["value"] = asyncio.run(coro)
            except BaseException as exc:
                error_box["error"] = exc

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if "error" in error_box:
            raise error_box["error"]
        return result_box.get("value")
    
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
            if not self.project_endpoint:
                if self._has_dynamic_fallback():
                    logger.warning("Azure AI Projects endpoint not configured; using dynamic Copilot meta-agent fallback for code-agent tasks.")
                    self.available = True
                    return True
                logger.warning("Code Agent credentials not configured in .env - feature disabled")
                logger.info("Required: AZURE_OPENAI_AGENT_PROJECT_ENDPOINT")
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

            self.openai_client = self.client.get_openai_client()
            self.agent = self._ensure_project_agent()
            logger.info(
                f"✅ Code Agent initialized: {self.agent.name if hasattr(self.agent, 'name') else self.agent_name} ({self.agent_model})"
            )

            if self._has_dynamic_fallback():
                logger.info("✅ Dynamic Copilot meta-agent fallback available for agentic code-agent requests")
            
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
            logger.info("   - AZURE_OPENAI_AGENT_PROJECT_ENDPOINT=https://{account}.services.ai.azure.com/api/projects/{project}")
            logger.info("   - AZURE_OPENAI_AGENT_NAME=edison-code-agent  # preferred")
            logger.info(f"   - AZURE_OPENAI_AGENT_MODEL={self.agent_model}")
            logger.info("")
            if self._has_dynamic_fallback():
                logger.info("   Falling back to the dynamic Copilot meta-agent runtime for code-agent tasks.")
                self.available = True
                return True
            self.available = False
            return False
    
    def create_thread(self) -> Optional[str]:
        """
        Create or reuse a conversation for the managed code agent.
        
        Returns:
            Thread ID if successful, None otherwise
        """
        if not self.available or not self.openai_client:
            return None
            
        try:
            if self.thread_id:
                return self.thread_id
            conversation = self.openai_client.conversations.create(items=[])
            self.thread_id = conversation.id
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
        if not self.available and not self._has_dynamic_fallback():
            return False
        
        question_lower = question.lower()

        if self._requires_agentic_approach(question):
            logger.info("Code agent triggered by agentic-request keyword")
            return True
        
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
        if not self.available and not self._has_dynamic_fallback():
            return {
                'answer': 'Code Agent is not available. Please configure AZURE_OPENAI_AGENT_* variables in .env',
                'code_executed': False,
                'error': 'Code Agent not configured'
            }

        if self._requires_agentic_approach(question):
            fallback_result = self._run_dynamic_meta_agent(
                question=question,
                context_data=context_data,
                conversation_history=conversation_history,
                enable_web_search=enable_web_search,
                reason="agentic request"
            )
            if fallback_result:
                return fallback_result
        
        try:
            if self.openai_client and self.agent:
                result = self._run_project_code_agent(
                    question=question,
                    context_data=context_data,
                    conversation_history=conversation_history,
                    enable_web_search=enable_web_search,
                )
                logger.info(
                    f"Code agent completed. Generated {len(result.get('tables', []))} tables, "
                    f"{len(result.get('files', []))} files, {len(result.get('charts', []))} charts"
                )
                return result

            fallback_result = self._run_dynamic_meta_agent(
                question=question,
                context_data=context_data,
                conversation_history=conversation_history,
                enable_web_search=enable_web_search,
                reason="Azure AI Projects agent unavailable"
            )
            if fallback_result:
                return fallback_result

            return {
                'answer': 'Code Agent is not available. Please configure AZURE_OPENAI_AGENT_* variables in .env',
                'code_executed': False,
                'error': 'Code Agent not configured'
            }
            
        except Exception as e:
            logger.error(f"Code agent error: {e}", exc_info=True)
            fallback_result = self._run_dynamic_meta_agent(
                question=question,
                context_data=context_data,
                conversation_history=conversation_history,
                enable_web_search=enable_web_search,
                reason=f"Azure AI Projects execution error: {e}"
            )
            if fallback_result:
                return fallback_result
            return {
                'answer': f'An error occurred: {str(e)}',
                'code_executed': False,
                'error': str(e)
            }

    def _build_full_message(
        self,
        question: str,
        context_data: Dict[str, Any],
        conversation_history: Optional[List],
        enable_web_search: bool,
    ) -> str:
        context_message = self._prepare_context_message(context_data)

        if conversation_history:
            history_text = "\n\n**Previous Conversation:**\n"
            for msg in conversation_history[-3:]:
                if isinstance(msg, tuple) and len(msg) == 2:
                    user_msg, assistant_msg = msg
                    if user_msg:
                        history_text += f"user: {str(user_msg)[:200]}...\n"
                    if assistant_msg:
                        history_text += f"assistant: {str(assistant_msg)[:200]}...\n"
                elif isinstance(msg, dict):
                    history_text += f"{msg['role']}: {msg['content'][:200]}...\n"
            context_message = history_text + "\n\n" + context_message

        web_search_note = "\n\n**Web Search Preference:** The user requested web-grounded reasoning; if you do not have direct web access, say so and proceed with the available engineering context." if enable_web_search else ""
        return f"{context_message}\n\n**User Question:** {question}{web_search_note}"

    def _run_project_code_agent(
        self,
        question: str,
        context_data: Dict[str, Any],
        conversation_history: Optional[List],
        enable_web_search: bool,
    ) -> Dict[str, Any]:
        if not self.openai_client or not self.agent:
            raise RuntimeError("Azure AI Projects code agent is not initialized")

        full_message = self._build_full_message(question, context_data, conversation_history, enable_web_search)
        conversation_id = self.create_thread()
        if not conversation_id:
            raise RuntimeError("Failed to create conversation thread")

        self.openai_client.conversations.items.create(
            conversation_id=conversation_id,
            items=[{"type": "message", "role": "user", "content": full_message}],
        )

        logger.info(f"Running code agent on conversation {conversation_id} ({self.agent_model} + Code Interpreter)")
        response = self.openai_client.responses.create(
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": getattr(self.agent, "name", self.agent_name),
                    "type": "agent_reference",
                }
            },
            max_output_tokens=4000,
            truncation="auto",
        )

        result = self._extract_project_response_result(response)
        result["analysis_status"] = f"Azure AI Projects Code Agent ({self.agent_model})"
        return result

    def _extract_file_ids_recursive(self, node: Any) -> List[str]:
        file_ids: List[str] = []
        visited: set[int] = set()

        def walk(value: Any) -> None:
            identifier = id(value)
            if identifier in visited:
                return
            visited.add(identifier)

            if value is None:
                return
            if isinstance(value, dict):
                for key, inner in value.items():
                    if key in {"file_id", "container_file_id"} and isinstance(inner, str):
                        file_ids.append(inner)
                    else:
                        walk(inner)
                return
            if isinstance(value, (list, tuple, set)):
                for inner in value:
                    walk(inner)
                return
            if hasattr(value, "file_id") and isinstance(getattr(value, "file_id"), str):
                file_ids.append(getattr(value, "file_id"))
            if hasattr(value, "container_file_id") and isinstance(getattr(value, "container_file_id"), str):
                file_ids.append(getattr(value, "container_file_id"))
            if hasattr(value, "__dict__"):
                walk(vars(value))

        walk(node)
        return list(dict.fromkeys(file_ids))

    def _extract_project_response_result(self, response: Any) -> Dict[str, Any]:
        result = {
            'answer': getattr(response, 'output_text', '') or '',
            'code_executed': False,
            'tables': [],
            'files': [],
            'charts': [],
            'raw_messages': []
        }

        if hasattr(response, 'output') and response.output:
            text_parts: List[str] = []
            file_ids: List[str] = []
            for item in response.output:
                item_type = getattr(item, 'type', '')
                if 'code_interpreter' in item_type:
                    result['code_executed'] = True
                if item_type == 'message' and hasattr(item, 'content'):
                    for content_item in item.content:
                        text_attr = getattr(content_item, 'text', None)
                        if isinstance(text_attr, str):
                            text_parts.append(text_attr)
                        elif hasattr(text_attr, 'value') and text_attr.value:
                            text_parts.append(text_attr.value)
                        elif hasattr(content_item, 'value') and content_item.value:
                            text_parts.append(content_item.value)
                        file_ids.extend(self._extract_file_ids_recursive(content_item))
                file_ids.extend(self._extract_file_ids_recursive(item))

            if text_parts and not result['answer']:
                result['answer'] = "\n\n".join(part for part in text_parts if part).strip()
            result['raw_messages'] = [result['answer']] if result['answer'] else []
            result['files'] = list(dict.fromkeys(file_ids))

        if result['files']:
            out_folder = os.path.abspath('out')
            os.makedirs(out_folder, exist_ok=True)
            downloaded_files = []
            for file_id in result['files']:
                file_name = f"code_agent_output_{file_id[:8]}.bin"
                output_path = os.path.join(out_folder, file_name)
                if self.download_file(file_id, output_path):
                    downloaded_files.append(output_path)
            result['files'] = downloaded_files

        if '|' in result['answer'] and result['answer'].count('|') > 5:
            result['tables'].append({
                'type': 'markdown',
                'content': result['answer']
            })

        if '<div' in result['answer'] and ('plotly' in result['answer'].lower() or 'class="plotly-graph-div"' in result['answer']):
            plotly_pattern = r'(<(?:html|div)[^>]*>.*?</(?:html|div)>)'
            matches = re.findall(plotly_pattern, result['answer'], re.DOTALL | re.IGNORECASE)
            for match in matches:
                if 'plotly' in match.lower():
                    result['charts'].append({
                        'type': 'plotly',
                        'html': match
                    })

        return result

    def _prepare_dynamic_agent_prompt(
        self,
        question: str,
        context_data: Dict[str, Any],
        conversation_history: Optional[List],
        enable_web_search: bool,
    ) -> str:
        full_message = self._build_full_message(question, context_data, conversation_history, enable_web_search)
        return (
            "You are the Copilot-backed agentic fallback for EDISON PRO's code agent. "
            "Work like a specialist agent: break the task into steps mentally, but return only the final answer. "
            "If the user requests a table, return a markdown table. If they request calculations, show the formula and result.\n\n"
            f"{full_message}"
        )

    def _run_dynamic_meta_agent(
        self,
        question: str,
        context_data: Dict[str, Any],
        conversation_history: Optional[List],
        enable_web_search: bool,
        reason: str,
    ) -> Optional[Dict[str, Any]]:
        if not self._has_dynamic_fallback():
            return None

        try:
            task = f"Engineering data transformation and agentic analysis for: {question}"
            ensure_result = self._run_coro_sync(
                self.dynamic_registry.ensure_agent_for_task(
                    task=task,
                    context={
                        "reason": reason,
                        "question": question,
                        "enable_web_search": enable_web_search,
                        "mode": "code-agent-fallback",
                    },
                    allow_create=True,
                )
            )
            agent_payload = ensure_result.get("agent") or {}
            agent_id = agent_payload.get("agent_id")
            if not agent_id:
                return None

            run_result = self._run_coro_sync(
                self.dynamic_registry.run_agent(
                    agent_id=agent_id,
                    prompt=self._prepare_dynamic_agent_prompt(
                        question,
                        context_data,
                        conversation_history,
                        enable_web_search,
                    ),
                    task=task,
                    auto_refine=False,
                    max_refinement_rounds=0,
                )
            )

            answer = run_result.get("answer", "")
            result = {
                'answer': answer or 'Dynamic meta-agent did not return an answer.',
                'code_executed': False,
                'tables': [],
                'files': [],
                'charts': [],
                'analysis_status': f"Copilot Meta-Agent fallback ({run_result.get('agent_name', agent_id)})",
                'agent_id': agent_id,
            }

            if '|' in result['answer'] and result['answer'].count('|') > 5:
                result['tables'].append({
                    'type': 'markdown',
                    'content': result['answer']
                })

            return result
        except BaseException as exc:
            logger.error(f"Dynamic meta-agent fallback failed: {exc}", exc_info=True)
            return None
    
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
        if not self.available or not self.openai_client:
            return False
        
        try:
            logger.info(f"[DEBUG] download_file called for {file_id} -> {output_path}")
            
            file_content = self.openai_client.files.content(file_id)
            logger.info(f"[DEBUG] Got file content handle for {file_id}")

            payload = file_content.read() if hasattr(file_content, 'read') else bytes(file_content)

            with open(output_path, 'wb') as f:
                f.write(payload)

            logger.info(f"[DEBUG] Wrote file {output_path}")
            logger.info(f"[DEBUG] File size: {len(payload)} bytes")
            
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
