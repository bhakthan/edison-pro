# Autonomous Agents Demo Guide

This document explains how to demo EDISON PRO's on-the-fly agent creation flow in Dynamic Agent Studio.

## Purpose

Dynamic Agent Studio supports an autonomous mode where the system:

1. inspects the current registry of available agents,
2. tries to match an existing agent to the requested task,
3. creates a new specialist agent when no suitable agent exists,
4. runs that resolved agent in the same session.

This is the core demo story: the user does not need to manually design an agent first when autonomous mode is enabled.

## Current Live Registry

At the time of writing, the live registry exposes these active agents:

1. `general-analyst`
   Capabilities: `analysis`, `reasoning`, `planning`, `summarization`
2. `data-transformer`
   Capabilities: `tabular`, `csv`, `transform`, `extract`
3. `data-specialist`
   Capabilities: `data`, `compare`, `create`, `breaker`, `result`, `table`

These matter because the registry will reuse an existing agent if the task overlaps strongly enough with an existing capability set.

## Matching Behavior

Dynamic agent matching currently uses capability overlap.

- Existing agent reuse happens only when the task has at least 3 overlapping tokens with an existing agent's name and capabilities.
- If the overlap is lower than that threshold, the registry treats the request as a capability gap and creates a new specialist.

### Good tasks for reuse

These tend to match existing agents:

1. `Analyze this drawing and summarize the findings`
2. `Extract the components and return a CSV`
3. `Compare transformer and breaker data and return a table`

### Good tasks for new-agent creation

These are more likely to trigger on-the-fly specialist creation:

1. `Create a relay coordination review specialist that identifies protection-zone conflicts and nuisance-trip risk.`
2. `Create a P&ID standards compliance specialist that finds ISA/IEC tag inconsistencies and summarizes gaps.`
3. `Create a revision impact specialist for electrical drawings that ranks changes by downstream construction risk.`
4. `Create a valve sequencing specialist that infers startup dependencies and unsafe sequence risks from a P&ID.`
5. `Create a submittal QA specialist that validates panel schedules against feeder annotations and flags mismatches.`

## What Counts As Input

For the autonomous-creation demo, the most important input is the task description.

Agent creation itself does not require a file upload.

Uploads are useful to make the run more realistic, but the create-agent decision is primarily driven by:

1. the task text,
2. the optional JSON context,
3. the capabilities already present in the registry.

## Recommended Demo Inputs

### Demo A: Electrical Protection Specialist

Task:

```text
Create a relay coordination review specialist that identifies protection-zone conflicts and explains likely nuisance-trip risks.
```

Context JSON:

```json
{
  "domain": "electrical",
  "document_type": "single-line diagram",
  "goal": "specialist creation demo",
  "priority": "high"
}
```

Optional file to upload first:

- substation single-line diagram
- switchgear protection drawing
- feeder coordination one-line

Why this works:

- It does not strongly overlap with `analysis`, `csv`, `extract`, or `compare breaker table`.
- It sounds like a real engineering niche where a specialist is justified.

### Demo B: P&ID Compliance Specialist

Task:

```text
Create a P&ID standards compliance specialist that finds ISA and IEC tag inconsistencies and produces a compliance gap summary.
```

Context JSON:

```json
{
  "domain": "pid",
  "document_type": "process and instrumentation diagram",
  "goal": "compliance review",
  "priority": "high"
}
```

Optional file to upload first:

- plant P&ID sheet
- instrumentation loop diagram
- tagged process flow sheet

Why this works:

- It is clearly domain-specific.
- It avoids the existing generic analysis and transformation capabilities.

### Demo C: Revision Impact Specialist

Task:

```text
Create a revision impact specialist for electrical drawings that ranks changes by downstream construction and commissioning risk.
```

Context JSON:

```json
{
  "domain": "electrical",
  "document_type": "drawing revision set",
  "goal": "revision risk ranking",
  "priority": "high"
}
```

Optional file to upload first:

- revision A drawing image
- revision B drawing image
- change-marked electrical plan

Why this works:

- It is specialized enough to avoid accidental reuse.
- It showcases a more executive-facing use case than raw extraction.

## Best Demo Flow In The UI

### Minimal autonomous demo

Use this when you want to prove the concept quickly without relying on uploaded data.

1. Open Dynamic Agent Studio.
2. Turn `Autonomous mode` on.
3. Paste one of the specialist-creation tasks above into the task area.
4. Paste the matching JSON context.
5. Enter a concrete execution prompt.
6. Click `Resolve Agent and Run`.

Expected outcome:

1. the system checks current registry capabilities,
2. no existing agent is a strong enough match,
3. a new specialist is created,
4. the new agent is selected and run in-session,
5. the registry shows the newly created agent afterward.

### Full showcase demo with upload

Use this when you want a stronger product story tying together upload, analysis, and autonomous agents.

1. Upload a PDF or diagram image in the Upload tab.
2. Move to Dynamic Agent Studio.
3. Keep `Autonomous mode` on.
4. Use a task such as:

```text
Create a relay coordination review specialist for this uploaded substation drawing and identify likely protection conflicts.
```

5. Use context such as:

```json
{
  "domain": "electrical",
  "document": "substation_single_line.pdf",
  "artifact_source": "uploaded drawing",
  "goal": "autonomous specialist demo"
}
```

6. Enter a run prompt such as:

```text
Review the uploaded drawing, identify likely protection-zone conflicts, and summarize the top nuisance-trip risks with mitigation ideas.
```

Expected outcome:

- the user sees that a normal engineering artifact can be uploaded first,
- the system then creates a specialist only when needed,
- the task is executed without manual agent authoring.

## Recommended Prompt Set For Live Demo

If time is short, use these exact prompts.

### Prompt 1: Force specialist creation

Task:

```text
Create a relay coordination review specialist that identifies protection-zone conflicts and explains likely nuisance-trip risks.
```

Run prompt:

```text
Review this task as a relay coordination specialist. Produce a concise engineering summary, the likely conflict areas, and recommended next validation checks.
```

### Prompt 2: Show reuse instead of creation

Task:

```text
Extract the engineering components and return a CSV-ready table.
```

Run prompt:

```text
Return the component data in a compact tabular structure with fields that can be exported to CSV.
```

Expected outcome:

- this should typically reuse `data-transformer` instead of creating a new agent.

### Prompt 3: Show another autonomous creation path

Task:

```text
Create a P&ID standards compliance specialist that finds ISA and IEC tag inconsistencies and produces a compliance gap summary.
```

Run prompt:

```text
Assess the request as a P&ID compliance specialist and summarize the highest-risk tag consistency gaps, assumptions, and follow-up review steps.
```

## What To Say During The Demo

Suggested talk track:

1. `These are the agents already in the registry.`
2. `If my task overlaps with one of them, the system reuses it.`
3. `If the task represents a real capability gap, autonomous mode creates a new specialist on the fly.`
4. `The user does not have to manually author that agent first.`
5. `The new specialist is then available in the registry for future reuse and refinement.`

## What To Avoid In The Demo

Avoid these if your goal is specifically to showcase agent creation:

1. very generic prompts like `analyze this drawing`
2. prompts that say `extract`, `csv`, or `transform` without anything specialized
3. prompts that closely resemble `compare breaker data and return a table`

Those are more likely to match existing agents and reduce the impact of the demo.

## Success Criteria

The demo is successful if the audience sees all of the following:

1. there is a finite starting registry,
2. the task is checked against what already exists,
3. a new specialist appears only when needed,
4. the newly created specialist is then used immediately,
5. the created agent remains available for later inspection and lineage review.