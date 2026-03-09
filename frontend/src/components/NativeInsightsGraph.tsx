import { useEffect, useState } from 'react';
import type { CrossSheetEdge, SheetCorrelationHint } from '../types';

interface NativeInsightsGraphProps {
	edges: CrossSheetEdge[];
	sheetHints: SheetCorrelationHint[];
	focusSheetIds?: string[];
	highlightSignals?: string[];
}

interface GraphNode {
	id: string;
	shortLabel: string;
	pages: string;
	degree: number;
	x: number;
	y: number;
}

type GraphSelection =
	| { kind: 'node'; nodeId: string }
	| { kind: 'edge'; edgeKey: string }
	| null;

function truncateLabel(value: string, maxLength: number): string {
	return value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}…`;
}

function buildGraphNodes(edges: CrossSheetEdge[], sheetHints: SheetCorrelationHint[]): GraphNode[] {
	const nodeIds = new Set<string>();
	const hintsById = new Map(sheetHints.map((hint) => [hint.sheet_id, hint]));
	const degreeById = new Map<string, number>();

	for (const hint of sheetHints) {
		nodeIds.add(hint.sheet_id);
	}

	for (const edge of edges) {
		nodeIds.add(edge.from_sheet_id);
		nodeIds.add(edge.to_sheet_id);
		degreeById.set(edge.from_sheet_id, (degreeById.get(edge.from_sheet_id) ?? 0) + 1);
		degreeById.set(edge.to_sheet_id, (degreeById.get(edge.to_sheet_id) ?? 0) + 1);
	}

	const ids = Array.from(nodeIds).sort();
	const centerX = 180;
	const centerY = 125;
	const radius = ids.length <= 2 ? 70 : ids.length <= 4 ? 86 : 96;

	return ids.map((id, index) => {
		const angle = ids.length === 1 ? 0 : (-Math.PI / 2) + ((Math.PI * 2 * index) / ids.length);
		const hint = hintsById.get(id);
		const pageSpan = hint?.page_span ?? [];
		const pages = pageSpan.length > 0 ? pageSpan.map((page) => page + 1).join(', ') : 'n/a';
		return {
			id,
			shortLabel: truncateLabel(id, 14),
			pages,
			degree: degreeById.get(id) ?? 0,
			x: ids.length === 1 ? centerX : centerX + Math.cos(angle) * radius,
			y: ids.length === 1 ? centerY : centerY + Math.sin(angle) * radius,
		};
	});
}

function strokeWidthForWeight(weight: number): number {
	if (weight >= 10) {
		return 4;
	}
	if (weight >= 6) {
		return 3;
	}
	if (weight >= 3) {
		return 2.25;
	}
	return 1.5;
}

function edgeTone(weight: number): string {
	if (weight >= 10) {
		return '#1d4ed8';
	}
	if (weight >= 6) {
		return '#2563eb';
	}
	return '#93c5fd';
}

function edgeKey(edge: CrossSheetEdge): string {
	return `${edge.from_sheet_id}::${edge.to_sheet_id}`;
}

function detailList(values: string[] | undefined, fallback: string): string[] {
	if (!values || values.length === 0) {
		return [fallback];
	}
	return values;
}

function normalizeSet(values: string[] | undefined): Set<string> {
	return new Set((values ?? []).map((value) => value.toLowerCase()));
}

function edgeMatchesSignals(edge: CrossSheetEdge, signalSet: Set<string>): boolean {
	if (signalSet.size === 0) {
		return false;
	}
	const edgeSignals = [
		...(edge.shared_references ?? []),
		...(edge.shared_tags ?? []),
		...(edge.shared_components ?? []),
		...(edge.shared_standards ?? []),
	].map((value) => value.toLowerCase());
	return edgeSignals.some((signal) => signalSet.has(signal));
}

export function NativeInsightsGraph({ edges, sheetHints, focusSheetIds = [], highlightSignals = [] }: NativeInsightsGraphProps) {
	const nodes = buildGraphNodes(edges, sheetHints);
	const nodeMap = new Map(nodes.map((node) => [node.id, node]));
	const hintMap = new Map(sheetHints.map((hint) => [hint.sheet_id, hint]));
	const strongestEdges = [...edges].sort((left, right) => right.weight - left.weight).slice(0, 4);
	const [selection, setSelection] = useState<GraphSelection>(null);
	const focusSheetSet = new Set(focusSheetIds);
	const highlightSignalSet = normalizeSet(highlightSignals);

	useEffect(() => {
		if (edges.length > 0) {
			setSelection({ kind: 'edge', edgeKey: edgeKey(edges[0]) });
			return;
		}
		if (nodes.length > 0) {
			setSelection({ kind: 'node', nodeId: nodes[0].id });
			return;
		}
		setSelection(null);
	}, [edges, nodes]);

	const selectedEdge = selection?.kind === 'edge'
		? edges.find((edge) => edgeKey(edge) === selection.edgeKey) ?? null
		: null;
	const selectedNodeId = selection?.kind === 'node'
		? selection.nodeId
		: selectedEdge?.from_sheet_id ?? null;
	const selectedNode = selectedNodeId ? nodes.find((node) => node.id === selectedNodeId) ?? null : null;
	const selectedHint = selectedNode ? hintMap.get(selectedNode.id) : undefined;
	const connectedEdges = selectedNode
		? edges.filter((edge) => edge.from_sheet_id === selectedNode.id || edge.to_sheet_id === selectedNode.id)
		: [];
	const hasExternalFocus = focusSheetSet.size > 0 || highlightSignalSet.size > 0;

	if (nodes.length === 0) {
		return (
			<div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
				No sheet graph is available for this upload.
			</div>
		);
	}

	return (
		<div className="space-y-4">
			<div className="rounded-2xl border border-slate-200 bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.12),_transparent_52%),linear-gradient(180deg,_#ffffff_0%,_#eff6ff_100%)] p-3">
				<svg viewBox="0 0 360 250" className="w-full h-auto" role="img" aria-label="Cross-sheet graph visualization">
					<defs>
						<filter id="nodeShadow" x="-20%" y="-20%" width="140%" height="140%">
							<feDropShadow dx="0" dy="4" stdDeviation="5" floodOpacity="0.12" />
						</filter>
					</defs>

					{edges.map((edge) => {
						const fromNode = nodeMap.get(edge.from_sheet_id);
						const toNode = nodeMap.get(edge.to_sheet_id);
						if (!fromNode || !toNode) {
							return null;
						}

						const isSelected = selection?.kind === 'edge' && selection.edgeKey === edgeKey(edge);
						const touchesSelectedNode = selectedNodeId === edge.from_sheet_id || selectedNodeId === edge.to_sheet_id;
						const matchesSignalFocus = edgeMatchesSignals(edge, highlightSignalSet);
						const matchesSheetFocus = focusSheetSet.has(edge.from_sheet_id) || focusSheetSet.has(edge.to_sheet_id);
						const isFocusMatch = matchesSignalFocus || matchesSheetFocus;
						const midX = (fromNode.x + toNode.x) / 2;
						const midY = (fromNode.y + toNode.y) / 2;
						return (
							<g
								key={`${edge.from_sheet_id}-${edge.to_sheet_id}`}
								onClick={() => setSelection({ kind: 'edge', edgeKey: edgeKey(edge) })}
								className="cursor-pointer"
							>
								<line
									x1={fromNode.x}
									y1={fromNode.y}
									x2={toNode.x}
									y2={toNode.y}
									stroke={isSelected ? '#0f172a' : isFocusMatch ? '#dc2626' : edgeTone(edge.weight)}
									strokeWidth={isSelected ? strokeWidthForWeight(edge.weight) + 1.5 : strokeWidthForWeight(edge.weight)}
									strokeLinecap="round"
									opacity={isSelected || touchesSelectedNode || isFocusMatch ? 1 : hasExternalFocus ? 0.2 : 0.85}
								/>
								<g>
									<rect
										x={midX - 14}
										y={midY - 10}
										width="28"
										height="20"
										rx="10"
										fill={isSelected ? '#dbeafe' : '#ffffff'}
										stroke={isSelected ? '#2563eb' : '#cbd5e1'}
									/>
									<text
										x={midX}
										y={midY + 4}
										textAnchor="middle"
										fontSize="10"
										fontWeight="700"
										fill="#0f172a"
									>
										{edge.weight}
									</text>
								</g>
							</g>
						);
					})}

					{nodes.map((node) => {
						const radius = 24 + Math.min(node.degree, 4) * 3;
						const isSelected = selectedNodeId === node.id;
						const isFocusMatch = focusSheetSet.has(node.id)
							|| edges.some((edge) => (edge.from_sheet_id === node.id || edge.to_sheet_id === node.id) && edgeMatchesSignals(edge, highlightSignalSet));
						return (
							<g
								key={node.id}
								filter="url(#nodeShadow)"
								onClick={() => setSelection({ kind: 'node', nodeId: node.id })}
								className="cursor-pointer"
							>
								<circle cx={node.x} cy={node.y} r={radius} fill="#ffffff" stroke={isSelected ? '#0f172a' : isFocusMatch ? '#dc2626' : '#2563eb'} strokeWidth={isSelected ? '3.5' : '2.5'} opacity={isFocusMatch || !hasExternalFocus ? 1 : 0.45} />
								<circle cx={node.x} cy={node.y} r={radius - 6} fill={isSelected ? '#bfdbfe' : isFocusMatch ? '#fee2e2' : '#dbeafe'} opacity={isFocusMatch || !hasExternalFocus ? 1 : 0.45} />
								<text x={node.x} y={node.y - 2} textAnchor="middle" fontSize="10" fontWeight="700" fill="#0f172a">
									{node.shortLabel}
								</text>
								<text x={node.x} y={node.y + 12} textAnchor="middle" fontSize="9" fill="#475569">
									p. {truncateLabel(node.pages, 10)}
								</text>
							</g>
						);
					})}
				</svg>
			</div>

			<div className="rounded-xl border border-slate-200 bg-white px-4 py-4">
				{selectedEdge ? (
					<div className="space-y-3">
						<div className="flex items-center justify-between gap-3">
							<div>
								<p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Selected link</p>
								<h5 className="text-base font-semibold text-slate-900">
									{selectedEdge.from_sheet_id} to {selectedEdge.to_sheet_id}
								</h5>
							</div>
							<span className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-800">
								Weight {selectedEdge.weight}
							</span>
						</div>
						<div className="grid gap-3 md:grid-cols-2">
							<div>
								<p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Shared references</p>
								<div className="flex flex-wrap gap-2">
									{detailList(selectedEdge.shared_references, 'No shared references').map((value) => (
										<span key={`ref-${value}`} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
											{value}
										</span>
									))}
								</div>
							</div>
							<div>
								<p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Shared components and tags</p>
								<div className="flex flex-wrap gap-2">
									{detailList([
										...(selectedEdge.shared_components ?? []),
										...(selectedEdge.shared_tags ?? []),
									], 'No shared components').map((value) => (
										<span key={`sig-${value}`} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
											{value}
										</span>
									))}
								</div>
							</div>
						</div>
					</div>
				) : selectedNode ? (
					<div className="space-y-3">
						<div className="flex items-center justify-between gap-3">
							<div>
								<p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Selected sheet</p>
								<h5 className="text-base font-semibold text-slate-900">{selectedNode.id}</h5>
							</div>
							<span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
								Pages {selectedNode.pages}
							</span>
						</div>
						<div className="grid gap-3 md:grid-cols-2">
							<div>
								<p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">References and standards</p>
								<div className="flex flex-wrap gap-2">
									{detailList([
										...(selectedHint?.top_references ?? []),
										...(selectedHint?.top_standards ?? []),
									], 'No highlighted references').map((value) => (
										<span key={`node-ref-${value}`} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
											{value}
										</span>
									))}
								</div>
							</div>
							<div>
								<p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Components and tags</p>
								<div className="flex flex-wrap gap-2">
									{detailList([
										...(selectedHint?.top_components ?? []),
										...(selectedHint?.top_tags ?? []),
									], 'No highlighted components').map((value) => (
										<span key={`node-comp-${value}`} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
											{value}
										</span>
									))}
								</div>
							</div>
						</div>
						<div>
							<p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Connected links</p>
							<div className="space-y-2">
								{connectedEdges.length > 0 ? connectedEdges.slice(0, 4).map((edge) => {
									const otherSheet = edge.from_sheet_id === selectedNode.id ? edge.to_sheet_id : edge.from_sheet_id;
									return (
										<button
											key={`connected-${edgeKey(edge)}`}
											type="button"
											onClick={() => setSelection({ kind: 'edge', edgeKey: edgeKey(edge) })}
											className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-700 hover:border-blue-300 hover:bg-blue-50"
										>
											<span>{otherSheet}</span>
											<span className="text-xs font-semibold text-slate-500">weight {edge.weight}</span>
										</button>
									);
								}) : (
									<p className="text-sm text-slate-400">This sheet has no connected edges.</p>
								)}
							</div>
						</div>
					</div>
				) : null}
			</div>

			<div className="grid gap-3 md:grid-cols-2">
				{strongestEdges.length > 0 ? (
					strongestEdges.map((edge) => {
						const sharedSignals = [
							...(edge.shared_references ?? []),
							...(edge.shared_tags ?? []),
							...(edge.shared_components ?? []),
						].slice(0, 4);
						const isSelected = selection?.kind === 'edge' && selection.edgeKey === edgeKey(edge);
						return (
							<button
								type="button"
								key={`${edge.from_sheet_id}-${edge.to_sheet_id}-card`}
								onClick={() => setSelection({ kind: 'edge', edgeKey: edgeKey(edge) })}
								className={`rounded-xl border bg-white px-4 py-3 text-left transition-colors ${isSelected ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'}`}
							>
								<div className="flex items-center justify-between gap-3 mb-2">
									<p className="text-sm font-semibold text-slate-900">
										{edge.from_sheet_id} to {edge.to_sheet_id}
									</p>
									<span className="rounded-full bg-blue-100 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-blue-800">
										{edge.relationship_strength ?? 'linked'}
									</span>
								</div>
								<p className="text-xs text-slate-500 mb-2">Weight {edge.weight}</p>
								<div className="flex flex-wrap gap-2">
									{sharedSignals.length > 0 ? (
										sharedSignals.map((signal) => (
											<span key={`${edge.from_sheet_id}-${edge.to_sheet_id}-${signal}`} className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
												{signal}
											</span>
										))
									) : (
										<span className="text-xs text-slate-400">No shared signals listed</span>
									)}
								</div>
							</button>
						);
					})
				) : (
					<div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500 md:col-span-2">
						Sheet nodes were found, but no weighted links rose above the graph threshold.
					</div>
				)}
			</div>
		</div>
	);
}
