# LLM-Based Automatic Unit Test Generation with Execution & Self-Repair

---

## Overview

This project **automatically generates, executes, and repairs unit tests** for Python functions using LLMs with multiple prompt strategies.

**Key improvements (May 2026):**
- ✅ Execution-grounded evaluation (pytest)
- ✅ Self-repair loop (LLM fixes failing tests)
- ✅ Multiple prompt strategies comparison
- ✅ Edge-case scoring
- ✅ Real pass/fail metrics

---

## Quick Start

### 1. Setup (one-time)

```bash
cd LLM_Generated_Testcases
source .venv/bin/activate
pip install -U pip ollama pytest streamlit plotly pandas numpy
ollama pull llama3
```

### 2. Run Complete Pipeline

```bash
touch scripts/__init__.py
sed -i '' 's/from scripts.prompt_strategies/from prompt_strategies/' scripts/generate_tests_llm_advanced.py

python3 scripts/enrich_sampled_methods_with_code.py && \
python3 scripts/generate_tests_llm_advanced.py && \
python3 scripts/execute_generated_tests.py && \
python3 scripts/edge_case_scoring.py && \
streamlit run scripts/dashboard.py
```

---

## Pipeline Steps

| Step | Script | Output | Time |
|------|--------|--------|------|
| 1 | `enrich_sampled_methods_with_code.py` | `sampled_methods_with_code.json` | 1-2 min (1st), <1s (cached) |
| 2 | `generate_tests_llm_advanced.py` | `generated_tests_by_strategy.json` | ~1 min per 20 methods |
| 3 | `execute_generated_tests.py` | `execution_summary.json` | ~2-3 min per 20 methods |
| 4 | `edge_case_scoring.py` | `edge_case_scoring.json` | ~1 min |
| 5 | `dashboard.py` | Interactive dashboard | instant |

---

## Example Output

```
EXECUTION SUMMARY
============================================================
Total tests: 30 (10 methods × 3 strategies)
Passed: 10 (33.3%)
Failed: 20 (66.7%)
Repair attempted: 30
Repair success: 10 (33.3%)
Avg duration: 0.50s

Error categories:
  - syntax_error: 20
  - passed_after_repair: 10
============================================================
```

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                     LLM Test Generation Pipeline                │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│  1. Enrich   │ 2. Generate  │ 3. Execute   │ 4. Score          │
│              │              │   + Repair   │                   │
│ sampled_     │ strategies   │ pytest in    │ AST-based edge    │
│ methods.json │ .json config │ sandbox      │ case analysis     │
│     ↓        │     ↓        │     ↓        │     ↓             │
│ methods_     │ tests_by_    │ execution_   │ edge_case_        │
│ with_code    │ strategy     │ summary      │ scoring           │
│ .json        │ .json        │ .json        │ .json             │
├──────────────┴──────────────┴──────────────┴───────────────────┤
│              5. Dashboard (Streamlit + Plotly)                  │
│  • Strategy comparison  • Sankey flow  • Radar charts          │
│  • Heatmaps  • Code viewer  • CSV export                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prompt Strategies

| Strategy | Temperature | Use Case |
|----------|-------------|----------|
| `baseline` | 0.3 | Simple, predictable tests |
| `context` | 0.5 | Balanced coverage |
| `advanced` | 0.7 | Edge cases + diversity |

---

## Key Metrics

- **Pass Rate:** % of tests that pass on first run
- **Repair Success:** % of failing tests fixed by LLM
- **Edge-Case Coverage:** % of boundary conditions tested
- **Avg Duration:** Time per test execution

---

## Troubleshooting

```bash
# Check Ollama is running
ollama list

# Start Ollama if needed (separate terminal)
ollama serve

# Pull model if missing
ollama pull llama3

# Test small subset first (5 methods)
python3 - <<'PY'
import json
from pathlib import Path
methods = json.loads(Path("results/sampled_methods_with_code.json").read_text())[:5]
Path("results/sampled_methods_with_code.json").write_text(json.dumps(methods, indent=2))
PY
```

---

## Results Location

```
results/
├── sampled_methods_with_code.json      # Input methods with code
├── generated_tests_by_strategy.json    # Generated tests per strategy
├── execution_summary.json              # Pass/fail metrics + repairs
└── edge_case_scoring.json              # Edge-case coverage
```

---

## Viewing Results

### In Code (no dashboard):

```bash
python3 - <<'PY'
import json, collections

d = json.load(open("results/execution_summary.json"))
print(json.dumps(d["summary"], indent=2))

# By strategy
strategies = collections.defaultdict(lambda: {"passed": 0, "total": 0})
for r in d["results"]:
    s = r.get("prompt_strategy", "unknown")
    strategies[s]["total"] += 1
    if r.get("passed"):
        strategies[s]["passed"] += 1

for strat, stats in sorted(strategies.items()):
    pct = stats["passed"] * 100 // stats["total"]
    print(f"{strat}: {stats['passed']}/{stats['total']} ({pct}%)")
PY
```

### In Dashboard:

```bash
streamlit run scripts/dashboard.py
# Opens http://localhost:8501
```

---

## For Production (300-500 tests)

Edit `scripts/generate_tests_llm_advanced.py`:

```python
MAX_METHODS = 500  # or your full dataset size
for i, m in enumerate(methods[:MAX_METHODS]):
    ...
```

Expected runtime: **~1.5-2 hours** (enrich + generate + execute + score)

---

## Project Structure

```
LLM_Generated_Testcases/
├── pymethods2test/data/                    # Dataset
├── scripts/
│   ├── enrich_sampled_methods_with_code.py # NEW: load dataset code
│   ├── generate_tests_llm_advanced.py      # Generate by strategy
│   ├── execute_generated_tests.py          # NEW: run + repair
│   ├── edge_case_scoring.py                # NEW: measure coverage
│   ├── prompt_strategies.py                # NEW: strategy loader
│   └── dashboard.py                        # NEW: premium dashboard
├── configs/
│   └── prompt_strategies.json              # NEW: strategy config
├── results/
│   ├── sampled_methods.json
│   ├── sampled_methods_with_code.json      # NEW
│   ├── generated_tests_by_strategy.json    # NEW
│   ├── execution_summary.json              # NEW
│   └── edge_case_scoring.json              # NEW
└── README.md
```

---

## Dashboard Features

- 📊 Pass/fail rates by strategy (grouped bar chart)
- 🔧 Repair success metrics with Sankey flow diagram
- 🎯 Edge-case coverage radar chart by strategy
- 🗺️ Function × Strategy heatmap
- 📈 Error category donut chart + duration box plot
- 🔍 Side-by-side code viewer (generated vs repaired)
- 💡 Auto-generated insights
- 📥 CSV export

---

## Technologies

- **LLM:** Ollama + Llama3
- **Execution:** pytest
- **Visualization:** Streamlit
- **Dataset:** pyMethods2Test

---

## Status

✅ Pipeline complete with execution-grounded evaluation  
✅ Self-repair loop implemented  
✅ Multiple strategies tested  
✅ Dashboard deployed  

---

## Citation

```
LLM-Generated Test Cases with Execution & Self-Repair (May 2026)
Focal-method dataset approach with real pytest validation
```