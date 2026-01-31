# Visual Diagrams - Memory Atlas Flow Charts

This page contains ASCII diagrams showing how the Memory Atlas system works.

## 🎯 Complete System Flow

### Overview Architecture

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                     EDISON PRO - MEMORY ATLAS SYSTEM                  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

                             ┌─────────────────┐
                             │   USER INPUT    │
                             │  • Diagram image│
                             │  • Text query   │
                             └────────┬────────┘
                                      │
                                      ↓
         ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ┃         FLICKERING COGNITIVE SYSTEM                ┃
         ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ↓                 ↓                 ↓
         ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
         │  VISION AGENT    │ │ SYMBOL AGENT │ │  CONTEXT AGENT   │
         │  • Extract       │ │ • Recognize  │ │  • Understand    │
         │    features      │ │   symbols    │ │    relationships │
         │  • Create        │ │ • Classify   │ │  • Map structure │
         │    embedding     │ │   components │ │  • Infer purpose │
         └──────────────────┘ └──────────────┘ └──────────────────┘
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      │
                                      ↓
         ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ┃              MEMORY ATLAS AGENT                    ┃
         ┃  • Search for similar patterns                     ┃
         ┃  • Retrieve relevant knowledge                     ┃
         ┃  • Store new learnings                             ┃
         ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                          ↓                       ↓
         ┌──────────────────────────┐  ┌──────────────────────────┐
         │   AZURE AI SEARCH        │  │   LOCAL JSON STORAGE     │
         │   (Cloud Vector DB)      │  │   (Backup)               │
         │                          │  │                          │
         │  • 512-dim vectors       │  │  • Pattern files         │
         │  • Fast similarity       │  │  • Offline access        │
         │  • 30ms retrieval        │  │  • 50ms retrieval        │
         │  • Scalable storage      │  │  • Privacy preserved     │
         └──────────────────────────┘  └──────────────────────────┘
                          │                       │
                          └───────────┬───────────┘
                                      │
                                      ↓
         ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ┃         CONFIDENCE EVALUATOR                       ┃
         ┃  • Calculate confidence score                      ┃
         ┃  • Assess pattern reliability                      ┃
         ┃  • Determine analysis path                         ┃
         ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                                      ↓
         ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
         ┃         INTERPRETATION AGENT                       ┃
         ┃  • Synthesize findings                             ┃
         ┃  • Generate answer                                 ┃
         ┃  • Provide confidence score                        ┃
         ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                      │
                                      ↓
                             ┌─────────────────┐
                             │   USER OUTPUT   │
                             │  • Analysis     │
                             │  • Components   │
                             │  • Confidence   │
                             └─────────────────┘
```

---

## 🔄 Decision Tree: Pattern Match or Full Analysis

```
                    ┌──────────────────┐
                    │  NEW DIAGRAM     │
                    │  ARRIVES         │
                    └────────┬─────────┘
                             │
                             ↓
                    ┌──────────────────┐
                    │ CREATE EMBEDDING │
                    │ (512 numbers)    │
                    └────────┬─────────┘
                             │
                             ↓
                    ┌──────────────────┐
                    │ SEARCH MEMORY    │
                    │ ATLAS            │
                    └────────┬─────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
      Similarity > 70%          Similarity < 70%
                │                         │
                ↓                         ↓
    ┌─────────────────────┐   ┌─────────────────────┐
    │   PATTERN FOUND!    │   │   NO MATCH FOUND    │
    │   ✓ High similarity │   │   ✗ New territory   │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                          │
               ↓                          ↓
    ┌─────────────────────┐   ┌─────────────────────┐
    │   FAST PATH         │   │   SLOW PATH         │
    │   ⚡ 30ms search    │   │   🐌 Full analysis  │
    │   ⚡ 150ms analysis │   │   🐌 500ms total    │
    │   Total: ~200ms     │   │                     │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                          │
               ↓                          ↓
    ┌─────────────────────┐   ┌─────────────────────┐
    │ GUIDED ANALYSIS     │   │ DEEP ANALYSIS       │
    │ • Use past          │   │ • All agents        │
    │   knowledge         │   │ • No guidance       │
    │ • Focus on known    │   │ • Explore fully     │
    │   components        │   │                     │
    │ • High confidence   │   │ • Lower confidence  │
    │   (70-90%)          │   │   (30-50%)          │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                          │
               ↓                          ↓
    ┌─────────────────────┐   ┌─────────────────────┐
    │ UPDATE PATTERN      │   │ CREATE NEW PATTERN  │
    │ • Increment use     │   │ • Version v1        │
    │ • Refine accuracy   │   │ • Store embedding   │
    │ • Track stats       │   │ • Save components   │
    │ • Next version      │   │ • Set metrics       │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                          │
               └────────────┬─────────────┘
                            │
                            ↓
                    ┌──────────────────┐
                    │ RETURN ANSWER    │
                    │ TO USER          │
                    └──────────────────┘
