"""Robust dynamic meta-agent registry.

Implements:
- Persistent registry (SQLite) for agent specs and version lineage.
- Startup rehydration + reflection event replay fallback.
- Closed-loop run flow (run -> evaluate -> refine -> rerun).
- Hybrid evaluator with robust fallback scoring when provider is unavailable.
- Observability counters and last-run diagnostics.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default model for dynamically-created agents.  The GitHubCopilotAgent provider
# uses its own routing, but keeping the name consistent with the project's
# deployment makes lineage records interpretable alongside AzureOpenAI traces.
_DEFAULT_AGENT_MODEL: str = os.getenv("DYNAMIC_AGENT_MODEL", "gpt-5-pro")

try:
    from agent_framework.github import GitHubCopilotAgent

    COPILOT_PROVIDER_AVAILABLE = True
except Exception:
    GitHubCopilotAgent = None
    COPILOT_PROVIDER_AVAILABLE = False


@dataclass
class DynamicAgentSpec:
    agent_id: str
    name: str
    instructions: str
    capabilities: List[str]
    model: str = _DEFAULT_AGENT_MODEL
    created_by: str = "meta-agent"
    created_at: str = ""
    version: int = 1
    last_refined_at: Optional[str] = None
    status: str = "active"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if not payload.get("created_at"):
            payload["created_at"] = datetime.now(timezone.utc).isoformat()
        return payload


class DynamicMetaAgentRegistry:
    """Persistent dynamic agent registry with self-reflective closed loop."""

    def __init__(self) -> None:
        self._agents: Dict[str, DynamicAgentSpec] = {}
        self._sessions: Dict[str, Any] = {}
        self._last_run_by_agent: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # Use a fixed path relative to this file's location so the DB and JSONL
        # land in the same place regardless of the process working directory.
        self._memory_dir = Path(__file__).parent.parent / "memory_atlas"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._history_file = self._memory_dir / "dynamic_agent_reflection_history.jsonl"
        self._db_path = self._memory_dir / "dynamic_agent_registry.db"

        self._stats: Dict[str, Any] = {
            "startup_restored_agents": 0,
            "startup_replayed_events": 0,
            "startup_replay_failures": 0,
            "persistence_errors": 0,
            "creation_count": 0,
            "refinement_count": 0,
            "evaluation_count": 0,
            "fallback_evaluator_usage": 0,
            "last_reload_at": None,
        }

        self._init_db()
        self._hydrate_startup_state()

    @property
    def provider_available(self) -> bool:
        return COPILOT_PROVIDER_AVAILABLE

    def list_agents(self) -> List[Dict[str, Any]]:
        return [spec.to_dict() for spec in self._agents.values() if spec.status == "active"]

    def get_agent(self, agent_id: str) -> Optional[DynamicAgentSpec]:
        return self._agents.get(agent_id)

    def status_snapshot(self) -> Dict[str, Any]:
        return {
            "provider_available": self.provider_available,
            "registry_agents": len([a for a in self._agents.values() if a.status == "active"]),
            "startup_restored_agents": self._stats.get("startup_restored_agents", 0),
            "startup_replayed_events": self._stats.get("startup_replayed_events", 0),
            "startup_replay_failures": self._stats.get("startup_replay_failures", 0),
            "persistence_errors": self._stats.get("persistence_errors", 0),
            "creation_count": self._stats.get("creation_count", 0),
            "refinement_count": self._stats.get("refinement_count", 0),
            "evaluation_count": self._stats.get("evaluation_count", 0),
            "fallback_evaluator_usage": self._stats.get("fallback_evaluator_usage", 0),
            "last_reload_at": self._stats.get("last_reload_at"),
        }

    def reload_from_persistence(self) -> Dict[str, Any]:
        self._agents = {}
        self._hydrate_startup_state()
        self._stats["last_reload_at"] = datetime.now(timezone.utc).isoformat()
        return self.status_snapshot()

    def get_last_run_diagnostics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        if agent_id:
            return self._last_run_by_agent.get(agent_id, {})

        if not self._last_run_by_agent:
            return {}

        latest = max(
            self._last_run_by_agent.values(),
            key=lambda item: item.get("timestamp", ""),
        )
        return latest

    def get_agent_lineage(self, agent_id: str) -> Dict[str, Any]:
        with self._db_connection() as conn:
            rows = conn.execute(
                """
                SELECT agent_id, version, name, instructions, capabilities_json, model,
                       created_by, created_at, last_refined_at, status
                FROM agent_versions
                WHERE agent_id = ?
                ORDER BY version ASC
                """,
                (agent_id,),
            ).fetchall()

            events = conn.execute(
                """
                SELECT event_type, payload_json, timestamp
                FROM reflection_events
                WHERE agent_id = ?
                ORDER BY id ASC
                """,
                (agent_id,),
            ).fetchall()

        if not rows:
            return {"agent_id": agent_id, "versions": [], "events": []}

        versions = []
        for row in rows:
            versions.append(
                {
                    "agent_id": row[0],
                    "version": row[1],
                    "name": row[2],
                    "instructions": row[3],
                    "capabilities": json.loads(row[4]) if row[4] else [],
                    "model": row[5],
                    "created_by": row[6],
                    "created_at": row[7],
                    "last_refined_at": row[8],
                    "status": row[9],
                }
            )

        parsed_events = []
        for evt in events:
            parsed_events.append(
                {
                    "event_type": evt[0],
                    "payload": self._safe_json_loads(evt[1], {}),
                    "timestamp": evt[2],
                }
            )

        return {"agent_id": agent_id, "versions": versions, "events": parsed_events}

    async def ensure_agent_for_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        allow_create: bool = True,
    ) -> Dict[str, Any]:
        existing = self._find_matching_agent(task)
        if existing:
            return {
                "status": "matched_existing",
                "agent": existing.to_dict(),
                "reason": "Matched by capability overlap.",
            }

        if not allow_create:
            return {
                "status": "not_found",
                "agent": None,
                "reason": "No suitable agent found and creation disabled.",
            }

        created = await self._create_agent_via_meta(task, context or {})
        return {
            "status": "created",
            "agent": created.to_dict(),
            "reason": "Meta-agent generated a new task-focused agent.",
        }

    async def run_agent(
        self,
        agent_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        task: Optional[str] = None,
        auto_refine: bool = True,
        min_score: float = 0.72,
        max_refinement_rounds: int = 1,
    ) -> Dict[str, Any]:
        spec = self._agents.get(agent_id)
        if not spec:
            raise ValueError(f"Unknown agent_id: {agent_id}")

        active_session_id = session_id or str(uuid.uuid4())
        effective_task = (task or prompt).strip()
        dynamic_threshold = self._threshold_for_task(effective_task, min_score)

        refinement_applied = False
        refinement_count = 0
        last_eval: Dict[str, Any] = {}
        answer_text = ""

        rounds = max(0, int(max_refinement_rounds))
        for _ in range(rounds + 1):
            answer_text = await self._run_once_with_session(spec, prompt, active_session_id)
            last_eval = await self._evaluate_output(spec, effective_task, prompt, answer_text)
            self._stats["evaluation_count"] += 1
            self._record_reflection_event(
                event_type="evaluation",
                agent_id=spec.agent_id,
                version=spec.version,
                payload={
                    "agent_name": spec.name,
                    "task": effective_task,
                    "score": last_eval.get("score"),
                    "issues": last_eval.get("issues", []),
                    "recommendations": last_eval.get("recommendations", []),
                    "mode": last_eval.get("mode"),
                },
            )

            score = float(last_eval.get("score", 0.0))
            should_refine = bool(last_eval.get("should_refine", score < dynamic_threshold))

            if not auto_refine or not should_refine or score >= dynamic_threshold:
                break

            refined = await self._refine_agent_spec(spec=spec, task=effective_task, evaluation=last_eval)
            if not refined:
                break

            refinement_applied = True
            refinement_count += 1
            spec = refined

        run_diag = {
            "agent_id": spec.agent_id,
            "agent_name": spec.name,
            "agent_version": spec.version,
            "task": effective_task,
            "score": last_eval.get("score"),
            "evaluation_mode": last_eval.get("mode"),
            "refinement_applied": refinement_applied,
            "refinement_rounds": refinement_count,
            "threshold": dynamic_threshold,
            "session_id": active_session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._last_run_by_agent[spec.agent_id] = run_diag
        self._persist_run_diagnostic(run_diag)

        return {
            "agent_id": spec.agent_id,
            "agent_name": spec.name,
            "answer": answer_text,
            "session_id": active_session_id,
            "evaluation": last_eval,
            "refinement_applied": refinement_applied,
            "refinement_rounds": refinement_count,
            "agent_version": spec.version,
        }

    async def _run_once_with_session(self, spec: DynamicAgentSpec, prompt: str, session_id: str) -> str:
        if not COPILOT_PROVIDER_AVAILABLE:
            return self._run_without_provider(spec, prompt)

        copilot_agent = GitHubCopilotAgent(
            default_options={
                "instructions": spec.instructions,
                "model": spec.model,
            }
        )

        async with copilot_agent:
            session = self._sessions.get(session_id)
            if session is None:
                session = copilot_agent.create_session()
                # Evict oldest entries to prevent unbounded memory growth
                _MAX_SESSIONS = 200
                if len(self._sessions) >= _MAX_SESSIONS:
                    oldest_key = next(iter(self._sessions))
                    del self._sessions[oldest_key]
                self._sessions[session_id] = session
            result = await copilot_agent.run(prompt, session=session)
            return self._result_to_text(result)

    def _run_without_provider(self, spec: DynamicAgentSpec, prompt: str) -> str:
        caps = ", ".join(spec.capabilities[:6])
        return (
            "Provider unavailable; returning deterministic specialist draft.\n\n"
            f"Agent: {spec.name} (v{spec.version})\n"
            f"Capabilities: {caps}\n\n"
            "Task Response Draft:\n"
            f"1. Interpret request: {prompt}\n"
            "2. Produce structured output with explicit assumptions.\n"
            "3. Flag uncertain fields for verification.\n"
            "4. Suggest next validation actions."
        )

    def _seed_default_agents(self) -> None:
        defaults = [
            DynamicAgentSpec(
                agent_id="general-analyst",
                name="General Analyst",
                instructions=(
                    "You are a practical analysis assistant. Break problems down, "
                    "state assumptions, and produce concise actionable outputs."
                ),
                capabilities=["analysis", "reasoning", "planning", "summarization"],
                model=_DEFAULT_AGENT_MODEL,
                created_by="system",
                created_at=datetime.now(timezone.utc).isoformat(),
                version=1,
                status="active",
            ),
            DynamicAgentSpec(
                agent_id="data-transformer",
                name="Data Transformer",
                instructions=(
                    "You specialize in tabular transformation and extraction tasks. "
                    "Return structured outputs that are easy to serialize as JSON/CSV."
                ),
                capabilities=["tabular", "csv", "transform", "extract"],
                model=_DEFAULT_AGENT_MODEL,
                created_by="system",
                created_at=datetime.now(timezone.utc).isoformat(),
                version=1,
                status="active",
            ),
        ]

        for spec in defaults:
            self._agents[spec.agent_id] = spec
            self._upsert_agent_spec(spec)
            self._insert_agent_version(spec)

    def _find_matching_agent(self, task: str) -> Optional[DynamicAgentSpec]:
        task_terms = self._tokenize(task)
        best_score = 0
        best: Optional[DynamicAgentSpec] = None

        for spec in self._agents.values():
            if spec.status != "active":
                continue
            cap_terms = self._tokenize(" ".join(spec.capabilities) + " " + spec.name)
            overlap = len(task_terms.intersection(cap_terms))
            if overlap > best_score:
                best_score = overlap
                best = spec

        # Threshold of 2 is too low and causes false positives; require at least 3
        # overlapping tokens before treating an existing agent as a match.
        return best if best_score >= 3 else None

    async def _create_agent_via_meta(self, task: str, context: Dict[str, Any]) -> DynamicAgentSpec:
        if COPILOT_PROVIDER_AVAILABLE:
            maybe = await self._create_agent_via_copilot_meta(task, context)
            if maybe:
                return maybe
        return self._create_agent_heuristic(task)

    async def _create_agent_via_copilot_meta(self, task: str, context: Dict[str, Any]) -> Optional[DynamicAgentSpec]:
        meta_instructions = (
            "You are a meta-agent architect. Your job is to design new agents for capability blindspots. "
            "Return ONLY valid JSON matching this schema: "
            "{\"name\": string, \"instructions\": string, \"capabilities\": string[], \"model\": string}."
        )
        prompt = (
            "Design a new specialized agent for this missing capability task.\n"
            f"TASK:\n{task}\n\n"
            f"CONTEXT:\n{json.dumps(context, ensure_ascii=True)}\n\n"
            "Constraints:\n"
            "- Name short and descriptive.\n"
            "- 4-8 capabilities tags.\n"
            f"- Use model {_DEFAULT_AGENT_MODEL} unless task requires otherwise.\n"
        )

        meta_agent = GitHubCopilotAgent(
            default_options={"instructions": meta_instructions, "model": _DEFAULT_AGENT_MODEL}
        )

        try:
            async with meta_agent:
                raw = await meta_agent.run(prompt)
            payload = self._extract_json_object(self._result_to_text(raw))
            name = str(payload.get("name", "Generated Specialist")).strip()
            instructions = str(payload.get("instructions", "You are a specialist assistant.")).strip()
            capabilities = payload.get("capabilities", [])
            if not isinstance(capabilities, list):
                capabilities = ["specialist", "generated"]
            capabilities = [str(v).strip() for v in capabilities if str(v).strip()] or ["specialist", "generated"]
            model = str(payload.get("model", _DEFAULT_AGENT_MODEL)).strip() or _DEFAULT_AGENT_MODEL
            return self._register_new_agent(name, instructions, capabilities, model)
        except Exception:
            return None

    def _create_agent_heuristic(self, task: str) -> DynamicAgentSpec:
        terms = [t for t in self._tokenize(task) if len(t) > 3]
        top_terms = terms[:6] if terms else ["specialist", "blindspot"]
        name = f"{top_terms[0].title()} Specialist"
        instructions = (
            "You are a generated specialist agent created to address a capability gap. "
            f"Primary task scope: {task}. "
            "Deliver actionable, verifiable output and clearly flag uncertainty."
        )
        return self._register_new_agent(name, instructions, top_terms, _DEFAULT_AGENT_MODEL)

    async def _evaluate_output(
        self,
        spec: DynamicAgentSpec,
        task: str,
        prompt: str,
        answer: str,
    ) -> Dict[str, Any]:
        if COPILOT_PROVIDER_AVAILABLE:
            maybe = await self._evaluate_output_with_copilot(spec, task, prompt, answer)
            if maybe:
                return maybe

        self._stats["fallback_evaluator_usage"] += 1
        return self._evaluate_output_heuristic(task, prompt, answer)

    async def _evaluate_output_with_copilot(
        self,
        spec: DynamicAgentSpec,
        task: str,
        prompt: str,
        answer: str,
    ) -> Optional[Dict[str, Any]]:
        critique_agent = GitHubCopilotAgent(
            default_options={
                "instructions": (
                    "You are a strict agent-output evaluator. Return ONLY JSON with schema: "
                    "{\"score\": number, \"issues\": string[], \"strengths\": string[], "
                    "\"recommendations\": string[], \"should_refine\": boolean}."
                ),
                "model": _DEFAULT_AGENT_MODEL,
            }
        )

        critique_prompt = (
            f"TASK:\n{task}\n\n"
            f"AGENT NAME: {spec.name}\n"
            f"AGENT INSTRUCTIONS:\n{spec.instructions}\n\n"
            f"USER PROMPT:\n{prompt}\n\n"
            f"AGENT ANSWER:\n{answer[:6000]}\n\n"
            "Score task closure, relevance, structure, and hallucination risk."
        )

        try:
            async with critique_agent:
                raw = await critique_agent.run(critique_prompt)
            payload = self._extract_json_object(self._result_to_text(raw))
            score = max(0.0, min(1.0, float(payload.get("score", 0.0))))
            return {
                "score": score,
                "issues": payload.get("issues", []),
                "strengths": payload.get("strengths", []),
                "recommendations": payload.get("recommendations", []),
                "should_refine": bool(payload.get("should_refine", score < 0.72)),
                "mode": "copilot-evaluator",
                "confidence_band": self._confidence_band(score),
            }
        except Exception:
            return None

    def _evaluate_output_heuristic(self, task: str, prompt: str, answer: str) -> Dict[str, Any]:
        issues: List[str] = []
        strengths: List[str] = []
        recommendations: List[str] = []

        task_terms = self._tokenize(task)
        prompt_terms = self._tokenize(prompt)
        answer_terms = self._tokenize(answer)

        union_terms = task_terms.union(prompt_terms)
        overlap = len(union_terms.intersection(answer_terms))
        semantic = overlap / max(1, len(union_terms))

        key_terms = sorted(list(union_terms), key=len, reverse=True)[:8]
        covered = sum(1 for term in key_terms if term in answer_terms)
        coverage = covered / max(1, len(key_terms))

        length = len(answer.strip())
        has_steps = bool(re.search(r"(^|\n)\s*(\d+\.|- )", answer))
        has_sections = answer.count("\n") >= 3
        structure = 0.0
        structure += min(1.0, length / 1800.0) * 0.6
        structure += 0.2 if has_steps else 0.0
        structure += 0.2 if has_sections else 0.0

        certainty_hits = len(re.findall(r"\b(definitely|certainly|guaranteed|always)\b", answer.lower()))
        weak_evidence_hits = len(re.findall(r"\b(maybe|probably|likely|unclear|unknown)\b", answer.lower()))
        risk = min(1.0, (certainty_hits * 0.12) + (0.08 if weak_evidence_hits == 0 and length < 300 else 0.0))

        score = (semantic * 0.35) + (coverage * 0.30) + (structure * 0.20) + ((1.0 - risk) * 0.15)
        score = max(0.0, min(1.0, score))

        if semantic < 0.25:
            issues.append("Low semantic alignment with task/prompt.")
            recommendations.append("Reuse task terminology explicitly and map answer sections to request intent.")
        else:
            strengths.append("Semantic alignment with task intent is acceptable.")

        if coverage < 0.35:
            issues.append("Insufficient coverage of key task terms.")
            recommendations.append("Include missing required fields and constraints from the task statement.")
        else:
            strengths.append("Coverage of key terms is acceptable.")

        if structure < 0.45:
            issues.append("Response structure is weak for operational handoff.")
            recommendations.append("Provide numbered steps, assumptions, and a clear output schema.")
        else:
            strengths.append("Response structure supports execution.")

        if risk > 0.4:
            issues.append("Potential overconfidence or insufficient uncertainty signaling.")
            recommendations.append("Flag unverifiable claims and add explicit uncertainty markers.")

        should_refine = score < 0.72
        return {
            "score": score,
            "issues": issues,
            "strengths": strengths,
            "recommendations": recommendations,
            "should_refine": should_refine,
            "mode": "heuristic-evaluator-v2",
            "confidence_band": self._confidence_band(score),
            "signals": {
                "semantic": semantic,
                "coverage": coverage,
                "structure": structure,
                "risk": risk,
            },
        }

    async def _refine_agent_spec(
        self,
        spec: DynamicAgentSpec,
        task: str,
        evaluation: Dict[str, Any],
    ) -> Optional[DynamicAgentSpec]:
        if COPILOT_PROVIDER_AVAILABLE:
            refined = await self._refine_agent_spec_with_copilot(spec, task, evaluation)
            if refined:
                return refined

        recs = evaluation.get("recommendations", [])
        rec_text = " ".join([str(r).strip() for r in recs if str(r).strip()])
        if not rec_text:
            rec_text = "Increase task specificity and produce structured actionable output."

        spec.instructions = (
            spec.instructions
            + "\n\nRefinement Notes: "
            + rec_text
            + " Always provide step-by-step output and explicit assumptions."
        )
        spec.version += 1
        spec.last_refined_at = datetime.now(timezone.utc).isoformat()
        self._agents[spec.agent_id] = spec
        self._upsert_agent_spec(spec)
        self._insert_agent_version(spec)
        self._stats["refinement_count"] += 1
        self._record_reflection_event(
            event_type="refinement",
            agent_id=spec.agent_id,
            version=spec.version,
            payload={
                "agent_name": spec.name,
                "task": task,
                "mode": "heuristic-refiner",
                "evaluation_score": evaluation.get("score"),
            },
        )
        return spec

    async def _refine_agent_spec_with_copilot(
        self,
        spec: DynamicAgentSpec,
        task: str,
        evaluation: Dict[str, Any],
    ) -> Optional[DynamicAgentSpec]:
        refiner = GitHubCopilotAgent(
            default_options={
                "instructions": (
                    "You are an agent-refiner. Improve the existing agent design based on critique. "
                    "Return ONLY JSON with schema: "
                    "{\"name\": string, \"instructions\": string, \"capabilities\": string[], \"model\": string}."
                ),
                "model": _DEFAULT_AGENT_MODEL,
            }
        )

        prompt = (
            f"TASK:\n{task}\n\n"
            f"CURRENT AGENT NAME: {spec.name}\n"
            f"CURRENT INSTRUCTIONS:\n{spec.instructions}\n\n"
            f"CURRENT CAPABILITIES: {json.dumps(spec.capabilities)}\n\n"
            f"EVALUATION:\n{json.dumps(evaluation, ensure_ascii=True)}\n\n"
            "Return a refined agent spec that closes the identified gaps."
        )

        try:
            async with refiner:
                raw = await refiner.run(prompt)
            payload = self._extract_json_object(self._result_to_text(raw))
            spec.name = str(payload.get("name", spec.name)).strip() or spec.name
            spec.instructions = str(payload.get("instructions", spec.instructions)).strip() or spec.instructions
            capabilities = payload.get("capabilities", spec.capabilities)
            if isinstance(capabilities, list):
                spec.capabilities = [str(c).strip() for c in capabilities if str(c).strip()] or spec.capabilities
            spec.model = str(payload.get("model", spec.model)).strip() or spec.model
            spec.version += 1
            spec.last_refined_at = datetime.now(timezone.utc).isoformat()
            self._agents[spec.agent_id] = spec
            self._upsert_agent_spec(spec)
            self._insert_agent_version(spec)
            self._stats["refinement_count"] += 1
            self._record_reflection_event(
                event_type="refinement",
                agent_id=spec.agent_id,
                version=spec.version,
                payload={
                    "agent_name": spec.name,
                    "task": task,
                    "mode": "copilot-refiner",
                    "evaluation_score": evaluation.get("score"),
                },
            )
            return spec
        except Exception:
            return None

    def _register_new_agent(
        self,
        name: str,
        instructions: str,
        capabilities: List[str],
        model: str,
    ) -> DynamicAgentSpec:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        agent_id = slug or f"generated-{uuid.uuid4().hex[:8]}"
        while agent_id in self._agents:
            agent_id = f"{agent_id}-{uuid.uuid4().hex[:4]}"

        spec = DynamicAgentSpec(
            agent_id=agent_id,
            name=name,
            instructions=instructions,
            capabilities=capabilities,
            model=model or _DEFAULT_AGENT_MODEL,
            created_by="meta-agent",
            created_at=datetime.now(timezone.utc).isoformat(),
            version=1,
            status="active",
        )
        self._agents[agent_id] = spec
        self._upsert_agent_spec(spec)
        self._insert_agent_version(spec)
        self._stats["creation_count"] += 1
        self._record_reflection_event(
            event_type="creation",
            agent_id=spec.agent_id,
            version=spec.version,
            payload={
                "agent_name": spec.name,
                "capabilities": spec.capabilities,
                "model": spec.model,
            },
        )
        return spec

    def _record_reflection_event(self, event_type: str, agent_id: str, version: int, payload: Dict[str, Any]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        event = {
            "event_type": event_type,
            "timestamp": timestamp,
            "agent_id": agent_id,
            "version": version,
            "payload": payload,
        }

        try:
            with self._history_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=True) + "\n")
        except Exception:
            self._stats["persistence_errors"] += 1

        try:
            with self._db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO reflection_events(agent_id, version, event_type, payload_json, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (agent_id, version, event_type, json.dumps(payload, ensure_ascii=True), timestamp),
                )
                conn.commit()
        except Exception:
            self._stats["persistence_errors"] += 1

    def _persist_run_diagnostic(self, run_diag: Dict[str, Any]) -> None:
        try:
            with self._db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO run_diagnostics(run_id, agent_id, session_id, task, score, evaluator_mode,
                                                refined, rounds, details_json, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        run_diag.get("agent_id"),
                        run_diag.get("session_id"),
                        run_diag.get("task"),
                        run_diag.get("score"),
                        run_diag.get("evaluation_mode"),
                        1 if run_diag.get("refinement_applied") else 0,
                        int(run_diag.get("refinement_rounds", 0)),
                        json.dumps(run_diag, ensure_ascii=True),
                        run_diag.get("timestamp"),
                    ),
                )
                conn.commit()
        except Exception:
            self._stats["persistence_errors"] += 1

    def _threshold_for_task(self, task: str, base: float) -> float:
        family = self._task_family(task)
        family_defaults = {
            "compliance": 0.80,
            "transformation": 0.74,
            "planning": 0.72,
            "general": 0.70,
        }
        return max(float(base), family_defaults.get(family, 0.70))

    def _task_family(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["compliance", "standard", "code", "regulatory"]):
            return "compliance"
        if any(k in t for k in ["table", "csv", "extract", "transform", "normalize"]):
            return "transformation"
        if any(k in t for k in ["plan", "strategy", "roadmap", "approach"]):
            return "planning"
        return "general"

    def _confidence_band(self, score: float) -> str:
        if score >= 0.82:
            return "high"
        if score >= 0.65:
            return "medium"
        return "low"

    def _init_db(self) -> None:
        with self._db_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_specs (
                    agent_id TEXT PRIMARY KEY,
                    current_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_versions (
                    agent_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    instructions TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_refined_at TEXT,
                    status TEXT NOT NULL,
                    PRIMARY KEY (agent_id, version)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reflection_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_diagnostics (
                    run_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    session_id TEXT,
                    task TEXT,
                    score REAL,
                    evaluator_mode TEXT,
                    refined INTEGER NOT NULL,
                    rounds INTEGER NOT NULL,
                    details_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _hydrate_startup_state(self) -> None:
        restored = self._load_agents_from_db()
        if restored == 0:
            replayed = self._rebuild_from_reflection_if_empty()
            if replayed == 0 and len(self._agents) == 0:
                self._seed_default_agents()
                restored = len(self._agents)

        self._stats["startup_restored_agents"] = len(self._agents)

    def _load_agents_from_db(self) -> int:
        try:
            with self._db_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT s.agent_id, s.current_version, s.status, s.created_at,
                           v.name, v.instructions, v.capabilities_json, v.model,
                           v.created_by, v.last_refined_at
                    FROM agent_specs s
                    JOIN agent_versions v
                      ON v.agent_id = s.agent_id AND v.version = s.current_version
                    WHERE s.status = 'active'
                    """
                ).fetchall()

            for row in rows:
                spec = DynamicAgentSpec(
                    agent_id=row[0],
                    version=int(row[1]),
                    status=row[2],
                    created_at=row[3],
                    name=row[4],
                    instructions=row[5],
                    capabilities=self._safe_json_loads(row[6], []),
                    model=row[7],
                    created_by=row[8],
                    last_refined_at=row[9],
                )
                self._agents[spec.agent_id] = spec

            return len(rows)
        except Exception:
            self._stats["startup_replay_failures"] += 1
            return 0

    def _rebuild_from_reflection_if_empty(self) -> int:
        try:
            if not self._history_file.exists():
                return 0

            replay_count = 0
            with self._history_file.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    evt = self._safe_json_loads(line, {})
                    if not evt:
                        continue

                    etype = evt.get("event_type")
                    agent_id = evt.get("agent_id")
                    version = int(evt.get("version", 1))
                    payload = evt.get("payload", {})
                    timestamp = evt.get("timestamp", datetime.now(timezone.utc).isoformat())

                    if etype == "creation" and agent_id:
                        spec = DynamicAgentSpec(
                            agent_id=agent_id,
                            name=str(payload.get("agent_name", agent_id)),
                            instructions=str(payload.get("instructions", "You are a specialist assistant.")),
                            capabilities=payload.get("capabilities", ["specialist", "generated"]),
                            model=str(payload.get("model", _DEFAULT_AGENT_MODEL)),
                            created_by="replay",
                            created_at=timestamp,
                            version=version,
                            status="active",
                        )
                        self._agents[agent_id] = spec
                        self._upsert_agent_spec(spec)
                        self._insert_agent_version(spec)
                        replay_count += 1

            self._stats["startup_replayed_events"] = replay_count
            return replay_count
        except Exception:
            self._stats["startup_replay_failures"] += 1
            return 0

    def _upsert_agent_spec(self, spec: DynamicAgentSpec) -> None:
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO agent_specs(agent_id, current_version, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(agent_id) DO UPDATE SET
                        current_version=excluded.current_version,
                        status=excluded.status,
                        updated_at=excluded.updated_at
                    """,
                    (
                        spec.agent_id,
                        int(spec.version),
                        spec.status,
                        spec.created_at or now,
                        now,
                    ),
                )
                conn.commit()
        except Exception:
            self._stats["persistence_errors"] += 1

    def _insert_agent_version(self, spec: DynamicAgentSpec) -> None:
        try:
            with self._db_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_versions(
                        agent_id, version, name, instructions, capabilities_json,
                        model, created_by, created_at, last_refined_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        spec.agent_id,
                        int(spec.version),
                        spec.name,
                        spec.instructions,
                        json.dumps(spec.capabilities, ensure_ascii=True),
                        spec.model,
                        spec.created_by,
                        spec.created_at or datetime.now(timezone.utc).isoformat(),
                        spec.last_refined_at,
                        spec.status,
                    ),
                )
                conn.commit()
        except Exception:
            self._stats["persistence_errors"] += 1

    def _db_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9_]{3,}", text.lower()))

    @staticmethod
    def _result_to_text(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if hasattr(result, "text") and getattr(result, "text"):
            return str(getattr(result, "text"))
        return str(result)

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, Any]:
        text = text.strip()
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            obj = json.loads(text[start : end + 1])
            if isinstance(obj, dict):
                return obj
        raise ValueError("Meta-agent did not return parseable JSON object.")

    @staticmethod
    def _safe_json_loads(value: Any, default: Any) -> Any:
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except Exception:
            return default


_REGISTRY: Optional[DynamicMetaAgentRegistry] = None


def get_dynamic_registry() -> DynamicMetaAgentRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = DynamicMetaAgentRegistry()
    return _REGISTRY
