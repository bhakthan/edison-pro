# Query Matching Flow - How Your Questions Find Answers

This page shows exactly what happens when you ask EDISON a question about a diagram.

## 🎯 The Complete Flow

Let's trace a user query from start to finish, showing how the Memory Atlas helps.

---

## 📝 User Query Example

**User uploads:** `power_distribution_diagram.png`

**User asks:** *"What are the main components in this electrical diagram and what's their purpose?"*

---

## 🔄 Step-by-Step Flow

### Step 1: Query Preprocessing

```
┌──────────────────────────────────────────────────────┐
│  USER INPUT                                          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  Image: power_distribution_diagram.png               │
│  Question: "What are the main components..."         │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
┌──────────────────────────────────────────────────────┐
│  FLICKERING SYSTEM RECEIVES INPUT                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  1. Load image from file                             │
│  2. Extract user intent from question                │
│  3. Prepare for analysis                             │
│                                                      │
│  Detected Intent:                                    │
│    • Type: Component identification                  │
│    • Domain: Electrical (likely)                     │
│    • Complexity: Medium                              │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 2: Create Embedding (Fingerprint)

```
┌──────────────────────────────────────────────────────┐
│  VISION AGENT ANALYZES IMAGE                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  📸 Process image through Azure AI Vision            │
│  🧮 Generate 512-dimensional embedding               │
│                                                      │
│  Visual Features Detected:                           │
│    • Lines: Vertical and horizontal                  │
│    • Symbols: Electrical notation                    │
│    • Text: Labels present                            │
│    • Layout: Grid-based                              │
│    • Complexity: Moderate                            │
│                                                      │
│  Embedding Created:                                  │
│  [0.68, 0.47, -0.22, 0.49, -0.18, 0.14, ...]        │
│                                                      │
│  ⏱️  Time: ~50ms                                     │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 3: Search Memory Atlas (THE KEY STEP!)

```
┌──────────────────────────────────────────────────────┐
│  MEMORY ATLAS AGENT - PATTERN SEARCH                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  🔍 Query Vector Database                            │
│     New embedding: [0.68, 0.47, -0.22, ...]         │
│                                                      │
│  🎯 Search Filters Applied:                          │
│     • Domain: electrical (from user intent)          │
│     • Accuracy: >70%                                 │
│     • Recency: Last 90 days                          │
│                                                      │
│  📊 RESULTS FROM AZURE AI SEARCH:                    │
│                                                      │
│  ┌─────────────────────────────────────────┐        │
│  │ Pattern 1: electrical_20251015_093734_0 │        │
│  │ Similarity: 89% ⭐⭐⭐                    │        │
│  │ Domain: electrical                       │        │
│  │ Accuracy: 82%                            │        │
│  │ Used: 25 times                           │        │
│  │ Context: Power distribution diagrams     │        │
│  │                                          │        │
│  │ Components Previously Found:             │        │
│  │   • Transformer (3-phase)                │        │
│  │   • Circuit breakers                     │        │
│  │   • Bus bars                             │        │
│  │   • Load connections                     │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
│  ┌─────────────────────────────────────────┐        │
│  │ Pattern 2: electrical_20251012_141523_3 │        │
│  │ Similarity: 76% ⭐⭐                      │        │
│  │ Domain: electrical                       │        │
│  │ Accuracy: 78%                            │        │
│  │ Context: Distribution panels             │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
│  ✅ BEST MATCH: Pattern 1 (89% similarity)          │
│                                                      │
│  ⏱️  Time: ~30ms (Azure Search)                     │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 4: Confidence Evaluation

```
┌──────────────────────────────────────────────────────┐
│  CONFIDENCE EVALUATOR                                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  📊 Calculate Confidence Based On:                   │
│                                                      │
│  1. Similarity Score: 89% → HIGH                     │
│  2. Pattern Accuracy: 82% → HIGH                     │
│  3. Past Success: 25 uses → PROVEN                   │
│  4. Domain Match: electrical ✓ → EXACT              │
│  5. Query Complexity: Medium → MANAGEABLE            │
│                                                      │
│  🎯 OVERALL CONFIDENCE: 76%                          │
│                                                      │
│  Confidence Breakdown:                               │
│    • Pattern Match: 89% (very similar!)              │
│    • Historical Success: 82% (worked before)         │
│    • Context Relevance: 85% (right domain)           │
│    • Query Clarity: 80% (clear question)             │
│                                                      │
│  Decision: HIGH CONFIDENCE - Use stored pattern!     │
│                                                      │
│  ⏱️  Time: ~10ms                                     │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 5: Guided Analysis (Fast Path)

