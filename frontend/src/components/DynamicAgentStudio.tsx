import { useEffect, useMemo, useState } from 'react';
import { Bot, PlusCircle, PlayCircle, RefreshCw, Sparkles, Wrench } from 'lucide-react';
import { api } from '../api/client';
import type {
  DynamicAgentsStatus,
  DynamicAgentSpec,
  EnsureDynamicAgentResponse,
  RunDynamicAgentResponse,
} from '../types';

export function DynamicAgentStudio() {
  const [status, setStatus] = useState<DynamicAgentsStatus | null>(null);
  const [agents, setAgents] = useState<DynamicAgentSpec[]>([]);
  const [loading, setLoading] = useState(false);
  const [ensureLoading, setEnsureLoading] = useState(false);
  const [runLoading, setRunLoading] = useState(false);
  const [opsLoading, setOpsLoading] = useState(false);

  const [task, setTask] = useState('');
  const [contextJson, setContextJson] = useState('{"domain":"engineering-diagrams","priority":"high"}');
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [prompt, setPrompt] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [autoRefine, setAutoRefine] = useState(true);
  const [minScore, setMinScore] = useState(0.72);
  const [maxRefinementRounds, setMaxRefinementRounds] = useState(1);

  const [ensureResult, setEnsureResult] = useState<EnsureDynamicAgentResponse | null>(null);
  const [runResult, setRunResult] = useState<RunDynamicAgentResponse | null>(null);
  const [lastRunDiagnostics, setLastRunDiagnostics] = useState<Record<string, unknown> | null>(null);
  const [lineage, setLineage] = useState<Record<string, unknown> | null>(null);
  const [showRawDiagnostics, setShowRawDiagnostics] = useState(false);
  const [showRawLineage, setShowRawLineage] = useState(false);
  const [error, setError] = useState('');

  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.agent_id === selectedAgentId) || null,
    [agents, selectedAgentId]
  );

  const diagnosticsSummary = useMemo(() => {
    if (!lastRunDiagnostics) return null;
    const d = lastRunDiagnostics;

    const asNumber = (v: unknown): number | null => (typeof v === 'number' ? v : null);
    const asString = (v: unknown): string => (typeof v === 'string' ? v : 'n/a');
    const asBool = (v: unknown): boolean | null => (typeof v === 'boolean' ? v : null);

    return {
      agentName: asString(d.agent_name),
      agentVersion: asNumber(d.agent_version),
      score: asNumber(d.score),
      evaluatorMode: asString(d.evaluation_mode),
      confidenceBand: asString((d.evaluation as Record<string, unknown> | undefined)?.confidence_band),
      refined: asBool(d.refinement_applied),
      rounds: asNumber(d.refinement_rounds),
      threshold: asNumber(d.threshold),
      sessionId: asString(d.session_id),
      timestamp: asString(d.timestamp),
    };
  }, [lastRunDiagnostics]);

  const lineageSummary = useMemo(() => {
    if (!lineage) return null;
    const versions = Array.isArray(lineage.versions) ? lineage.versions : [];
    const events = Array.isArray(lineage.events) ? lineage.events : [];
    const latestVersion = versions.length > 0 ? versions[versions.length - 1] as Record<string, unknown> : null;
    const latestEvent = events.length > 0 ? events[events.length - 1] as Record<string, unknown> : null;

    return {
      totalVersions: versions.length,
      totalEvents: events.length,
      latestVersionNumber:
        latestVersion && typeof latestVersion.version === 'number' ? latestVersion.version : null,
      latestVersionName:
        latestVersion && typeof latestVersion.name === 'string' ? latestVersion.name : 'n/a',
      latestEventType:
        latestEvent && typeof latestEvent.event_type === 'string' ? latestEvent.event_type : 'n/a',
      latestEventTimestamp:
        latestEvent && typeof latestEvent.timestamp === 'string' ? latestEvent.timestamp : 'n/a',
    };
  }, [lineage]);

  const qualityBadge = useMemo(() => {
    if (!diagnosticsSummary) return null;
    const score = diagnosticsSummary.score;
    const band = diagnosticsSummary.confidenceBand;

    if (band === 'high' || (score !== null && score >= 0.82)) {
      return { label: 'High', className: 'bg-emerald-100 text-emerald-800 border-emerald-200' };
    }
    if (band === 'medium' || (score !== null && score >= 0.65)) {
      return { label: 'Medium', className: 'bg-amber-100 text-amber-800 border-amber-200' };
    }
    if (score !== null) {
      return { label: 'Low', className: 'bg-rose-100 text-rose-800 border-rose-200' };
    }
    return { label: 'N/A', className: 'bg-slate-100 text-slate-700 border-slate-200' };
  }, [diagnosticsSummary]);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [statusData, agentsData] = await Promise.all([
        api.getDynamicAgentsStatus(),
        api.listDynamicAgents(),
      ]);
      setStatus(statusData);
      setAgents(agentsData);
      if (!selectedAgentId && agentsData.length > 0) {
        setSelectedAgentId(agentsData[0].agent_id);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load dynamic agent registry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleEnsureAgent = async () => {
    if (!task.trim()) return;
    setEnsureLoading(true);
    setError('');
    setEnsureResult(null);
    try {
      let context: Record<string, unknown> | undefined;
      if (contextJson.trim()) {
        context = JSON.parse(contextJson);
      }

      const result = await api.ensureDynamicAgent({
        task: task.trim(),
        context,
        allow_create: true,
      });

      setEnsureResult(result);
      await load();

      if (result.agent) {
        setSelectedAgentId(result.agent.agent_id);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to ensure dynamic agent.');
    } finally {
      setEnsureLoading(false);
    }
  };

  const handleRunAgent = async () => {
    if (!selectedAgentId || !prompt.trim()) return;
    setRunLoading(true);
    setError('');
    setRunResult(null);
    try {
      const result = await api.runDynamicAgent({
        agent_id: selectedAgentId,
        prompt: prompt.trim(),
        session_id: sessionId.trim() || undefined,
        task: task.trim() || undefined,
        auto_refine: autoRefine,
        min_score: minScore,
        max_refinement_rounds: maxRefinementRounds,
      });
      setRunResult(result);
      setSessionId(result.session_id);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to run dynamic agent.');
    } finally {
      setRunLoading(false);
    }
  };

  const handleReloadRegistry = async () => {
    setOpsLoading(true);
    setError('');
    try {
      const reload = await api.reloadDynamicAgents();
      await load();
      setLastRunDiagnostics(reload.metrics);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to reload persistent registry.');
    } finally {
      setOpsLoading(false);
    }
  };

  const handleLoadLastRunDiagnostics = async () => {
    setOpsLoading(true);
    setError('');
    try {
      const diag = await api.getDynamicAgentsLastRun(selectedAgentId || undefined);
      setLastRunDiagnostics(diag);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load run diagnostics.');
    } finally {
      setOpsLoading(false);
    }
  };

  const handleLoadLineage = async () => {
    if (!selectedAgentId) return;
    setOpsLoading(true);
    setError('');
    try {
      const lineageResult = await api.getDynamicAgentLineage(selectedAgentId);
      setLineage(lineageResult as unknown as Record<string, unknown>);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load agent lineage.');
    } finally {
      setOpsLoading(false);
    }
  };

  return (
    <div className="chat-container" style={{ overflowY: 'auto', display: 'block' }}>
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        <div className="rounded-2xl border border-cyan-200 bg-gradient-to-r from-cyan-50 to-teal-50 p-5">
          <div className="flex items-center gap-3 mb-2">
            <Sparkles className="w-5 h-5 text-cyan-700" />
            <h2 className="text-xl font-bold text-slate-900">Dynamic Agent Studio</h2>
          </div>
          <p className="text-sm text-slate-700">
            Meta-agent workflow: if no existing agent can do a task, the system creates a new specialist agent on the fly,
            registers it, and runs it in-session.
          </p>
          {status && (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-700">
                Registry: {status.available ? 'available' : 'unavailable'}
              </span>
              <span className="px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-700">
                Copilot Provider: {status.provider_available ? 'enabled' : 'fallback mode'}
              </span>
              {status.metrics && (
                <span className="px-2 py-1 rounded-full bg-white border border-slate-200 text-slate-700">
                  Restored agents: {String((status.metrics as Record<string, unknown>).startup_restored_agents ?? 0)}
                </span>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-1 rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                <Bot className="w-4 h-4" /> Agent Registry
              </h3>
              <button
                className="text-xs px-2 py-1 rounded-lg border border-slate-200 hover:bg-slate-50"
                onClick={load}
                disabled={loading}
              >
                <span className="inline-flex items-center gap-1">
                  <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
                </span>
              </button>
            </div>

            <div className="mb-3 grid grid-cols-1 gap-2">
              <button
                type="button"
                className="text-xs px-2 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-60"
                onClick={handleReloadRegistry}
                disabled={opsLoading}
              >
                {opsLoading ? 'Working...' : 'Reload From Persistence'}
              </button>
              <button
                type="button"
                className="text-xs px-2 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-60"
                onClick={handleLoadLastRunDiagnostics}
                disabled={opsLoading}
              >
                {opsLoading ? 'Working...' : 'Load Last-Run Diagnostics'}
              </button>
              <button
                type="button"
                className="text-xs px-2 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-60"
                onClick={handleLoadLineage}
                disabled={opsLoading || !selectedAgentId}
              >
                {opsLoading ? 'Working...' : 'Load Selected Agent Lineage'}
              </button>
            </div>

            <div className="space-y-2 max-h-[440px] overflow-y-auto pr-1">
              {agents.map((agent) => (
                <button
                  key={agent.agent_id}
                  type="button"
                  onClick={() => setSelectedAgentId(agent.agent_id)}
                  className={`w-full text-left rounded-xl border px-3 py-2 transition-colors ${
                    selectedAgentId === agent.agent_id
                      ? 'border-cyan-400 bg-cyan-50'
                      : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  <p className="font-medium text-sm text-slate-900">{agent.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{agent.agent_id}</p>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 4).map((cap) => (
                      <span key={cap} className="px-1.5 py-0.5 rounded bg-slate-100 text-[10px] text-slate-600">
                        {cap}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>

            {lastRunDiagnostics && (
              <div className="mt-3 rounded-xl border border-indigo-200 bg-indigo-50 p-2">
                <p className="text-[11px] font-semibold text-indigo-900 mb-2">Diagnostics Snapshot</p>
                {diagnosticsSummary ? (
                  <div className="grid grid-cols-2 gap-2 text-[10px] text-indigo-900">
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Agent</strong>
                      <div>{diagnosticsSummary.agentName}</div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Version</strong>
                      <div>{diagnosticsSummary.agentVersion ?? 'n/a'}</div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Score</strong>
                      <div>
                        {diagnosticsSummary.score !== null
                          ? diagnosticsSummary.score.toFixed(2)
                          : 'n/a'}
                      </div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Quality</strong>
                      <div>
                        {qualityBadge ? (
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded border ${qualityBadge.className}`}>
                            {qualityBadge.label}
                          </span>
                        ) : (
                          'n/a'
                        )}
                      </div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Threshold</strong>
                      <div>
                        {diagnosticsSummary.threshold !== null
                          ? diagnosticsSummary.threshold.toFixed(2)
                          : 'n/a'}
                      </div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1 col-span-2">
                      <strong>Evaluator</strong>
                      <div>{diagnosticsSummary.evaluatorMode}</div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Refined</strong>
                      <div>
                        {diagnosticsSummary.refined === null
                          ? 'n/a'
                          : diagnosticsSummary.refined
                            ? 'yes'
                            : 'no'}
                      </div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1">
                      <strong>Rounds</strong>
                      <div>{diagnosticsSummary.rounds ?? 'n/a'}</div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1 col-span-2">
                      <strong>Session</strong>
                      <div className="break-all">{diagnosticsSummary.sessionId}</div>
                    </div>
                    <div className="rounded border border-indigo-200 bg-white px-2 py-1 col-span-2">
                      <strong>Timestamp</strong>
                      <div>{diagnosticsSummary.timestamp}</div>
                    </div>
                  </div>
                ) : null}
                <button
                  type="button"
                  className="mt-2 text-[10px] px-2 py-1 rounded border border-indigo-300 bg-white hover:bg-indigo-100"
                  onClick={() => setShowRawDiagnostics((v) => !v)}
                >
                  {showRawDiagnostics ? 'Hide Raw JSON' : 'Show Raw JSON'}
                </button>
                {showRawDiagnostics && (
                  <pre className="mt-2 text-[10px] text-indigo-900 whitespace-pre-wrap max-h-36 overflow-y-auto">
                    {JSON.stringify(lastRunDiagnostics, null, 2)}
                  </pre>
                )}
              </div>
            )}

            {lineage && (
              <div className="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 p-2">
                <p className="text-[11px] font-semibold text-emerald-900 mb-2">Lineage</p>
                {lineageSummary ? (
                  <div className="grid grid-cols-2 gap-2 text-[10px] text-emerald-900">
                    <div className="rounded border border-emerald-200 bg-white px-2 py-1">
                      <strong>Total versions</strong>
                      <div>{lineageSummary.totalVersions}</div>
                    </div>
                    <div className="rounded border border-emerald-200 bg-white px-2 py-1">
                      <strong>Total events</strong>
                      <div>{lineageSummary.totalEvents}</div>
                    </div>
                    <div className="rounded border border-emerald-200 bg-white px-2 py-1 col-span-2">
                      <strong>Latest version</strong>
                      <div>
                        {lineageSummary.latestVersionNumber ?? 'n/a'} - {lineageSummary.latestVersionName}
                      </div>
                    </div>
                    <div className="rounded border border-emerald-200 bg-white px-2 py-1 col-span-2">
                      <strong>Latest event</strong>
                      <div>{lineageSummary.latestEventType}</div>
                      <div>{lineageSummary.latestEventTimestamp}</div>
                    </div>
                  </div>
                ) : null}
                <button
                  type="button"
                  className="mt-2 text-[10px] px-2 py-1 rounded border border-emerald-300 bg-white hover:bg-emerald-100"
                  onClick={() => setShowRawLineage((v) => !v)}
                >
                  {showRawLineage ? 'Hide Raw JSON' : 'Show Raw JSON'}
                </button>
                {showRawLineage && (
                  <pre className="mt-2 text-[10px] text-emerald-900 whitespace-pre-wrap max-h-36 overflow-y-auto">
                    {JSON.stringify(lineage, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>

          <div className="xl:col-span-2 space-y-5">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2 mb-3">
                <PlusCircle className="w-4 h-4" /> Ensure Agent For Task
              </h3>
              <div className="space-y-3">
                <textarea
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400"
                  placeholder="Describe the missing capability task..."
                  rows={3}
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                />
                <textarea
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-mono text-slate-900 placeholder-slate-400"
                  placeholder="Optional JSON context"
                  rows={4}
                  value={contextJson}
                  onChange={(e) => setContextJson(e.target.value)}
                />
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-xl bg-cyan-600 text-white px-4 py-2 text-sm font-semibold hover:bg-cyan-700 disabled:opacity-60"
                  onClick={handleEnsureAgent}
                  disabled={ensureLoading || !task.trim()}
                >
                  {ensureLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />}
                  Ensure / Generate Agent
                </button>
              </div>

              {ensureResult && (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm">
                  <p className="font-medium text-emerald-800">
                    Status: {ensureResult.status}
                  </p>
                  <p className="text-emerald-700 mt-1">{ensureResult.reason}</p>
                  {ensureResult.agent && (
                    <p className="text-emerald-800 mt-2">
                      Active agent: <strong>{ensureResult.agent.name}</strong> ({ensureResult.agent.agent_id})
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <h3 className="font-semibold text-slate-900 flex items-center gap-2 mb-3">
                <PlayCircle className="w-4 h-4" /> Run Selected Agent
              </h3>

              {selectedAgent ? (
                <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-sm font-medium text-slate-900">{selectedAgent.name}</p>
                  <p className="text-xs text-slate-600 mt-1">Model: {selectedAgent.model}</p>
                </div>
              ) : (
                <p className="text-sm text-slate-600 mb-3">Select an agent from the registry first.</p>
              )}

              <div className="space-y-3">
                <input
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400"
                  placeholder="Session ID (optional, for memory continuity)"
                  value={sessionId}
                  onChange={(e) => setSessionId(e.target.value)}
                />
                <textarea
                  className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400"
                  placeholder="Prompt for the selected agent"
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                />
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      checked={autoRefine}
                      onChange={(e) => setAutoRefine(e.target.checked)}
                    />
                    Auto-refine if score is low
                  </label>
                  <label className="text-sm text-slate-700">
                    Min score
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.01}
                      value={minScore}
                      onChange={(e) => setMinScore(Number(e.target.value || 0.72))}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2 py-1 text-slate-900"
                    />
                  </label>
                  <label className="text-sm text-slate-700">
                    Max refine rounds
                    <input
                      type="number"
                      min={0}
                      max={3}
                      step={1}
                      value={maxRefinementRounds}
                      onChange={(e) => setMaxRefinementRounds(Number(e.target.value || 1))}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-2 py-1 text-slate-900"
                    />
                  </label>
                </div>
                <button
                  type="button"
                  className="inline-flex items-center gap-2 rounded-xl bg-teal-600 text-white px-4 py-2 text-sm font-semibold hover:bg-teal-700 disabled:opacity-60"
                  onClick={handleRunAgent}
                  disabled={runLoading || !selectedAgentId || !prompt.trim()}
                >
                  {runLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                  Run Agent
                </button>
              </div>

              {runResult && (
                <div className="mt-4 rounded-xl border border-cyan-200 bg-cyan-50 p-3">
                  <div className="mb-2 flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-1 rounded bg-white border border-cyan-200 text-cyan-800">
                      Version: {runResult.agent_version ?? 1}
                    </span>
                    <span className="px-2 py-1 rounded bg-white border border-cyan-200 text-cyan-800">
                      Refined: {runResult.refinement_applied ? 'yes' : 'no'}
                    </span>
                    <span className="px-2 py-1 rounded bg-white border border-cyan-200 text-cyan-800">
                      Rounds: {runResult.refinement_rounds ?? 0}
                    </span>
                    {runResult.evaluation?.score !== undefined && (
                      <span className="px-2 py-1 rounded bg-white border border-cyan-200 text-cyan-800">
                        Score: {Number(runResult.evaluation.score).toFixed(2)}
                      </span>
                    )}
                  </div>
                  {runResult.evaluation?.issues && runResult.evaluation.issues.length > 0 && (
                    <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800">
                      <strong>Issues:</strong> {runResult.evaluation.issues.join(' | ')}
                    </div>
                  )}
                  <p className="text-xs text-cyan-800 mb-2">Session: {runResult.session_id}</p>
                  <pre className="text-sm text-slate-900 whitespace-pre-wrap leading-relaxed">
                    {runResult.answer}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
