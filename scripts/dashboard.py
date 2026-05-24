"""
Dashboard for LLM-Generated Test Cases
Shows execution results, strategy comparisons, and edge-case analysis
"""

import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from collections import defaultdict

# Page setup
st.set_page_config(
    page_title="LLM Test Generator · Dashboard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Light theme styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

/* Clean white background */
.stApp {
    background-color: #f8fafc;
}

/* Header banner */
.hero {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.25);
}
.hero h1 { margin: 0; font-weight: 800; font-size: 1.9rem; }
.hero p  { margin: 0.3rem 0 0; opacity: 0.9; font-size: 1rem; }

/* Metric cards with soft shadows */
.card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 1px 8px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
    margin-bottom: 0.8rem;
}
.card h3 {
    color: #64748b;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 0.3rem;
}
.card .num {
    color: #1e293b;
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1.1;
}
.card .detail {
    color: #94a3b8;
    font-size: 0.8rem;
    margin-top: 0.2rem;
}

/* Insight boxes */
.tip {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    color: #166534;
    margin-bottom: 0.6rem;
    font-size: 0.92rem;
}

/* Section titles */
.section-title {
    color: #1e293b;
    font-size: 1.2rem;
    font-weight: 700;
    margin: 1.5rem 0 0.6rem;
    padding-bottom: 0.3rem;
    border-bottom: 2px solid #e2e8f0;
}
</style>
""", unsafe_allow_html=True)


# --- Load data from results folder ---

RESULTS = Path("results")

@st.cache_data
def load_data():
    """Load all three result files. Returns None if missing."""
    try:
        execution = json.loads((RESULTS / "execution_summary.json").read_text())
        edge_cases = json.loads((RESULTS / "edge_case_scoring.json").read_text())
        generated = json.loads((RESULTS / "generated_tests_by_strategy.json").read_text())
        return execution, edge_cases, generated
    except FileNotFoundError:
        return None, None, None

exec_data, edge_data, gen_data = load_data()

if not exec_data:
    st.error("Results not found. Please run the pipeline first.")
    st.stop()

# Pull out the pieces we need
summary = exec_data["summary"]
results = exec_data.get("results", [])
edge_items = edge_data.get("items", []) if edge_data else []
edge_summary = edge_data.get("summary", {}) if edge_data else {}

# Common plotly style for light backgrounds
def chart_style(**extras):
    base = dict(
        paper_bgcolor="white",
        plot_bgcolor="#fafafa",
        font=dict(family="Inter", color="#334155"),
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor="#f1f5f9"),
        yaxis=dict(gridcolor="#f1f5f9"),
    )
    base.update(extras)
    return base


# --- Sidebar with filters ---

all_strategies = sorted({r.get("prompt_strategy", "unknown") for r in results})
all_functions = sorted({r.get("function_name", "?") for r in results})

with st.sidebar:
    st.markdown("### 🎛️ Controls")

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # Let user pick which strategies and functions to show
    selected_strategies = st.multiselect("Strategies", all_strategies, default=all_strategies)
    selected_functions = st.multiselect("Functions", all_functions, default=all_functions)
    passed_only = st.toggle("Show passed only", False)

    st.divider()
    st.markdown("### 📊 Dataset Info")
    st.metric("Methods", len(all_functions))
    st.metric("Strategies", len(all_strategies))
    st.metric("Total Tests", summary["total"])

# Apply filters to results
filtered = [
    r for r in results
    if r.get("prompt_strategy") in selected_strategies
    and r.get("function_name") in selected_functions
    and (not passed_only or r.get("passed"))
]


# --- Header ---

st.markdown("""
<div class="hero">
    <h1>🧬 LLM-Generated Test Cases Dashboard</h1>
    <p>Execution-Grounded Evaluation · Self-Repair · Multi-Strategy Comparison</p>
