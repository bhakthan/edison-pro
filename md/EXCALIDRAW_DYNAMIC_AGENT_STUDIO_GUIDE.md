# Excalidraw Diagrams for Dynamic Agent Studio

This guide provides three Excalidraw-compatible scene files for presenting Dynamic Agent Studio to different audiences.

## Files

### Executive audience

1. `md/excalidraw/dynamic-agent-studio-executive-overview.excalidraw`
   - Focus: what just-in-time agents mean in plain business language
   - Message: when a new need appears, the platform creates the right specialist agent at the moment of need

2. `md/excalidraw/dynamic-agent-studio-executive-loop.excalidraw`
   - Focus: self-reflection and self-improvement in plain business language
   - Message: the platform checks its own work, improves itself when needed, and becomes more reusable over time

### Technical audience

3. `md/excalidraw/dynamic-agent-studio-technical-walkthrough.excalidraw`
   - Focus: UI, API, registry, meta-agent, evaluator/refiner, and persistence flow
   - Message: how ensure/run, evaluation, refinement, and persistence work together

## How to open

### In Excalidraw

1. Go to https://excalidraw.com/
2. Click `Open`
3. Select one of the `.excalidraw` files above

## Suggested speaking track

### Executive overview

Use the first two diagrams to explain:

- We no longer wait for every agent to be prebuilt.
- The system creates a specialist only when the business needs one.
- The specialist is checked automatically.
- If the result is weak, the system improves the specialist and tries again.
- The learning is saved so future work is faster and more reliable.

### Technical walkthrough

Use the third diagram to explain:

- `POST /dynamic-agents/ensure` matches or creates an agent
- `POST /dynamic-agents/run` executes the agent with optional auto-refine
- evaluation determines whether refinement is needed
- persistence stores active agents, lineage, and reflection events
- diagnostics and lineage can be inspected from the UI and API

## Note

I could not directly invoke `mcp.excalidraw.com` as an MCP server from this environment, so these were created as Excalidraw-compatible scene files that can be opened directly in Excalidraw.