```
┌──────────────────────────────────────────────────────┐
│  MULTI-AGENT ANALYSIS (Guided by Memory)            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  🚀 FAST PATH ACTIVATED                              │
│                                                      │
│  Retrieved Pattern Guides Analysis:                  │
│  ┌────────────────────────────────────────┐         │
│  │ "Look for these components first:"     │         │
│  │   • Transformer                        │         │
│  │   • Circuit breakers                   │         │
│  │   • Bus bars                           │         │
│  │   • Load connections                   │         │
│  │                                        │         │
│  │ "Common relationships:"                │         │
│  │   Transformer → Breakers → Buses → Loads        │
│  └────────────────────────────────────────┘         │
│                                                      │
│  Agent Coordination:                                 │
│                                                      │
│  👁️  Vision Agent:                                  │
│     ✓ Locate transformer (top) - FOUND               │
│     ✓ Identify breakers (middle) - FOUND             │
│     ✓ Track bus connections - FOUND                  │
│                                                      │
│  🔤 Symbol Agent:                                    │
│     ✓ Recognize electrical symbols - MATCHED         │
│     ✓ Identify component types - CONFIRMED           │
│                                                      │
│  🧩 Context Agent:                                   │
│     ✓ Map relationships - AS EXPECTED                │
│     ✓ Understand flow - POWER DISTRIBUTION           │
│                                                      │
│  ⚡ Fewer iterations needed (guided by pattern)      │
│                                                      │
│  ⏱️  Time: ~150ms (vs 500ms without pattern!)       │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 6: Generate Response

```
┌──────────────────────────────────────────────────────┐
│  INTERPRETATION AGENT - FINAL ANSWER                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  📝 Synthesize findings with pattern context:        │
│                                                      │
│  ANSWER GENERATED:                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  "This is a power distribution electrical diagram    │
│   (single-line format). Based on previous analysis   │
│   of similar diagrams, the main components are:      │
│                                                      │
│   🔧 TRANSFORMER (3-phase)                           │
│      Purpose: Steps down voltage from utility        │
│      Location: Top of diagram                        │
│      Rating: 480V secondary                          │
│                                                      │
│   🔧 CIRCUIT BREAKERS (200A)                         │
│      Purpose: Protect downstream circuits            │
│      Location: Distribution panel                    │
│      Quantity: 4 main breakers                       │
│                                                      │
│   🔧 BUS BARS (Copper)                               │
│      Purpose: Distribute power to loads              │
│      Configuration: Horizontal distribution          │
│                                                      │
│   🔧 LOAD CONNECTIONS                                │
│      Purpose: Feed power to end equipment            │
│      Quantity: 4 load circuits                       │
│                                                      │
│   The power flow is: Utility → Transformer →         │
│   Breakers → Bus Bars → Load Connections             │
│                                                      │
│   Confidence: 76% (High - based on 89% pattern       │
│   similarity and 82% historical accuracy)"           │
│                                                      │
│  ⏱️  Time: ~50ms                                     │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 7: Update Memory Atlas

```
┌──────────────────────────────────────────────────────┐
│  MEMORY ATLAS - PATTERN UPDATE                       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  🔄 Update Retrieved Pattern:                        │
│                                                      │
│  Pattern: electrical_20251015_093734_0               │
│  Changes:                                            │
│    • Retrieval count: 25 → 26                        │
│    • Last used: Updated to now                       │
│    • Avg similarity: 0.87 → 0.88 (improved!)         │
│    • Success count: 25 → 26                          │
│    • Accuracy: 82% → 83% (refined)                   │
│                                                      │
│  📊 Usage Statistics Updated in Azure Search         │
│                                                      │
│  Version History:                                    │
│    v24 → v25 → v26 (new!)                            │
│                                                      │
│  🎓 Pattern gets smarter with each use!              │
│                                                      │
│  ⏱️  Time: ~20ms                                     │
│                                                      │
└────────────────────┬─────────────────────────────────┘
                     │
                     ↓
```

### Step 8: Return to User