</div>
""", unsafe_allow_html=True)


# --- Top metric cards ---

total = summary["total"]
passed = summary["passed"]
failed = summary["failed"]
repair_attempted = summary["repair_attempted"]
repair_success = summary["repair_success"]
avg_duration = summary["avg_duration_sec"]
avg_edge = edge_summary.get("avg_score", 0)

def make_card(icon, label, value, detail=""):
    return f"""<div class="card">
        <h3>{icon} {label}</h3>
        <div class="num">{value}</div>
        <div class="detail">{detail}</div>
    </div>"""

c1, c2, c3, c4, c5 = st.columns(5)

pass_pct = passed * 100 // total if total else 0
fail_pct = failed * 100 // total if total else 0
repair_pct = repair_success * 100 // repair_attempted if repair_attempted else 0

with c1:
    st.markdown(make_card("✅", "Pass Rate", f"{passed}/{total}", f"{pass_pct}% overall"), unsafe_allow_html=True)
with c2:
    st.markdown(make_card("❌", "Failed", str(failed), f"{fail_pct}% unresolved"), unsafe_allow_html=True)
with c3:
    st.markdown(make_card("🔧", "Repair Success", f"{repair_success}/{repair_attempted}", f"{repair_pct}% fix rate"), unsafe_allow_html=True)
with c4:
    st.markdown(make_card("⏱️", "Avg Duration", f"{avg_duration:.2f}s", "per test"), unsafe_allow_html=True)
with c5:
    st.markdown(make_card("🎯", "Edge Score", f"{avg_edge:.0%}", f"across {len(edge_items)} tests"), unsafe_allow_html=True)


# --- Auto-generated insights ---

st.markdown('<div class="section-title">💡 Key Insights</div>', unsafe_allow_html=True)

# Figure out which strategy performed best
strat_stats = defaultdict(lambda: {"passed": 0, "failed": 0, "total": 0, "repaired": 0})
for r in results:
    s = r.get("prompt_strategy", "?")
    strat_stats[s]["total"] += 1
    if r.get("passed"):
        strat_stats[s]["passed"] += 1
    else:
        strat_stats[s]["failed"] += 1
    if r.get("repair_success"):
        strat_stats[s]["repaired"] += 1

best_strategy = max(strat_stats, key=lambda s: strat_stats[s]["passed"] / max(strat_stats[s]["total"], 1))
best_pct = strat_stats[best_strategy]["passed"] * 100 // max(strat_stats[best_strategy]["total"], 1)

# Which strategy has best edge-case scores
edge_by_strat = defaultdict(list)
for item in edge_items:
    edge_by_strat[item.get("prompt_strategy", "?")].append(item["score"])
best_edge_strat = max(edge_by_strat, key=lambda s: np.mean(edge_by_strat[s])) if edge_by_strat else "N/A"
best_edge_avg = np.mean(edge_by_strat[best_edge_strat]) if edge_by_strat else 0

# What's the most common error
error_cats = summary.get("by_error_category", {})
top_error = max((k for k in error_cats if k != "passed_after_repair"), key=lambda k: error_cats[k], default="none")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="tip">🏆 <strong>Best strategy:</strong> {best_strategy} — {best_pct}% pass rate</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="tip">🎯 <strong>Best edge coverage:</strong> {best_edge_strat} — {best_edge_avg:.0%} avg</div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="tip">⚠️ <strong>Top error:</strong> {top_error} — {error_cats.get(top_error, 0)} occurrences</div>', unsafe_allow_html=True)


# --- Strategy comparison charts ---

st.markdown('<div class="section-title">🔀 Strategy Comparison</div>', unsafe_allow_html=True)

col_left, col_right = st.columns(2)

# Grouped bar chart: passed vs repaired vs failed by strategy
with col_left:
    strat_names = sorted(strat_stats.keys())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Passed", x=strat_names,
        y=[strat_stats[s]["passed"] for s in strat_names],
        marker_color="#10b981",
        text=[strat_stats[s]["passed"] for s in strat_names],
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        name="Repaired", x=strat_names,
        y=[strat_stats[s]["repaired"] for s in strat_names],
        marker_color="#8b5cf6",
        text=[strat_stats[s]["repaired"] for s in strat_names],
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        name="Failed", x=strat_names,
        y=[strat_stats[s]["failed"] - strat_stats[s]["repaired"] for s in strat_names],
        marker_color="#ef4444",
        text=[strat_stats[s]["failed"] - strat_stats[s]["repaired"] for s in strat_names],
        textposition="outside"
    ))
    fig.update_layout(**chart_style(
        title="Pass / Repair / Fail by Strategy",
        barmode="group", height=420,
        legend=dict(orientation="h", y=-0.15)
    ))
    st.plotly_chart(fig, width='stretch')

# Radar chart: edge-case category coverage per strategy
with col_right:
    coverage_rate = edge_summary.get("category_coverage_rate", {})
    categories = list(coverage_rate.keys())

    if categories:
        # Build per-strategy coverage from individual items
        strat_coverage = defaultdict(lambda: defaultdict(list))
        for item in edge_items:
            s = item.get("prompt_strategy", "?")
            for cat, hit in item.get("covered", {}).items():
                strat_coverage[s][cat].append(1 if hit else 0)

        colors = {"baseline_name_only": "#f59e0b", "advanced_with_code": "#10b981", "strict_import_focal_module": "#6366f1"}

        fig = go.Figure()
        for s in sorted(strat_coverage.keys()):
            values = [np.mean(strat_coverage[s].get(c, [0])) * 100 for c in categories]
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=s[:25],
                line=dict(color=colors.get(s, "#6366f1")),
                opacity=0.7,
            ))

        fig.update_layout(**chart_style(
            title="Edge-Case Coverage Radar by Strategy",
            height=420,
            polar=dict(
                bgcolor="#fafafa",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e2e8f0", color="#64748b"),
                angularaxis=dict(gridcolor="#e2e8f0", color="#64748b"),
            ),
            legend=dict(orientation="h", y=-0.15),
        ))
        st.plotly_chart(fig, width='stretch')


# --- Sankey: test outcome flow ---

st.markdown('<div class="section-title">🌊 Test Outcome Flow</div>', unsafe_allow_html=True)

# Calculate how many passed on first try vs after repair
first_run_pass = passed - repair_success
first_run_fail = total - first_run_pass
unrepairable = first_run_fail - repair_success

# Build the sankey nodes and links
labels = ["All Tests", "Passed (1st run)", "Failed (1st run)", "Repaired ✅", "Unrepairable ❌"]
error_labels = [k for k in error_cats if k != "passed_after_repair"]
labels += error_labels

sources = [0, 0, 2, 2]
targets = [1, 2, 3, 4]
values = [first_run_pass, first_run_fail, repair_success, unrepairable]
link_colors = ["rgba(16,185,129,0.4)", "rgba(239,68,68,0.3)", "rgba(139,92,246,0.4)", "rgba(239,68,68,0.3)"]

# Connect unrepairable to specific error types
for i, err in enumerate(error_labels):
    sources.append(4)
    targets.append(5 + i)
    values.append(error_cats[err])
    link_colors.append("rgba(148,163,184,0.25)")

fig = go.Figure(go.Sankey(
    node=dict(
        pad=20, thickness=25,
        label=labels,
        color=["#6366f1", "#10b981", "#ef4444", "#8b5cf6", "#f43f5e"] + ["#94a3b8"] * len(error_labels),
    ),
    link=dict(source=sources, target=targets, value=values, color=link_colors),
))
fig.update_layout(**chart_style(title="Test Outcome Flow", height=400))
st.plotly_chart(fig, width='stretch')


# --- Error analysis ---

st.markdown('<div class="section-title">🚨 Error Analysis</div>', unsafe_allow_html=True)

col_left, col_right = st.columns(2)

# Donut chart of error categories
with col_left:
    if error_cats:
        err_labels = list(error_cats.keys())
        err_values = list(error_cats.values())
        err_colors = [
            "#10b981" if "pass" in l else
            "#ef4444" if "syntax" in l else
            "#f59e0b" if "assert" in l else
            "#6366f1" if "import" in l else "#94a3b8"
            for l in err_labels
        ]

        fig = go.Figure(go.Pie(
            labels=err_labels, values=err_values, hole=0.55,
            marker=dict(colors=err_colors),
            textinfo="label+percent+value",
            textfont=dict(size=12),
        ))
        fig.update_layout(**chart_style(title="Error Category Distribution", height=400))
        st.plotly_chart(fig, width='stretch')

# Error table + duration box plot
with col_right:
    if error_cats:
        df_err = pd.DataFrame(
            sorted(error_cats.items(), key=lambda x: x[1], reverse=True),
            columns=["Error Type", "Count"],
        )
        df_err["Percentage"] = (df_err["Count"] / df_err["Count"].sum() * 100).round(1).astype(str) + "%"
        st.dataframe(df_err, width='stretch', hide_index=True)

    # Box plot showing execution time per strategy
    dur_rows = [{"Strategy": r.get("prompt_strategy", "?"), "Duration (s)": r.get("duration_sec", 0)} for r in results]
    if dur_rows:
        df_dur = pd.DataFrame(dur_rows)
        fig = px.box(
            df_dur, x="Strategy", y="Duration (s)", color="Strategy",
            color_discrete_sequence=["#f59e0b", "#10b981", "#6366f1"],
        )
        fig.update_layout(**chart_style(title="Execution Duration by Strategy", height=300, showlegend=False))
        st.plotly_chart(fig, width='stretch')


# --- Heatmaps ---

st.markdown('<div class="section-title">🗺️ Heatmaps</div>', unsafe_allow_html=True)

col_left, col_right = st.columns(2)

# Heatmap: which function passed/failed/was repaired under each strategy
with col_left:
    heatmap_data = {}
    for r in filtered:
        fn = r.get("function_name", "?")
        strat = r.get("prompt_strategy", "?")
        # 2 = passed first try, 1 = repaired, 0 = failed
        if r.get("passed") and not r.get("repair_success"):
            val = 2
        elif r.get("repair_success"):
            val = 1
        else:
            val = 0
        heatmap_data.setdefault(fn, {})[strat] = val

    if heatmap_data:
        df_heat = pd.DataFrame(heatmap_data).T.fillna(-1)
        fig = go.Figure(go.Heatmap(
            z=df_heat.values,
            x=df_heat.columns.tolist(),
            y=df_heat.index.tolist(),
            colorscale=[[0, "#fecaca"], [0.5, "#c4b5fd"], [1, "#86efac"]],
            text=[["Pass" if v == 2 else "Repair" if v == 1 else "Fail" for v in row] for row in df_heat.values],
            texttemplate="%{text}",
            zmin=0, zmax=2, showscale=False,
        ))
        fig.update_layout(**chart_style(
            title="Function × Strategy Outcome",
            height=420,
            yaxis=dict(gridcolor="#f1f5f9", dtick=1),
            xaxis=dict(gridcolor="#f1f5f9"),
        ))
        st.plotly_chart(fig, width='stretch')

# Heatmap: edge-case coverage per function
with col_right:
    if edge_items:
        edge_heat = {}
        for item in edge_items:
            fn = item.get("function_name", "?")
            for cat, hit in item.get("covered", {}).items():
                edge_heat.setdefault(fn, {})[cat] = edge_heat.get(fn, {}).get(cat, 0) + (1 if hit else 0)

        df_edge = pd.DataFrame(edge_heat).T.fillna(0)
        # Normalize by number of strategies so values are 0-1
        df_edge = df_edge / max(len(all_strategies), 1)

        fig = go.Figure(go.Heatmap(
            z=df_edge.values,
            x=df_edge.columns.tolist(),
            y=df_edge.index.tolist(),
            colorscale="YlGnBu",
            zmin=0, zmax=1,
            text=np.round(df_edge.values, 2),
            texttemplate="%{text:.0%}",
        ))
        fig.update_layout(**chart_style(
            title="Edge-Case Coverage by Function",
            height=420,
            yaxis=dict(gridcolor="#f1f5f9", dtick=1),
            xaxis=dict(gridcolor="#f1f5f9", tickangle=45),
        ))
        st.plotly_chart(fig, width='stretch')


# --- Code viewer ---

st.markdown('<div class="section-title">🔍 Code Viewer</div>', unsafe_allow_html=True)

# Build a quick lookup so we can show original generated code
gen_lookup = {}
if gen_data:
    for g in gen_data:
        key = (g.get("method_name", ""), g.get("prompt_strategy", ""))
        gen_lookup[key] = g.get("generated_test", "")

# Show each test as an expandable section
for r in filtered[:20]:
    fn = r.get("function_name", "?")
    strat = r.get("prompt_strategy", "?")
    status = "✅ Passed" if r.get("passed") else "❌ Failed"
    tag = " (repaired)" if r.get("repair_success") else ""

    with st.expander(f"{status}{tag}  ·  {fn}  ·  {strat}", expanded=False):
        left, right = st.columns(2)

        with left:
            st.caption("📝 Generated Test")
            original = gen_lookup.get((fn, strat), "No code available")
            st.code(original[:2000] if original else "N/A", language="python")

        with right:
            if r.get("repair_success") and r.get("repaired_test_code"):
                st.caption("🔧 Repaired Test")
                st.code(r["repaired_test_code"][:2000], language="python")
            else:
                st.caption("📋 Pytest Output")
                st.code(r.get("pytest_output_tail", "No output")[:2000], language="text")


# --- Detailed results table ---

st.markdown('<div class="section-title">📋 Detailed Results</div>', unsafe_allow_html=True)

rows = []
for r in filtered:
    rows.append({
        "Function": r.get("function_name", "?"),
        "Strategy": r.get("prompt_strategy", "?"),
        "Status": "✅" if r.get("passed") else "❌",
        "Error": r.get("error_category", "—"),
        "Duration": f"{r.get('duration_sec', 0):.2f}s",
        "Repaired": "✅" if r.get("repair_success") else ("🔄" if r.get("repair_attempted") else "—"),
    })

if rows:
    df_table = pd.DataFrame(rows)
    st.dataframe(df_table, width='stretch', hide_index=True, height=400)

    # Let user download filtered results as CSV
    csv = df_table.to_csv(index=False)
    st.download_button("📥 Export CSV", csv, "llm_test_results.csv", "text/csv", use_container_width=True)


# --- Footer ---

st.markdown("""
---
<div style="text-align: center; color: #94a3b8; padding: 1rem; font-size: 0.9rem;">
    <strong>🧬 LLM Test Generator</strong> · Ollama + Llama3 + Pytest + Streamlit<br>
    Execution-grounded evaluation with self-repair · May 2026
</div>
""", unsafe_allow_html=True)