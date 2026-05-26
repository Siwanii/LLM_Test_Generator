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

/* Metric cards */
.card {
    background: white;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    border-top: 4px solid #e2e8f0;
    margin-bottom: 0.8rem;
    position: relative;
}
.card.green  { border-top-color: #10b981; }
.card.red    { border-top-color: #ef4444; }
.card.purple { border-top-color: #8b5cf6; }
.card.amber  { border-top-color: #f59e0b; }
.card.blue   { border-top-color: #3b82f6; }
.card h3 {
    color: #64748b;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin: 0 0 0.35rem;
}
.card .num {
    color: #1e293b;
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
}
.card .detail { color: #94a3b8; font-size: 0.8rem; margin-top: 0.25rem; }
.card .bar-bg {
    background: #f1f5f9;
    border-radius: 99px;
    height: 5px;
    margin-top: 0.6rem;
    overflow: hidden;
}
.card .bar-fill {
    height: 5px;
    border-radius: 99px;
    transition: width 0.5s ease;
}

/* Insight boxes */
.tip {
    background: #f0fdf4;
    border-left: 4px solid #10b981;
    border-radius: 0 10px 10px 0;
    padding: 0.9rem 1.1rem;
    color: #166534;
    margin-bottom: 0.6rem;
    font-size: 0.92rem;
}
.tip.amber { background:#fffbeb; border-color:#f59e0b; color:#92400e; }
.tip.red   { background:#fff1f2; border-color:#ef4444; color:#9f1239; }

/* Section titles */
.section-title {
    color: #1e293b;
    font-size: 1.15rem;
    font-weight: 700;
    margin: 2rem 0 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #e2e8f0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Pill badge */
.pill {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-left: 0.4rem;
}
.pill.green  { background: #dcfce7; color: #166534; }
.pill.red    { background: #fee2e2; color: #991b1b; }
.pill.purple { background: #ede9fe; color: #5b21b6; }
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

def make_card(icon, label, value, detail="", color="", pct=None, bar_color="#10b981"):
    bar_html = ""
    if pct is not None:
        bar_html = f'<div class="bar-bg"><div class="bar-fill" style="width:{pct}%;background:{bar_color}"></div></div>'
    return f'<div class="card {color}"><h3>{icon} {label}</h3><div class="num">{value}</div><div class="detail">{detail}</div>{bar_html}</div>'

c1, c2, c3, c4, c5 = st.columns(5)

pass_pct = passed * 100 // total if total else 0
fail_pct = failed * 100 // total if total else 0
repair_pct = repair_success * 100 // repair_attempted if repair_attempted else 0
edge_pct  = int(avg_edge * 100)

with c1:
    st.markdown(make_card("✅", "Pass Rate", f"{passed}/{total}", f"{pass_pct}% of all tests", "green", pass_pct, "#10b981"), unsafe_allow_html=True)
with c2:
    st.markdown(make_card("❌", "Failed", str(failed), f"{fail_pct}% unresolved", "red", fail_pct, "#ef4444"), unsafe_allow_html=True)
with c3:
    st.markdown(make_card("🔧", "Repair Success", f"{repair_success}/{repair_attempted}", f"{repair_pct}% fixed by LLM", "purple", repair_pct, "#8b5cf6"), unsafe_allow_html=True)
with c4:
    st.markdown(make_card("⏱️", "Avg Duration", f"{avg_duration:.2f}s", "per test execution", "amber"), unsafe_allow_html=True)
with c5:
    st.markdown(make_card("🎯", "Edge Score", f"{avg_edge:.0%}", f"across {len(edge_items)} tests", "blue", edge_pct, "#3b82f6"), unsafe_allow_html=True)


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
    st.markdown(f'<div class="tip">🏆 <strong>Best strategy:</strong> {best_strategy}<br><span style="font-size:1.3rem;font-weight:800">{best_pct}%</span> pass rate</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="tip amber">🎯 <strong>Best edge coverage:</strong> {best_edge_strat}<br><span style="font-size:1.3rem;font-weight:800">{best_edge_avg:.0%}</span> avg score</div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="tip red">⚠️ <strong>Top error type:</strong> {top_error}<br><span style="font-size:1.3rem;font-weight:800">{error_cats.get(top_error, 0)}</span> occurrences</div>', unsafe_allow_html=True)


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
    # Add pass-rate % annotation on top of each group
    for s in strat_names:
        pct_s = strat_stats[s]["passed"] * 100 // max(strat_stats[s]["total"], 1)
        fig.add_annotation(x=s, y=strat_stats[s]["total"] + 1.5,
                           text=f"<b>{pct_s}% pass</b>", showarrow=False,
                           font=dict(size=11, color="#334155"))
    fig.update_layout(**chart_style(
        title="Pass / Repair / Fail by Strategy",
        barmode="group", height=440,
        legend=dict(orientation="h", y=-0.15),
        yaxis=dict(gridcolor="#f1f5f9", title="Test Count"),
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

# Scale height with number of functions so rows are readable
num_funcs = len({r.get("function_name") for r in filtered})
heatmap_height = max(500, 120 + num_funcs * 28)

# Font size for cell labels: shrinks as dataset grows, but always visible
cell_font = max(8, 13 - max(0, num_funcs - 10))

# y-axis label font also scales down for large datasets
y_font_size = max(9, 14 - max(0, num_funcs - 15))

# --- Heatmap 1: Function × Strategy outcome (full width) ---
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
    label_matrix = [["Pass" if v == 2 else "Repair" if v == 1 else "Fail" for v in row] for row in df_heat.values]

    fig = go.Figure(go.Heatmap(
        z=df_heat.values,
        x=df_heat.columns.tolist(),
        y=df_heat.index.tolist(),
        # Green=Pass, Purple=Repair, Red=Fail
        colorscale=[[0, "#fca5a5"], [0.5, "#c4b5fd"], [1, "#6ee7b7"]],
        text=label_matrix,          # always show text
        texttemplate="%{text}",
        textfont=dict(size=cell_font, color="#1e293b"),
        zmin=0, zmax=2,
        showscale=True,
        colorbar=dict(
            tickvals=[0.33, 1.0, 1.67],
            ticktext=["❌ Fail", "🔧 Repair", "✅ Pass"],
            title=dict(text="Outcome", side="top"),
            thickness=16, len=0.5, x=1.01,
        ),
    ))
    fig.update_layout(**chart_style(
        title=f"Function × Strategy Outcome  ({num_funcs} functions × {len(df_heat.columns)} strategies)",
        height=heatmap_height,
        yaxis=dict(automargin=True, tickfont=dict(size=y_font_size), gridcolor="#f1f5f9"),
        xaxis=dict(tickfont=dict(size=12), side="top", gridcolor="#f1f5f9"),
        margin=dict(l=200, r=100, t=90, b=20),
    ))
    st.plotly_chart(fig, width='stretch')

    # Color legend row below the heatmap for quick reference
    leg1, leg2, leg3, _ = st.columns([1, 1, 1, 4])
    with leg1:
        st.markdown("<div style='background:#6ee7b7;border-radius:6px;padding:6px 12px;text-align:center;font-weight:700;color:#065f46;font-size:0.85rem'>✅ Pass</div>", unsafe_allow_html=True)
    with leg2:
        st.markdown("<div style='background:#c4b5fd;border-radius:6px;padding:6px 12px;text-align:center;font-weight:700;color:#4c1d95;font-size:0.85rem'>🔧 Repair</div>", unsafe_allow_html=True)
    with leg3:
        st.markdown("<div style='background:#fca5a5;border-radius:6px;padding:6px 12px;text-align:center;font-weight:700;color:#7f1d1d;font-size:0.85rem'>❌ Fail</div>", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# --- Heatmap 2: Edge-case coverage per function (full width) ---
if edge_items:
    edge_heat = {}
    for item in edge_items:
        fn = item.get("function_name", "?")
        for cat, hit in item.get("covered", {}).items():
            edge_heat.setdefault(fn, {})[cat] = edge_heat.get(fn, {}).get(cat, 0) + (1 if hit else 0)

    df_edge = pd.DataFrame(edge_heat).T.fillna(0)
    # Normalize: 0-1 scale per strategy count
    df_edge = df_edge / max(len(all_strategies), 1)

    num_cats = len(df_edge.columns)
    edge_height = max(420, 80 + len(df_edge) * 22)
    show_edge_text = len(df_edge) <= 20 and num_cats <= 12

    fig = go.Figure(go.Heatmap(
        z=df_edge.values,
        x=df_edge.columns.tolist(),
        y=df_edge.index.tolist(),
        colorscale="YlGnBu",
        zmin=0, zmax=1,
        text=np.round(df_edge.values, 2) if show_edge_text else None,
        texttemplate="%{text:.0%}" if show_edge_text else "",
        textfont=dict(size=9),
        colorbar=dict(title="Coverage", thickness=12, len=0.6),
    ))
    fig.update_layout(**chart_style(
        title=f"Edge-Case Coverage by Function ({len(df_edge)} functions × {num_cats} categories)",
        height=edge_height,
        yaxis=dict(gridcolor="#f1f5f9", automargin=True, tickfont=dict(size=y_font_size)),
        xaxis=dict(gridcolor="#f1f5f9", tickangle=35, tickfont=dict(size=11), automargin=True),
        margin=dict(l=180, r=40, t=80, b=80),
    ))
    st.plotly_chart(fig, width='stretch')


# --- Code viewer ---

st.markdown('<div class="section-title">🔍 Code Viewer</div>', unsafe_allow_html=True)

# Build a lookup: (function_name, strategy) -> generated code
gen_lookup = {}
if gen_data:
    for g in gen_data:
        key = (g.get("method_name", ""), g.get("prompt_strategy", ""))
        gen_lookup[key] = g.get("generated_test", "")

# Controls: search box + show-only-failures toggle
cv_col1, cv_col2 = st.columns([3, 1])
with cv_col1:
    search_fn = st.text_input("🔎 Filter by function name", placeholder="e.g. compute", label_visibility="collapsed")
with cv_col2:
    show_failed_only = st.toggle("Failures only", False)

# Filter the list to show
viewer_results = [
    r for r in filtered
    if (not search_fn or search_fn.lower() in r.get("function_name", "").lower())
    and (not show_failed_only or not r.get("passed"))
][:30]  # cap at 30 to keep page fast

if not viewer_results:
    st.info("No tests match the current filter.")
else:
    # Group by function name so each function gets one expander with strategy tabs
    from itertools import groupby
    viewer_by_fn = defaultdict(list)
    for r in viewer_results:
        viewer_by_fn[r.get("function_name", "?")].append(r)

    for fn, fn_results in viewer_by_fn.items():
        # Pick a status summary for the expander label
        n_pass = sum(1 for r in fn_results if r.get("passed"))
        n_total = len(fn_results)
        status_icon = "✅" if n_pass == n_total else ("⚠️" if n_pass > 0 else "❌")
        label = f"{status_icon} {fn}  —  {n_pass}/{n_total} passed"

        with st.expander(label, expanded=False):
            tab_names = [r.get("prompt_strategy", "?") for r in fn_results]
            tabs = st.tabs(tab_names)

            for tab, r in zip(tabs, fn_results):
                with tab:
                    passed_badge = "<span style='color:#10b981;font-weight:700'>✅ PASSED</span>" if r.get("passed") else "<span style='color:#ef4444;font-weight:700'>❌ FAILED</span>"
                    repair_note = " <span style='color:#8b5cf6'>(repaired by LLM)</span>" if r.get("repair_success") else ""
                    st.markdown(f"**Status:** {passed_badge}{repair_note} &nbsp;|&nbsp; **Duration:** {r.get('duration_sec',0):.2f}s &nbsp;|&nbsp; **Error:** {r.get('error_category','—')}", unsafe_allow_html=True)

                    left, right = st.columns(2)
                    with left:
                        st.caption("📝 Generated Test")
                        original = gen_lookup.get((fn, r.get("prompt_strategy","")), "")
                        st.code(original[:2000] or "No code stored", language="python")
                    with right:
                        if r.get("repair_success") and r.get("repaired_test_code"):
                            st.caption("🔧 Repaired Test")
                            st.code(r["repaired_test_code"][:2000], language="python")
                        else:
                            st.caption("📋 Pytest Output")
                            st.code(r.get("pytest_output_tail", "No output")[:1500], language="text")


# --- Detailed results table ---

st.markdown('<div class="section-title">📋 Detailed Results</div>', unsafe_allow_html=True)

# Summary counts above table
tab_all, tab_pass, tab_fail = st.tabs([f"All ({len(filtered)})", f"✅ Passed ({sum(1 for r in filtered if r.get('passed'))})", f"❌ Failed ({sum(1 for r in filtered if not r.get('passed'))})"])

def build_table(subset):
    rows = []
    for r in subset:
        rows.append({
            "Function": r.get("function_name", "?"),
            "Strategy": r.get("prompt_strategy", "?").replace("_", " "),
            "Status": "✅ Pass" if r.get("passed") else "❌ Fail",
            "Error Category": r.get("error_category", "—"),
            "Duration (s)": round(r.get("duration_sec", 0), 3),
            "Repaired": "Yes ✅" if r.get("repair_success") else ("Attempted" if r.get("repair_attempted") else "No"),
        })
    return pd.DataFrame(rows)

with tab_all:
    df_all = build_table(filtered)
    st.dataframe(df_all, width='stretch', hide_index=True, height=380)
    csv = df_all.to_csv(index=False)
    st.download_button("📥 Export CSV", csv, "llm_test_results.csv", "text/csv", use_container_width=True)

with tab_pass:
    df_p = build_table([r for r in filtered if r.get("passed")])
    st.dataframe(df_p, width='stretch', hide_index=True, height=380)

with tab_fail:
    df_f = build_table([r for r in filtered if not r.get("passed")])
    st.dataframe(df_f, width='stretch', hide_index=True, height=380)


# --- Footer ---

st.markdown("""
---
<div style="text-align: center; color: #94a3b8; padding: 1rem; font-size: 0.9rem;">
    <strong>🧬 LLM Test Generator</strong> · Ollama + Llama3 + Pytest + Streamlit<br>
    Execution-grounded evaluation with self-repair · May 2026
</div>
""", unsafe_allow_html=True)