```

---

## 📊 Embedding Similarity Visualization

```
                    VECTOR SPACE (simplified to 2D)

        Dimension 2
            ↑
         1.0│
            │                               ● Civil Blueprint
            │                            
         0.5│     ● Mechanical Part
            │      
         0.0│─────────────────────────────────────────→ Dimension 1
            │                                          0.0  0.5  1.0
        -0.5│          ⭐ NEW DIAGRAM
            │        (to be matched)
            │               
        -1.0│     ● Electrical Power         ● P&ID Process
            │       (89% similar!)
            │     ● Electrical Control
            │       (85% similar)


High Similarity Zone (>80%):
┌─────────────────────────────────────┐
│  ● Electrical Power    ⭐ NEW       │  These are VERY similar
│  ● Electrical Control               │  → Use pattern knowledge!
└─────────────────────────────────────┘

Medium Similarity Zone (50-80%):
  ● Mechanical Part                      Some similarities
                                        → Consider pattern

Low Similarity Zone (<50%):
  ● Civil Blueprint                      Different types
  ● P&ID Process                        → Full analysis needed


MATCHING LOGIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If distance between NEW ⭐ and stored ●:
  • Small distance (>80%) → High match → Fast path
  • Medium distance (50-80%) → Moderate → Consider
  • Large distance (<50%) → No match → Slow path
```

---

## 🎯 Confidence Calculation Flow

```
┌─────────────────────────────────────────────────────────────┐
│              CONFIDENCE CALCULATION ENGINE                  │
└─────────────────────────────────────────────────────────────┘

Input Factors:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. SIMILARITY SCORE (40% weight)
   ┌─────────────────────────────────┐
   │ New vs Stored Embedding         │
   │ Score: 89%                      │
   │ Contribution: 89% × 0.4 = 35.6% │
   └─────────────────────────────────┘

2. HISTORICAL ACCURACY (30% weight)
   ┌─────────────────────────────────┐
   │ Pattern's Past Performance      │
   │ Score: 82%                      │
   │ Contribution: 82% × 0.3 = 24.6% │
   └─────────────────────────────────┘

3. USAGE FREQUENCY (15% weight)
   ┌─────────────────────────────────┐
   │ How Often Pattern Used          │
   │ Uses: 25 times                  │
   │ Score: 90% (highly proven)      │
   │ Contribution: 90% × 0.15 = 13.5%│
   └─────────────────────────────────┘

4. DOMAIN MATCH (10% weight)
   ┌─────────────────────────────────┐
   │ Query vs Pattern Domain         │
   │ Match: Electrical = Electrical  │
   │ Score: 100%                     │
   │ Contribution: 100% × 0.1 = 10%  │
   └─────────────────────────────────┘

5. QUERY CLARITY (5% weight)
   ┌─────────────────────────────────┐
   │ How Clear is User Query         │
   │ Score: 85%                      │
   │ Contribution: 85% × 0.05 = 4.25%│
   └─────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL CONFIDENCE: 87.95% ≈ 88%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Confidence Bands:
  90-100% → ⭐⭐⭐ Expert level (rare)
  80-89%  → ⭐⭐   High confidence
  70-79%  → ⭐     Good confidence
  50-69%  → ⚠️     Medium confidence
  <50%    → ❓     Low confidence (full analysis)