```
┌──────────────────────────────────────────────────────┐
│  FINAL RESPONSE TO USER                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│                                                      │
│  ✅ ANSWER DELIVERED                                 │
│                                                      │
│  Total Time: ~290ms                                  │
│    • Create embedding: 50ms                          │
│    • Search patterns: 30ms                           │
│    • Calculate confidence: 10ms                      │
│    • Guided analysis: 150ms                          │
│    • Generate response: 50ms                         │
│    • Update pattern: 20ms                            │
│                                                      │
│  📊 Performance vs. No Pattern:                      │
│    • Without pattern: ~500ms                         │
│    • With pattern: ~290ms                            │
│    • Speed improvement: 1.7x faster                  │
│                                                      │
│  📈 Quality vs. No Pattern:                          │
│    • Without pattern: 33% confidence                 │
│    • With pattern: 76% confidence                    │
│    • Confidence improvement: +43 points              │
│                                                      │
│  🎯 User Experience: SIGNIFICANTLY BETTER!           │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 🔀 Alternative Flow: No Pattern Match

What happens if NO similar pattern exists?

```
Step 3: Search Memory Atlas
│
├─→ NO MATCH FOUND (<70% similarity)
│   
│   ┌──────────────────────────────────────┐
│   │ 🔍 Search Results:                   │
│   │    Best match: 42% similarity        │
│   │    (too low to use)                  │
│   │                                      │
│   │ 💭 System: "This is new territory!"  │
│   │                                      │
│   │ Decision: FULL ANALYSIS MODE         │
│   └──────────────────────────────────────┘
│
├─→ Step 4: Full Analysis (Slow Path)
│   
│   ┌──────────────────────────────────────┐
│   │ 🐌 Deep Multi-Agent Analysis         │
│   │    • No guidance from patterns       │
│   │    • All agents work from scratch    │
│   │    • More iterations needed          │
│   │    • Lower initial confidence        │
│   │                                      │
│   │ ⏱️  Time: ~500ms (slower!)           │
│   │ ✅ Confidence: 33% (lower!)          │
│   └──────────────────────────────────────┘
│
└─→ Step 7: SAVE NEW PATTERN
    
    ┌──────────────────────────────────────┐
    │ 💾 Create New Pattern                │
    │    Pattern ID: mechanical_xxx        │
    │    Version: v1                       │
    │    Domain: mechanical (new!)         │
    │                                      │
    │ 🎓 System learned something new!     │
    │                                      │
    │ Next time: Will be faster!           │
    └──────────────────────────────────────┘
```

---

## 📊 Comparison: With vs Without Memory Atlas

### Timeline Comparison

**Without Memory Atlas (Every Query):**
```
0ms    100ms   200ms   300ms   400ms   500ms
│───────│───────│───────│───────│───────│
└─ Full analysis (slow) ─────────────────┘ ✓ Done

Confidence: 33%
```

**With Memory Atlas (Matched Query):**
```
0ms    100ms   200ms   300ms   400ms   500ms
│───────│───────│───────│
└─ Guided analysis ─────┘ ✓ Done
   (3x faster!)

Confidence: 76%
```

---

## 🎯 Key Insights

### 1. Pattern Matching Is the Speed Boost

```
Search Memory Atlas → Find Match → Fast Path
                  ↓
            No Match → Full Analysis → Save New Pattern
```

### 2. Confidence Comes from Experience

```
High Similarity (89%) + High Accuracy (82%) + Many Uses (25)
                        ↓
            HIGH CONFIDENCE (76%)
```

### 3. Continuous Improvement Loop

```
Query → Search → Match → Use Pattern → Update Stats
                                           ↓
                              Pattern Gets Smarter
                                           ↓
                              Next Query Even Better!
```

### 4. Hybrid Storage Ensures Speed

```
Azure Search (Cloud):
  • 30ms vector search
  • Millions of patterns
  • Semantic similarity

Local JSON (Backup):
  • 50ms file search
  • Offline capability
  • Privacy preserved

Automatic Fallback: Try cloud, use local if needed
```

---

## 💡 Real-World Impact

### Scenario: Engineering Firm Usage

**Week 1:**
- 100 queries
- 5 unique diagram types
- Average response: 500ms
- Average confidence: 35%

**Week 4:**
- 100 queries
- 50 stored patterns
- Average response: 150ms (3x faster!)
- Average confidence: 68% (near double!)

**Week 12:**
- 100 queries
- 200 stored patterns
- Average response: 80ms (6x faster!)
- Average confidence: 78% (much higher!)

**The system becomes an expert in YOUR specific diagram types!**

---

## ✅ Summary

The query matching flow shows how Memory Atlas:

1. **Recognizes** similar diagrams instantly (89% match)
2. **Retrieves** relevant past knowledge (30ms)
3. **Guides** faster analysis (150ms vs 500ms)
4. **Boosts** confidence significantly (76% vs 33%)
5. **Updates** itself after each use (self-improvement)

**Result:** Faster, smarter, more confident system with every query!

---

Next: **[Learning Over Time](learning-over-time.md)** - See the growth trajectory

Or: **[Confidence System](confidence-system.md)** - Understand the confidence calculations