```

---

## 🔄 Learning Cycle Over Time

```
ITERATION 1 (First Time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────┐    ┌──────────┐    ┌─────────┐
│ Diagram │ →  │ Analyze  │ →  │ Answer  │
│   New   │    │ (500ms)  │    │  33%    │
└─────────┘    └──────────┘    └─────────┘
                      │
                      ↓
                ┌──────────┐
                │ LEARN &  │
                │  SAVE    │
                │ Pattern  │
                │   v1     │
                └──────────┘


ITERATION 2 (Similar Diagram)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ Diagram │ →  │ Search   │ →  │ Analyze  │ →  │ Answer  │
│Similar! │    │ MATCH! ✓ │    │ (200ms)  │    │  65%    │
└─────────┘    └──────────┘    └──────────┘    └─────────┘
                                      │
                                      ↓
                                ┌──────────┐
                                │ UPDATE   │
                                │ Pattern  │
                                │   v2     │
                                └──────────┘


ITERATION 5 (More Similar Diagrams)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ Diagram │ →  │ Search   │ →  │ Analyze  │ →  │ Answer  │
│Similar! │    │ MATCH! ✓ │    │ (120ms)  │    │  78%    │
└─────────┘    └──────────┘    └──────────┘    └─────────┘
                                      │
                                      ↓
                                ┌──────────┐
                                │ REFINE   │
                                │ Pattern  │
                                │   v5     │
                                └──────────┘


ITERATION 25 (Expert Level)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ Diagram │ →  │ Search   │ →  │ Analyze  │ →  │ Answer  │
│Similar! │    │ MATCH! ✓ │    │  (50ms)  │    │  88%    │
└─────────┘    └──────────┘    └──────────┘    └─────────┘
                                      │
                                      ↓
                                ┌──────────┐
                                │ EXPERT   │
                                │ Pattern  │
                                │  v25 ⭐  │
                                └──────────┘

TRAJECTORY:
  Time:       500ms → 200ms → 120ms → 50ms  (10x faster!)
  Confidence:  33% →  65% →  78% →  88%     (2.7x better!)
  Version:     v1 →   v2 →   v5 →   v25     (refined!)
```

---

## 🗺️ Memory Atlas Storage Structure

```
MEMORY ATLAS DIRECTORY STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

memory_atlas/
│
├── electrical_20251015_093734_0.json  ← Pattern file
│   ├── pattern_id: "electrical_20251015_093734_0"
│   ├── version_id: "v25"
│   ├── parent_version: "v24"
│   ├── domain: "electrical"
│   ├── features: [0.36, 0.04, -0.02, ...] (512 numbers)
│   ├── components: [transformer, breakers, ...]
│   ├── accuracy: 0.82
│   ├── success_count: 25
│   ├── contexts: ["power distribution"]
│   └── timestamp: "2025-10-15T09:37:34"
│
├── electrical_20251012_141523_3.json
├── mechanical_20251013_082145_7.json
├── pid_20251014_153022_1.json
└── ...


AZURE AI SEARCH INDEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

edison-cognitive-patterns
│
├── [Document 1]
│   ├── id: "electrical_20251015_093734_0_v25"
│   ├── pattern_id: "electrical_20251015_093734_0"
│   ├── feature_embedding: [512-dim vector]  ← For similarity search
│   ├── domain: "electrical"
│   ├── accuracy: 0.82
│   ├── retrieval_count: 25
│   └── ... (19 fields total)
│
├── [Document 2]
├── [Document 3]
└── ... (100+ documents)


HYBRID RETRIEVAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Query arrives
     │
     ↓
Try Azure AI Search first
     │
     ├─→ Success (30ms) ────────→ Use cloud result
     │
     └─→ Failed/Offline
            │
            ↓
         Fallback to local JSON (50ms) → Use local result
```

---

## 📈 Performance Improvement Graph

```
PERFORMANCE METRICS OVER 90 DAYS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Response Time (milliseconds):
500 │●
    │ ╲
400 │  ●
    │   ╲
300 │    ●──●
    │        ╲
200 │         ●──●──●
    │                ╲
100 │                 ●──●──●──●
    │                             ╲
  0 │                              ●───●───●───●
    └──┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───
      Day 10  20  30  40  50  60  70  80  90


Confidence Score (%):
100 │                                    ●───●───●
    │                               ●───●
 80 │                          ●───●
    │                     ●───●
 60 │                ●───●
    │           ●───●
 40 │      ●───●
    │ ●───●
 20 │
    └──┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───
      Day 10  20  30  40  50  60  70  80  90


Pattern Count:
300 │                                          ●
    │                                      ●──●
250 │                                  ●──●
    │                              ●──●
200 │                          ●──●
    │                      ●──●
150 │                  ●──●
    │              ●──●
100 │          ●──●
    │      ●──●
 50 │  ●──●
    │●─●
  0 └──┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───
      Day 10  20  30  40  50  60  70  80  90


Pattern Match Rate (%):
100 │                                      ●───●
    │                                  ●───●
 80 │                              ●───●
    │                          ●───●
 60 │                      ●───●
    │                  ●───●
 40 │              ●───●
    │          ●───●
 20 │      ●───●
    │  ●───●
  0 │●─●
    └──┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───
      Day 10  20  30  40  50  60  70  80  90
```

---

## 🎓 Key Visualization Insights

1. **System Architecture**: Shows how all components work together
2. **Decision Tree**: Demonstrates the fast vs slow path logic
3. **Vector Space**: Visualizes how similarity matching works
4. **Confidence Calculation**: Breaks down how confidence is computed
5. **Learning Cycle**: Shows improvement over iterations
6. **Storage Structure**: Explains hybrid storage approach
7. **Performance Graphs**: Proves measurable improvements over time

These diagrams illustrate why even ONE pattern makes a significant difference!

---

Back to: **[Wiki Home](README.md)**
