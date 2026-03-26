"""
Interactive Web Server for LLM Planning Agent using Gradio

Run with: python app.py
Or: gradio app.py
"""

import sys
from pathlib import Path
import os
import json
from typing import Optional, Tuple, List, Dict
import time

# Add parent directory to path to import modules
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent

if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv(parent_dir / ".env")
except ImportError:
    pass

# Import the planning agent module
try:
    from agent import LLMPlanningAgent, AnalysisPlan, PlanStep, LLMClient, PROVIDERS, load_database
except ImportError as e:
    print(f"Import Error: {str(e)}")
    print(f"Make sure you're running from the interactive_web_server directory")
    print(f"Parent directory: {parent_dir}")
    sys.exit(1)

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gradio as gr
from datetime import datetime
from pathlib import Path
import re
import tempfile

# ============================================================
# Nature Journal Style Configuration
# ============================================================

NATURE_COLORS = ['#2171B5', '#6BAED6', '#238B45', '#CB181D', '#FE9929', '#756BB1', '#D94701', '#636363']

NATURE_PRIMARY = '#2171B5'
NATURE_SECONDARY = '#6BAED6'
NATURE_RED = '#CB181D'
NATURE_GREEN = '#238B45'
NATURE_AMBER = '#FE9929'
NATURE_GRAY = '#636363'

# Plotly layout template matching Nature Journal style
PLOTLY_LAYOUT = dict(
    font=dict(family="Arial", size=12, color="#333"),
    plot_bgcolor="white",
    paper_bgcolor="white",
    margin=dict(l=60, r=20, t=50, b=40),
)

def _apply_nature_axes(fig):
    """Apply Nature-style axis formatting to a Plotly figure."""
    fig.update_xaxes(showgrid=False, showline=True, linewidth=0.8, linecolor="#333",
                     ticks="outside", tickwidth=0.8, ticklen=4)
    fig.update_yaxes(showgrid=False, showline=True, linewidth=0.8, linecolor="#333",
                     ticks="outside", tickwidth=0.8, ticklen=4)
    fig.update_layout(**PLOTLY_LAYOUT)
    return fig

# ============================================================
# Example Queries (Agent tab)
# ============================================================

PRERUN_EXAMPLES = [
    ("Vemurafenib-BRAF Analysis (pre-run)", "example_results/vemurafenib_braf.json"),
    ("EGFR Target Landscape (pre-run)", "example_results/egfr_landscape.json"),
]

EXAMPLE_QUERIES = [
    ("Vemurafenib-BRAF Evidence", "How strong is the evidence that vemurafenib binds to BRAF, and does real-world clinical data support this interaction?"),
    ("Cetirizine-BRAF Interaction", "Is there any evidence that cetirizine interacts with BRAF? What do binding assays, drug response screens, and EHR records show?"),
    ("Erlotinib Repurposing", "Could erlotinib be repurposed for diseases beyond its current indications? What does its binding profile and selectivity suggest?"),
    ("EGFR Target Landscape", "Which drugs most potently target EGFR, and how does EGFR rank among druggable oncology targets?"),
    ("BRAF Melanoma Therapies", "What therapeutic options exist for melanoma patients through BRAF-targeted drugs, and how do they compare in clinical evidence?"),
    ("Database Overview", "What data sources and how many records does this database contain?"),
    ("BRAF Target Profile", "Give me a complete profile of BRAF -- what drugs target it, what diseases is it linked to, and is it an oncogene?"),
]

# Database Explorer examples: (label, field_values...)
BINDING_EXAMPLES = [
    ("BRAF", "BRAF", "", ""),
    ("EGFR", "EGFR", "", ""),
    ("BRAF + Vemurafenib", "BRAF", "CHEMBL1229517", ""),
    ("EGFR + Erlotinib", "EGFR", "CHEMBL553", "7.0"),
]

SELECTIVITY_EXAMPLES = [
    ("Vemurafenib", "CHEMBL1229517", "All"),
    ("Erlotinib", "CHEMBL553", "All"),
    ("Highly Selective", "", "Highly Selective"),
    ("Broad-spectrum", "", "Broad-spectrum"),
]

EHR_EXAMPLES = [
    ("CHEMBL716", "CHEMBL716", "", "", "", "Both"),
    ("Aspirin", "", "aspirin", "", "", "Both"),
    ("Prostate Cancer (C61)", "", "", "C61", "", "Both"),
    ("Melanoma (MS)", "", "", "", "melanoma", "Mount Sinai"),
]

# ============================================================
# Provider / Model Map
# ============================================================

PROVIDER_MAP = {
    "OpenAI": ("openai", PROVIDERS["openai"]["models"]),
    "Google Gemini": ("gemini", PROVIDERS["gemini"]["models"]),
    "Anthropic Claude": ("claude", PROVIDERS["claude"]["models"]),
}

# ============================================================
# Global State
# ============================================================

# Database loads at startup — no API key needed
print("Loading database...")
db = load_database(str(parent_dir / "Database"), load_full_data=True)
print(f"Database loaded: {len(db.dfs)} datasets")

planning_agent: Optional[LLMPlanningAgent] = None
current_plan: Optional[AnalysisPlan] = None
execution_history = []

# ============================================================
# Utility Functions
# ============================================================


def _not_initialized():
    return "<p style='color: #CB181D; font-family: Arial;'>Please click <strong>Initialize Agent</strong> first.</p>"


def _nature_card(title, content, color=NATURE_PRIMARY):
    """Generate a Nature-style HTML card."""
    return (f"<div style='font-family: Arial, sans-serif; background: #fff; "
            f"border: 1px solid #e0e0e0; border-left: 3px solid {color}; "
            f"padding: 16px; border-radius: 4px; margin: 8px 0;'>"
            f"<h4 style='margin: 0 0 8px 0; color: #333;'>{title}</h4>"
            f"{content}</div>")


def _nature_stat_card(title, value, color=NATURE_PRIMARY):
    """Generate a Nature-style statistic card."""
    return (f"<div style='font-family: Arial, sans-serif; background: linear-gradient(135deg, {color}11, {color}08); "
            f"border-left: 3px solid {color}; padding: 14px; border-radius: 4px;'>"
            f"<div style='font-size: 0.82em; color: #666; margin-bottom: 4px;'>{title}</div>"
            f"<div style='font-size: 1.5em; font-weight: bold; color: {color};'>{value}</div></div>")


def _linkify_cell(col, val):
    """Add external database links to known ID columns."""
    s = str(val)
    if col in ('drugId', 'Drug') and s.startswith('CHEMBL'):
        return f"<a href='https://www.ebi.ac.uk/chembl/compound_report_card/{s}' target='_blank' style='color:{NATURE_PRIMARY};'>{s}</a>"
    if col == 'Gene' and s and s != 'nan':
        return f"<a href='https://www.uniprot.org/uniprotkb?query=gene:{s}+AND+organism_id:9606' target='_blank' style='color:{NATURE_PRIMARY};'>{s}</a>"
    if col in ('ICD10', 'icd_code') and s and s != 'nan':
        return f"<a href='https://icd.who.int/browse10/2019/en#/{s}' target='_blank' style='color:{NATURE_PRIMARY};'>{s}</a>"
    return s


def _nature_table_html(df, max_rows=50):
    """Convert a DataFrame to a Nature-style HTML table with links and scrolling."""
    if df is None or df.empty:
        return "<p style='font-family: Arial; color: #666;'>No data available.</p>"
    display_df = df.head(max_rows)
    html = "<div style='max-height: 500px; overflow-y: auto; overflow-x: auto; border: 1px solid #e0e0e0; border-radius: 4px;'>"
    html += "<table style='font-family: Arial, sans-serif; border-collapse: collapse; width: 100%; font-size: 11px;'>"
    html += "<thead><tr style='border-bottom: 2px solid #333; position: sticky; top: 0; z-index: 1;'>"
    for col in display_df.columns:
        html += f"<th style='padding: 8px 12px; text-align: left; font-weight: 600; color: #333; background: #f5f5f5;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for i, (_, row) in enumerate(display_df.iterrows()):
        bg = "#fafafa" if i % 2 == 0 else "#fff"
        html += f"<tr style='background: {bg}; border-bottom: 1px solid #e0e0e0;'>"
        for col, val in zip(display_df.columns, row):
            if isinstance(val, float):
                cell = f"{val:.4f}"
            else:
                cell = _linkify_cell(col, val)
            if len(cell) > 200:
                cell = cell[:197] + "..."
            html += f"<td style='padding: 6px 12px; color: #333; white-space: nowrap;'>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    if len(df) > max_rows:
        html += f"<p style='font-size: 10px; color: #999; margin-top: 4px;'>Showing {max_rows} of {len(df)} rows</p>"
    return html


# ============================================================
# Download Utilities
# ============================================================

# Module-level state to hold last results for download
_last_results = {}


def _save_plotly_image(fig, fmt="png"):
    """Save a Plotly figure to a temp file and return the path."""
    if fig is None:
        return None
    suffix = f".{fmt}"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, prefix="linkd_")
    fig.write_image(tmp.name, format=fmt, width=1200, height=800, scale=2)
    return tmp.name


def _save_csv(df, name="results"):
    """Save a DataFrame to a temp CSV and return the path."""
    if df is None or (hasattr(df, 'empty') and df.empty):
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, prefix=f"linkd_{name}_")
    df.to_csv(tmp.name, index=False)
    return tmp.name


def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML for proper display."""
    if not markdown_text:
        return ""
    lines = markdown_text.split('\n')
    html_lines = []
    in_ordered_list = False
    in_unordered_list = False
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if not line_stripped:
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            html_lines.append('<br>')
            continue
        if re.match(r'^## (.+)$', line_stripped):
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            header_text = re.match(r'^## (.+)$', line_stripped).group(1)
            html_lines.append(f'<h2 style="margin-top: 15px; margin-bottom: 10px; color: #2171B5; font-weight: bold;">{header_text}</h2>')
        elif re.match(r'^### (.+)$', line_stripped):
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            header_text = re.match(r'^### (.+)$', line_stripped).group(1)
            html_lines.append(f'<h3 style="margin-top: 12px; margin-bottom: 8px; color: #2171B5; font-weight: bold;">{header_text}</h3>')
        numbered_pattern = r'^(\s*)(\*\*)?(\d+)[\.\)]\s*(.+?)(\*\*)?$'
        numbered_match = re.match(numbered_pattern, line_stripped)
        if numbered_match:
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            para_text = numbered_match.group(4).strip().rstrip('*')
            para_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', para_text)
            para_text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', para_text)
            html_lines.append(f'<p style="margin-bottom: 10px; line-height: 1.6;">{para_text}</p>')
            continue
        elif re.match(r'^[-*]\s+(.+)$', line_stripped):
            if not in_unordered_list:
                if in_ordered_list:
                    html_lines.append('</ol>')
                    in_ordered_list = False
                html_lines.append('<ul style="margin-left: 20px; margin-top: 8px; margin-bottom: 8px;">')
                in_unordered_list = True
            list_content = re.match(r'^[-*]\s+(.+)$', line_stripped).group(1)
            list_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', list_content)
            html_lines.append(f'<li style="margin-bottom: 5px; line-height: 1.6;">{list_content}</li>')
        else:
            if in_ordered_list:
                html_lines.append('</ol>')
                in_ordered_list = False
            if in_unordered_list:
                html_lines.append('</ul>')
                in_unordered_list = False
            para_text = line
            if re.search(r'^\s*(\*\*)?\s*(\d+)[\.\)]\s+', para_text.strip()):
                para_text = re.sub(r'^\s*(\*\*)?\s*(\d+)[\.\)]\s+', '', para_text.strip())
            para_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', para_text)
            para_text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', para_text)
            if para_text.strip() and not para_text.strip().startswith('<'):
                html_lines.append(f'<p style="margin-bottom: 10px; line-height: 1.6;">{para_text}</p>')
            elif para_text.strip():
                html_lines.append(para_text)
    if in_ordered_list:
        html_lines.append('</ol>')
    if in_unordered_list:
        html_lines.append('</ul>')
    html = '\n'.join(html_lines)
    html = re.sub(r'<p>\s*</p>', '', html)
    html = re.sub(r'<p>(<h[2-4])', r'\1', html)
    html = re.sub(r'(</h[2-4]>)\s*</p>', r'\1', html)
    html = re.sub(r'<br>\s*<br>\s*<br>', '<br><br>', html)
    return html


# ============================================================
# Agent Tab Functions (preserved from original)
# ============================================================


def initialize_agent(provider_name: str, model_name: str, api_key: str):
    """Initialize the planning agent with selected LLM provider."""
    global planning_agent

    # Try UI key first, then .env
    key = api_key.strip() if api_key else ""
    if not key:
        provider_key, _ = PROVIDER_MAP.get(provider_name, ("openai", []))
        env_var = PROVIDERS[provider_key]["env_key"]
        key = os.getenv(env_var, "")

    if not key:
        return f"Please enter an API key for {provider_name} (or set {PROVIDERS[PROVIDER_MAP[provider_name][0]]['env_key']} in .env)."

    provider_key, _ = PROVIDER_MAP[provider_name]
    try:
        llm_client = LLMClient(provider=provider_key, api_key=key, model=model_name)
        planning_agent = LLMPlanningAgent(
            llm_client=llm_client,
            db=db,
        )
        return f"Agent initialized with {provider_name} / {model_name}. Ready."
    except Exception as e:
        return f"Error: {str(e)}"





# ============================================================
# Database-Only Examples (no API key needed)
# ============================================================


def load_prerun_example(filepath):
    """Load a pre-run LLM example result from JSON file."""
    try:
        with open(Path(__file__).parent / filepath) as f:
            data = json.load(f)
        return (data.get("query", ""),
                "Pre-run example loaded.",
                data.get("plan_html", ""),
                data.get("execution_status", ""),
                data.get("results_html", ""))
    except Exception as e:
        return ("", f"Error loading example: {e}", "", "", "")


def generate_plan(query: str):
    """Generate an analysis plan from a query."""
    global planning_agent, current_plan
    if not planning_agent:
        return "Please initialize the agent first.", "", gr.Button("Generate Plan", variant="primary"), gr.Button("Execute Plan", variant="secondary", interactive=False)
    if not query.strip():
        return "Please enter a query.", "", gr.Button("Generate Plan", variant="primary"), gr.Button("Execute Plan", variant="secondary", interactive=False)
    try:
        start_time = time.time()
        plan = planning_agent.generate_plan(query)
        elapsed_time = time.time() - start_time
        current_plan = plan
        plan_html = f"<h3 style='font-family: Arial;'>Generated Analysis Plan</h3>"
        plan_html += f"<p style='font-family: Arial;'><strong>Query:</strong> {query}</p>"
        plan_html += f"<p style='font-family: Arial;'><strong>Total Steps:</strong> {len(plan.steps)}</p><hr>"
        plan_html += "<ol style='font-family: Arial;'>"
        for step in plan.steps:
            plan_html += f"<li style='margin: 10px 0; padding: 10px; border-left: 3px solid {NATURE_PRIMARY}; background-color: #f8f9fa;'>"
            plan_html += f"<p><strong>{step.description}</strong> <em style='color: #666;'>(Sources: {', '.join(step.data_sources)})</em></p>"
            plan_html += f"</li>"
        plan_html += "</ol>"
        time_str = f"{elapsed_time:.2f}s" if elapsed_time < 60 else f"{elapsed_time/60:.1f}m"
        return (
            f"Generated plan with {len(plan.steps)} steps (Time: {time_str})",
            plan_html,
            gr.Button("Generate Plan", variant="secondary", interactive=True),
            gr.Button("Execute Plan", variant="primary", interactive=True)
        )
    except Exception as e:
        return f"Error: {str(e)}", "", gr.Button("Generate Plan", variant="primary"), gr.Button("Execute Plan", variant="secondary", interactive=False)


def format_results_summary(plan: AnalysisPlan) -> str:
    """Format execution results as bullet points."""
    summary_html = "<h3 style='font-family: Arial;'>Analysis Results Summary</h3>"
    summary_html += "<div style='font-family: Arial; padding: 15px; background-color: #f8f9fa; border-radius: 4px;'>"
    key_findings = []
    for step in plan.steps:
        if step.status == "completed" and step.result:
            step_summary = f"<li style='margin: 15px 0;'><strong>{step.description}</strong>"
            findings = []
            for key, value in step.result.items():
                if isinstance(value, dict):
                    if "count" in value:
                        findings.append(f"Found {value['count']} records")
                        if "avg_auc_corr" in value and value["avg_auc_corr"]:
                            findings.append(f"Average AUC correlation: {value['avg_auc_corr']:.4f}")
                        if "avg_ic50_corr" in value and value["avg_ic50_corr"]:
                            findings.append(f"Average IC50 correlation: {value['avg_ic50_corr']:.4f}")
                    elif "overall_strength" in value:
                        findings.append(f"Evidence strength: {value['overall_strength'].upper()}")
                        if "sources" in value:
                            sources_found = [s for s, d in value["sources"].items() if d.get("found")]
                            if sources_found:
                                findings.append(f"Evidence from: {', '.join([s.replace('_', ' ').title() for s in sources_found])}")
                    elif "mount_sinai" in value or "uk_biobank" in value:
                        total = value.get("count", 0)
                        if total > 0:
                            findings.append(f"EHR associations: {total} total (Mount Sinai: {value.get('mount_sinai', 0)}, UK Biobank: {value.get('uk_biobank', 0)})")
                    elif "Selectivity_Score" in value:
                        findings.append(f"Selectivity Score: {value.get('Selectivity_Score', 0):.4f}")
                    elif "Avg_pKd" in value:
                        findings.append(f"Target binding: Avg pKd = {value.get('Avg_pKd', 0):.2f}, {value.get('N_hit', 0):,.0f} drug hits")
            if findings:
                step_summary += "<br>"
                for finding in findings:
                    step_summary += f"<p style='margin: 4px 0 4px 20px; color: #555;'>{finding}</p>"
            step_summary += "</li>"
            key_findings.append(step_summary)
        elif step.status == "failed":
            key_findings.append(f"<li style='margin: 15px 0; color: {NATURE_RED};'><strong>{step.description}</strong><p>Failed: {step.error}</p></li>")
    if key_findings:
        summary_html += "<ul style='list-style-type: none; padding-left: 0;'>" + "".join(key_findings) + "</ul>"
    else:
        summary_html += "<p>No results available.</p>"
    summary_html += "</div>"
    return summary_html


def execute_plan(progress=gr.Progress()):
    """Execute the current plan with real-time status updates."""
    global planning_agent, current_plan, execution_history
    if not planning_agent:
        yield "Please initialize the agent first.", ""
        return
    if not current_plan:
        yield "Please generate a plan first.", ""
        return
    try:
        plan = current_plan
        execution_start_time = time.time()
        completed = 0
        processing_details = []
        status_updates = []
        step_times = []
        status_text = f"Executing plan: {len(plan.steps)} steps total\n"
        yield status_text, "<div style='font-family: Arial; padding: 10px;'><p>Starting execution...</p></div>"

        for i, step in enumerate(plan.steps):
            if step.status == "pending":
                step_start_time = time.time()
                if progress:
                    progress((i / len(plan.steps)), desc=f"Step {step.step_number}/{len(plan.steps)}: {step.description[:50]}...")
                processing_details.append(f"Executing Step {step.step_number}: {step.description}")
                status_updates.append(f"<li style='margin: 5px 0; padding: 5px; background: #FFF8E1; border-left: 3px solid {NATURE_AMBER};'>Step {step.step_number}: {step.description[:60]}... (In Progress)</li>")
                real_elapsed = time.time() - execution_start_time
                elapsed_str = f"{max(real_elapsed, 0.1):.1f}s" if real_elapsed < 60 else f"{real_elapsed/60:.1f}m"
                status_text = f"Step {step.step_number}/{len(plan.steps)}: {step.description[:60]}...\nCompleted: {completed}/{len(plan.steps)} | Time: {elapsed_str}"
                current_html = _build_status_html(status_updates, completed, len(plan.steps), elapsed_str)
                yield status_text, current_html

                step = planning_agent.execute_step(step, plan.query)
                step_duration = time.time() - step_start_time
                step_times.append(step_duration)
                total_elapsed = time.time() - execution_start_time
                total_str = f"{total_elapsed:.1f}s" if total_elapsed < 60 else f"{total_elapsed/60:.1f}m"
                step_str = f"{step_duration:.1f}s" if step_duration < 60 else f"{step_duration/60:.1f}m"

                if step.status == "completed":
                    completed += 1
                    processing_details[-1] = f"Completed Step {step.step_number}: {step.description} ({step_str})"
                    status_updates[-1] = f"<li style='margin: 5px 0; padding: 5px; background: #E8F5E9; border-left: 3px solid {NATURE_GREEN};'>Step {step.step_number}: {step.description[:60]}... ({step_str})</li>"
                elif step.status == "failed":
                    processing_details[-1] = f"Failed Step {step.step_number}: {step.description} ({step.error})"
                    status_updates[-1] = f"<li style='margin: 5px 0; padding: 5px; background: #FFEBEE; border-left: 3px solid {NATURE_RED};'>Step {step.step_number}: {step.description[:60]}... (Failed: {step.error[:50]})</li>"

                status_text = f"Progress: {completed}/{len(plan.steps)} completed | Time: {total_str}"
                current_html = _build_status_html(status_updates, completed, len(plan.steps), total_str)
                yield status_text, current_html

        # Generate summary
        if progress:
            progress(0.9, desc="Generating analysis summary...")
        summary_elapsed = time.time() - execution_start_time
        summary_str = f"{summary_elapsed:.1f}s" if summary_elapsed < 60 else f"{summary_elapsed/60:.1f}m"
        status_updates.append(f"<li style='margin: 5px 0; padding: 5px; background: #FFF8E1; border-left: 3px solid {NATURE_AMBER};'>Generating summary...</li>")
        yield f"Generating summary... | Time: {summary_str}", _build_status_html(status_updates, completed, len(plan.steps), summary_str)

        plan.summary = planning_agent._generate_summary(plan)
        plan.overall_status = "completed"
        total_time = time.time() - execution_start_time
        total_time_str = f"{total_time:.1f}s" if total_time < 60 else f"{total_time/60:.1f}m"
        summary_dur = total_time - summary_elapsed
        summary_dur_str = f"{summary_dur:.1f}s" if summary_dur < 60 else f"{summary_dur/60:.1f}m"
        processing_details.append(f"Summary generated ({summary_dur_str})")
        status_updates[-1] = f"<li style='margin: 5px 0; padding: 5px; background: #E8F5E9; border-left: 3px solid {NATURE_GREEN};'>Summary generated ({summary_dur_str})</li>"

        if progress:
            progress(1.0, desc="Complete!")
        status_text = f"All steps completed! | Total: {total_time_str}"
        status_html = _build_status_html(status_updates, completed, len(plan.steps), total_time_str, done=True)
        results_summary = format_results_summary(plan)
        llm_summary_html = ""
        if plan.summary:
            llm_summary_html = f"<h3 style='font-family: Arial;'>Analysis Summary</h3>"
            llm_summary_html += f"<div style='font-family: Arial; padding: 15px; background: #E3F2FD; border-radius: 4px; margin-top: 20px; line-height: 1.8;'>"
            llm_summary_html += convert_markdown_to_html(plan.summary)
            llm_summary_html += "</div>"
        avg_step = sum(step_times) / len(step_times) if step_times else 0
        avg_str = f"{avg_step:.1f}s" if avg_step < 60 else f"{avg_step/60:.1f}m"
        processing_html = f"<div style='font-family: Arial; margin: 10px 0; padding: 10px; background: #FFF8E1; border-left: 3px solid {NATURE_AMBER}; border-radius: 4px;'>"
        processing_html += f"<p><strong>Processing Details:</strong> Total: {total_time_str} | Avg per step: {avg_str}</p>"
        processing_html += "<ul>" + "".join([f"<li>{d}</li>" for d in processing_details]) + "</ul></div>"
        final_results = status_html + "<hr>" + processing_html + "<hr>" + results_summary + llm_summary_html
        execution_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": plan.query,
            "steps": len(plan.steps),
            "completed": completed
        })
        yield status_text, final_results
    except Exception as e:
        import traceback
        yield f"Error: {str(e)}\n\n{traceback.format_exc()}", ""


def _build_status_html(updates, completed, total, elapsed_str, done=False):
    color = NATURE_GREEN if done else NATURE_PRIMARY
    html = f"<div style='font-family: Arial; padding: 10px; background: #f8f9fa; border-radius: 4px; margin-bottom: 15px;'>"
    html += "<h4>Execution Status</h4>"
    html += "<ul style='list-style-type: none; padding-left: 0;'>" + "".join(updates) + "</ul>"
    prefix = "Done: " if done else "Progress: "
    html += f"<p style='margin-top: 10px; font-weight: bold; color: {color};'>{prefix}{completed}/{total} steps | Time: {elapsed_str}</p>"
    html += "</div>"
    return html


def load_example(example_index: int) -> str:
    if 0 <= example_index < len(EXAMPLE_QUERIES):
        return EXAMPLE_QUERIES[example_index][1]
    return ""


def get_history() -> str:
    if not execution_history:
        return "<p style='font-family: Arial;'>No execution history yet.</p>"
    html = "<h3 style='font-family: Arial;'>Execution History</h3><ul style='font-family: Arial;'>"
    for i, item in enumerate(reversed(execution_history[-10:]), 1):
        html += f"<li style='margin: 10px 0;'><strong>Query {i}:</strong> {item['query'][:60]}...<br>"
        html += f"<small>Time: {item['timestamp']} | Steps: {item['steps']} | Completed: {item['completed']}</small></li>"
    html += "</ul>"
    return html


# ============================================================
# Database Explorer: Overview Functions
# ============================================================


def _build_overview():
    """Build overview HTML and Plotly figure. Called once at startup."""
    stats = db.get_statistics()
    db_info = db.get_database_info()

    # Stats cards
    cards = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 15px 0;'>"
    if "drugs" in stats:
        cards += _nature_stat_card("Unique Drugs", f"{stats['drugs']['unique_drugs']:,}", NATURE_GREEN)
        cards += _nature_stat_card("Unique Targets", f"{stats['drugs']['unique_targets']:,}", NATURE_PRIMARY)
        cards += _nature_stat_card("Unique Diseases", f"{stats['drugs']['unique_diseases']:,}", NATURE_RED)
        cards += _nature_stat_card("Drug-Target-Disease", f"{stats['drugs']['total_records']:,}", '#756BB1')
    if "ehr_mount_sinai" in stats:
        cards += _nature_stat_card("EHR Mount Sinai", f"{stats['ehr_mount_sinai']['total_records']:,}", NATURE_AMBER)
    if "ehr_uk_biobank" in stats:
        cards += _nature_stat_card("EHR UK Biobank", f"{stats['ehr_uk_biobank']['total_records']:,}", '#D94701')
    if "drug_response" in stats:
        cards += _nature_stat_card("Drug Response", f"{stats['drug_response']['total_records']:,}", '#1B9E77')
    if "causal_associations" in stats:
        cards += _nature_stat_card("Causal Gene-Disease", f"{stats['causal_associations']['total_records']:,}", NATURE_GRAY)
    cards += "</div>"

    # Data source table
    table = "<h4 style='font-family: Arial;'>Loaded Data Sources</h4>"
    table += "<div style='max-height: 300px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 4px;'>"
    table += "<table style='font-family: Arial; border-collapse: collapse; width: 100%; font-size: 11px;'>"
    table += "<thead><tr style='border-bottom: 2px solid #333;'>"
    table += "<th style='padding: 8px 12px; text-align: left; font-weight: 600; background: #f5f5f5;'>Dataset</th>"
    table += "<th style='padding: 8px 12px; text-align: right; font-weight: 600; background: #f5f5f5;'>Rows</th>"
    table += "<th style='padding: 8px 12px; text-align: right; font-weight: 600; background: #f5f5f5;'>Columns</th></tr></thead><tbody>"
    for name, info in sorted(db_info.items()):
        table += f"<tr style='border-bottom: 1px solid #e0e0e0;'>"
        table += f"<td style='padding: 6px 12px;'>{name}</td>"
        table += f"<td style='padding: 6px 12px; text-align: right;'>{info['rows']:,}</td>"
        table += f"<td style='padding: 6px 12px; text-align: right;'>{info['column_count']}</td></tr>"
    table += "</tbody></table></div>"
    combined_html = cards + table

    # Plotly 2x2 overview chart
    fig = make_subplots(rows=2, cols=2,
        subplot_titles=["a) Records per Data Source", "b) Clinical Trial Phases",
                        "c) Top 10 Most-Targeted Genes", "d) Oncogene Roles"],
        specs=[[{"type": "bar"}, {"type": "bar"}], [{"type": "bar"}, {"type": "pie"}]],
        vertical_spacing=0.12, horizontal_spacing=0.1)

    # a) Records per source
    sources, counts, colors = [], [], []
    for i, (key, label) in enumerate([("drugs", "Drug-Target-Disease"), ("causal_associations", "Causal Gene-Disease"),
                        ("ehr_mount_sinai", "EHR Mount Sinai"), ("ehr_uk_biobank", "EHR UK Biobank"),
                        ("drug_response", "Drug Response")]):
        if key in stats:
            sources.append(label)
            counts.append(stats[key]["total_records"])
            colors.append(NATURE_COLORS[i % len(NATURE_COLORS)])
    fig.add_trace(go.Bar(y=sources, x=counts, orientation='h', marker_color=colors,
        text=[f"{c:,}" for c in counts], textposition='outside',
        hovertemplate="<b>%{y}</b><br>Records: %{x:,}<extra></extra>"), row=1, col=1)

    # b) Phase distribution
    if "drugs" in stats and stats["drugs"].get("phases"):
        phases = stats["drugs"]["phases"]
        sorted_keys = sorted(phases.keys())
        fig.add_trace(go.Bar(x=[f"Phase {k}" for k in sorted_keys],
            y=[phases[k] for k in sorted_keys],
            marker_color=NATURE_COLORS[:len(sorted_keys)],
            hovertemplate="<b>%{x}</b><br>Records: %{y:,}<extra></extra>"), row=1, col=2)

    # c) Top 10 genes
    if "drug_target_disease" in db.dfs:
        dtd = db.dfs["drug_target_disease"]
        if "Gene" in dtd.columns:
            top = dtd["Gene"].value_counts().head(10)
            fig.add_trace(go.Bar(y=top.index[::-1].tolist(), x=top.values[::-1].tolist(),
                orientation='h', marker_color=NATURE_SECONDARY,
                hovertemplate="<b>%{y}</b><br>Associations: %{x:,}<extra></extra>"), row=2, col=1)

    # d) Oncogene roles
    if "oncogenes" in stats and stats["oncogenes"].get("role_distribution"):
        roles = stats["oncogenes"]["role_distribution"]
        fig.add_trace(go.Pie(labels=list(roles.keys()), values=list(roles.values()),
            marker_colors=NATURE_COLORS[:len(roles)],
            textinfo='label+percent', textfont_size=10), row=2, col=2)

    fig.update_layout(height=700, showlegend=False, **PLOTLY_LAYOUT)
    fig.update_xaxes(showgrid=False, showline=True, linewidth=0.8, linecolor="#333")
    fig.update_yaxes(showgrid=False, showline=True, linewidth=0.8, linecolor="#333")

    return combined_html, fig


# Precompute overview at startup
print("Building overview...")
_overview_html, _overview_fig = _build_overview()
print("Overview ready.")


# ============================================================
# Database Explorer: Drug-Target Binding Module
# ============================================================


def binding_module_search(gene: str, drug_id: str, min_affinity: str):
    """Orchestrate binding module queries."""
    if db is None:
        return None, None, _not_initialized(), _not_initialized()

    gene = gene.strip().upper() if gene else ""
    drug_id = drug_id.strip() if drug_id else ""
    min_aff = float(min_affinity) if min_affinity and min_affinity.strip() else None

    if not gene and not drug_id:
        return None, None, "<p style='font-family: Arial;'>Enter a gene symbol and/or drug ID.</p>", ""

    landscape_fig = None
    radar_fig = None
    stats_html = ""
    table_html = ""

    # Gene-based search
    if gene:
        binding_stats = db.get_target_binding_stats(gene=gene)
        if binding_stats:
            stats_html += _nature_card(f"{gene} Binding Statistics",
                f"<p>Avg pKd: <strong>{binding_stats.get('Avg_pKd', 'N/A')}</strong> | "
                f"Max pKd: <strong>{binding_stats.get('Max_pKd', 'N/A')}</strong> | "
                f"Drug Hits: <strong>{binding_stats.get('N_hit', 'N/A')}</strong> | "
                f"TPI: <strong>{binding_stats.get('TPI', 'N/A')}</strong></p>", NATURE_PRIMARY)

        # Get drugs targeting this gene
        drugs_df = db.get_drugs_by_target(gene)
        if not drugs_df.empty:
            display_cols = [c for c in ['drugId', 'Drug Name', 'Gene', 'phase', 'status', 'diseaseId'] if c in drugs_df.columns]
            table_html = _nature_table_html(drugs_df[display_cols] if display_cols else drugs_df)

        # Build landscape plot (Plotly)
        top_drugs = db.get_drugs_for_target_with_affinity(gene, limit=20)
        if not top_drugs.empty and "aff_local" in top_drugs.columns:
            adf = top_drugs.sort_values("aff_local", ascending=True)
            colors = [NATURE_GREEN if v >= 7 else NATURE_SECONDARY for v in adf["aff_local"]]
            landscape_fig = go.Figure(go.Bar(
                y=adf["Drug"], x=adf["aff_local"], orientation='h',
                marker_color=colors,
                customdata=adf["Drug"],
                hovertemplate="<b>%{y}</b><br>pKd: %{x:.2f}<br>"
                    "<a href='https://www.ebi.ac.uk/chembl/compound_report_card/%{customdata}'>View on ChEMBL</a><extra></extra>"))
            landscape_fig.add_vline(x=7.0, line_dash="dash", line_color=NATURE_RED, opacity=0.6,
                                    annotation_text="pKd = 7", annotation_position="top right")
            landscape_fig.update_layout(title=f"Drug Binding Affinities for {gene}",
                xaxis_title="Binding Affinity (pKd)", height=max(400, len(adf) * 28), **PLOTLY_LAYOUT)
            _apply_nature_axes(landscape_fig)

    # Drug + Gene: evidence radar (Plotly)
    if drug_id and gene:
        evidence = db.get_comprehensive_drug_target_evidence(drug_id, gene)
        if evidence and "sources" in evidence:
            categories = ["Binding Affinity", "Drug Response", "Target Statistics", "Drug Selectivity"]
            source_keys = ["binding_affinity", "drug_response", "target_stats", "drug_selectivity"]
            values = []
            for key in source_keys:
                src = evidence["sources"].get(key, {})
                if src.get("found"):
                    values.append(1.0 if src.get("strength", "moderate") == "strong" else 0.6)
                else:
                    values.append(0.0)
            radar_fig = go.Figure(go.Scatterpolar(
                r=values + [values[0]], theta=categories + [categories[0]],
                fill='toself', fillcolor=f'rgba(33,113,181,0.2)',
                line_color=NATURE_PRIMARY, line_width=2,
                marker=dict(size=8, color=NATURE_PRIMARY),
                hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>"))
            radar_fig.update_layout(
                title=f"Evidence: {drug_id} / {gene}<br>Overall: {evidence.get('overall_strength', 'unknown').upper()}",
                polar=dict(radialaxis=dict(visible=True, range=[0, 1.1], tickvals=[0.2, 0.4, 0.6, 0.8, 1.0])),
                height=450, **PLOTLY_LAYOUT)

            stats_html += _nature_card("Evidence Summary",
                f"<p>Overall strength: <strong>{evidence.get('overall_strength', 'unknown').upper()}</strong></p>"
                + "".join([f"<p>{lab}: {'Found' if evidence['sources'].get(k, {}).get('found') else 'Not found'}</p>"
                          for k, lab in zip(source_keys, categories)]),
                NATURE_GREEN if evidence.get('overall_strength') == 'strong' else NATURE_AMBER)

    elif drug_id and not gene:
        targets_df = db.get_targets_for_drug_with_affinity(drug_id, min_affinity=min_aff)
        if not targets_df.empty:
            table_html = _nature_table_html(targets_df)

    _last_results['binding_fig'] = landscape_fig
    return landscape_fig, radar_fig, stats_html, table_html


# ============================================================
# Database Explorer: Selectivity Module
# ============================================================


def plot_selectivity_bars(drug_id: str):
    """Plotly bar chart of target affinities for a drug."""
    if db is None:
        return None
    targets_df = db.get_targets_for_drug_with_affinity(drug_id, limit=20)
    if targets_df.empty or "aff_local" not in targets_df.columns:
        return None
    pdf = targets_df.sort_values("aff_local", ascending=True).tail(20)
    labels = pdf["Target"].str[:25] if "Target" in pdf.columns else pdf.index.astype(str)
    colors = [NATURE_GREEN if v >= 7 else NATURE_SECONDARY for v in pdf["aff_local"]]
    fig = go.Figure(go.Bar(y=labels, x=pdf["aff_local"], orientation='h', marker_color=colors,
        hovertemplate="<b>%{y}</b><br>pKd: %{x:.2f}<extra></extra>"))
    fig.add_vline(x=7.0, line_dash="dash", line_color=NATURE_RED, opacity=0.6,
                  annotation_text="pKd = 7", annotation_position="top right")
    fig.update_layout(title=f"Target Affinities for {drug_id}",
        xaxis_title="Binding Affinity (pKd)", height=max(350, len(pdf) * 28), **PLOTLY_LAYOUT)
    _apply_nature_axes(fig)
    return fig


def plot_selectivity_umap(drug_id: str):
    """Plotly UMAP scatter plot highlighting a specific drug."""
    if db is None or "drug_umap" not in db.dfs:
        return None
    umap_df = db.dfs["drug_umap"]
    if "x" not in umap_df.columns or "y" not in umap_df.columns:
        return None
    type_colors = {"Highly Selective": NATURE_GREEN, "Moderate poly-target": NATURE_AMBER, "Broad-spectrum": NATURE_RED}
    fig = go.Figure()
    for t, color in type_colors.items():
        mask = umap_df["Type"] == t
        sub = umap_df[mask]
        fig.add_trace(go.Scatter(x=sub["x"], y=sub["y"], mode='markers',
            marker=dict(size=4, color=color, opacity=0.4), name=t,
            customdata=sub["Drug"] if "Drug" in sub.columns else None,
            hovertemplate="Drug: %{customdata}<br>Type: " + t + "<extra></extra>"))
    drug_mask = umap_df["Drug"].str.contains(drug_id, case=False, na=False)
    if drug_mask.any():
        hit = umap_df[drug_mask]
        fig.add_trace(go.Scatter(x=hit["x"], y=hit["y"], mode='markers',
            marker=dict(size=14, color="black", symbol="star"),
            name=drug_id, hovertemplate=f"<b>{drug_id}</b><extra></extra>"))
    fig.update_layout(title="Drug Selectivity Landscape",
        xaxis_title="UMAP-1", yaxis_title="UMAP-2", height=500, **PLOTLY_LAYOUT)
    _apply_nature_axes(fig)
    return fig


def selectivity_module_search(drug_id: str, selectivity_type: str):
    """Orchestrate selectivity module queries."""
    if db is None:
        return None, None, _not_initialized(), ""

    drug_id = drug_id.strip() if drug_id else ""
    bars_fig = None
    umap_fig = None
    info_html = ""
    table_html = ""

    if drug_id:
        info = db.get_drug_selectivity_info(drug_id=drug_id)
        if info:
            info_html = _nature_card(f"{info.get('Drug', drug_id)} Selectivity",
                f"<p>Selectivity Score: <strong>{info.get('Selectivity_Score', 'N/A')}</strong></p>"
                f"<p>Type: <strong>{info.get('drug_type', 'N/A')}</strong></p>"
                f"<p>Targets Measured: <strong>{info.get('N_target_measured', 'N/A')}</strong></p>",
                NATURE_GREEN if info.get('drug_type') == 'Highly Selective' else NATURE_AMBER)
        bars_fig = plot_selectivity_bars(drug_id)
        umap_fig = plot_selectivity_umap(drug_id)

    if selectivity_type and selectivity_type != "All":
        type_df = db.get_drugs_by_selectivity_type(selectivity_type)
        if not type_df.empty:
            display_cols = [c for c in ['Drug', 'Type', 'x', 'y', 'cluster'] if c in type_df.columns]
            table_html = _nature_table_html(type_df[display_cols] if display_cols else type_df)

    if not drug_id and (not selectivity_type or selectivity_type == "All"):
        info_html = "<p style='font-family: Arial;'>Enter a drug ID or select a selectivity type.</p>"

    _last_results['sel_fig'] = bars_fig
    return bars_fig, umap_fig, info_html, table_html


# ============================================================
# Database Explorer: EHR Module
# ============================================================


def plot_ehr_forest(ehr_df: pd.DataFrame):
    """Plotly forest plot of odds ratios by disease, colored by source."""
    if ehr_df is None or ehr_df.empty:
        return None
    or_col = None
    for col_candidate in ['logit_or', 'odds_ratio', 'OR']:
        if col_candidate in ehr_df.columns:
            or_col = col_candidate
            break
    if not or_col:
        return None
    plot_df = ehr_df.dropna(subset=[or_col]).head(30).copy()
    if plot_df.empty:
        return None
    if 'ICD10' in plot_df.columns:
        plot_df['label'] = plot_df['ICD10'].astype(str)
    elif 'Disease' in plot_df.columns:
        plot_df['label'] = plot_df['Disease'].astype(str).str[:30]
    else:
        plot_df['label'] = [f"Assoc {i+1}" for i in range(len(plot_df))]

    source_colors = {'mount_sinai': NATURE_PRIMARY, 'uk_biobank': NATURE_AMBER}
    fig = go.Figure()
    if 'ehr_source' in plot_df.columns:
        for src, color in source_colors.items():
            mask = plot_df['ehr_source'] == src
            sub = plot_df[mask]
            if not sub.empty:
                fig.add_trace(go.Scatter(x=sub[or_col], y=sub['label'], mode='markers',
                    marker=dict(size=8, color=color), name=src.replace('_', ' ').title(),
                    hovertemplate="<b>%{y}</b><br>OR: %{x:.3f}<extra></extra>"))
    else:
        fig.add_trace(go.Scatter(x=plot_df[or_col], y=plot_df['label'], mode='markers',
            marker=dict(size=8, color=NATURE_PRIMARY),
            hovertemplate="<b>%{y}</b><br>OR: %{x:.3f}<extra></extra>"))
    fig.add_vline(x=1.0, line_dash="dash", line_color=NATURE_GRAY, opacity=0.5)
    fig.update_layout(title="EHR Drug-Disease Associations", xaxis_title="Odds Ratio",
        height=max(400, len(plot_df) * 22), **PLOTLY_LAYOUT)
    _apply_nature_axes(fig)
    return fig


def plot_ehr_comparison(risk_assessment: dict):
    """Plotly grouped bar chart: protective vs risk-increasing by source."""
    if not risk_assessment or not risk_assessment.get('found'):
        return None
    sources, protective, risk_inc = [], [], []
    for src_key, src_label in [('mount_sinai', 'Mount Sinai'), ('uk_biobank', 'UK Biobank')]:
        if src_key in risk_assessment and risk_assessment[src_key].get('total', 0) > 0:
            sources.append(src_label)
            protective.append(risk_assessment[src_key].get('protective', 0))
            risk_inc.append(risk_assessment[src_key].get('risk_increasing', 0))
    if not sources:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Protective (OR < 1)', x=sources, y=protective, marker_color=NATURE_GREEN,
        hovertemplate="<b>%{x}</b><br>Protective: %{y}<extra></extra>"))
    fig.add_trace(go.Bar(name='Risk-increasing (OR > 1)', x=sources, y=risk_inc, marker_color=NATURE_RED,
        hovertemplate="<b>%{x}</b><br>Risk-increasing: %{y}<extra></extra>"))
    fig.update_layout(barmode='group', title="Prevention Risk Assessment",
        yaxis_title="Number of Associations", height=400, **PLOTLY_LAYOUT)
    _apply_nature_axes(fig)
    return fig


def ehr_module_search(drug_id: str, drug_name: str, icd_code: str, disease_name: str, source: str):
    """Orchestrate EHR module queries."""
    if db is None:
        return _not_initialized(), None, None, ""

    drug_id = drug_id.strip() if drug_id else None
    drug_name = drug_name.strip() if drug_name else None
    icd_code = icd_code.strip() if icd_code else None
    disease_name = disease_name.strip() if disease_name else None
    source_val = None if source == "Both" else source.lower().replace(" ", "_") if source else None

    if not any([drug_id, drug_name, icd_code, disease_name]):
        return "<p style='font-family: Arial;'>Enter at least one search parameter.</p>", None, None, ""

    # Get associations
    ehr_df = db.get_ehr_drug_disease_associations(
        drug_id=drug_id, drug_name=drug_name, icd_code=icd_code,
        disease_name=disease_name, source=source_val
    )

    # Risk assessment
    risk = db.assess_prevention_risk(
        drug_id=drug_id, drug_name=drug_name, icd_code=icd_code, disease_name=disease_name
    )

    # Risk summary HTML
    risk_html = ""
    if risk and risk.get('found'):
        content = f"<p>Total associations: <strong>{risk['total_associations']}</strong></p>"
        for src_key, src_label in [('mount_sinai', 'Mount Sinai'), ('uk_biobank', 'UK Biobank')]:
            if src_key in risk and risk[src_key].get('total', 0) > 0:
                s = risk[src_key]
                content += (f"<p><strong>{src_label}:</strong> {s['total']} associations | "
                            f"Protective: {s.get('protective', 0)} | Risk-increasing: {s.get('risk_increasing', 0)} | "
                            f"Avg OR: {s.get('avg_or', 'N/A')}</p>")
        risk_html = _nature_card("Prevention Risk Assessment", content, NATURE_PRIMARY)
    elif ehr_df is not None and not ehr_df.empty:
        risk_html = _nature_card("EHR Results", f"<p>Found {len(ehr_df)} associations.</p>", NATURE_PRIMARY)
    else:
        risk_html = "<p style='font-family: Arial;'>No EHR data found for this query.</p>"

    # Plots
    forest_fig = plot_ehr_forest(ehr_df) if ehr_df is not None and not ehr_df.empty else None
    comparison_fig = plot_ehr_comparison(risk) if risk and risk.get('found') else None

    # Table
    table_html = ""
    if ehr_df is not None and not ehr_df.empty:
        table_html = _nature_table_html(ehr_df)

    _last_results['ehr_fig'] = forest_fig
    _last_results['ehr_df'] = ehr_df
    return risk_html, forest_fig, comparison_fig, table_html


# ============================================================
# Load custom CSS
# ============================================================


def load_custom_css() -> str:
    css_file = Path(__file__).parent / "css" / "custom.css"
    if css_file.exists():
        with open(css_file, 'r') as f:
            return f.read()
    return ""


# ============================================================
# Gradio Interface
# ============================================================

custom_css = load_custom_css()

with gr.Blocks(title="LinkD Drug Discovery Agent") as demo:
    # Global header
    gr.Markdown("# LinkD Drug Discovery Agent")

    gr.Markdown(f"*Database loaded: {len(db.dfs)} datasets*")

    # ================================================================
    # Top-level tabs
    # ================================================================
    with gr.Tabs():

        # ============================================================
        # TAB 1: DATABASE EXPLORER
        # ============================================================
        with gr.TabItem("Database Explorer"):
            with gr.Tabs():

                # ---- Overview sub-tab (preloaded) ----
                with gr.TabItem("Overview"):
                    gr.Markdown("### Database Overview")
                    overview_cards = gr.HTML(value=_overview_html)
                    overview_plot = gr.Plot(value=_overview_fig)
                    with gr.Row():
                        overview_dl_png = gr.Button("Download PNG", size="sm")
                        overview_dl_pdf = gr.Button("Download PDF", size="sm")
                    overview_dl_file = gr.File(visible=False)

                # ---- Drug-Target Binding sub-tab ----
                with gr.TabItem("Drug-Target Binding"):
                    gr.Markdown("### Drug-Target Binding Explorer")
                    gr.Markdown("**Examples:** click to load inputs")
                    with gr.Row():
                        bind_ex_btns = []
                        for label, *_ in BINDING_EXAMPLES:
                            bind_ex_btns.append(gr.Button(label, size="sm"))
                    with gr.Row():
                        with gr.Column(scale=1):
                            binding_gene_input = gr.Textbox(label="Gene Symbol", placeholder="e.g., BRAF, EGFR")
                            binding_drug_input = gr.Textbox(label="Drug ChEMBL ID (optional)", placeholder="e.g., CHEMBL1229517")
                            binding_affinity_input = gr.Textbox(label="Min Affinity (optional)", placeholder="e.g., 7.0")
                            binding_search_btn = gr.Button("Search", variant="primary")
                        with gr.Column(scale=2):
                            with gr.Row():
                                binding_landscape_plot = gr.Plot(label="Binding Landscape")
                                binding_radar_plot = gr.Plot(label="Evidence Radar")
                            binding_stats_html = gr.HTML()
                            binding_table_html = gr.HTML()
                            with gr.Row():
                                bind_dl_csv = gr.Button("Download CSV", size="sm")
                                bind_dl_png = gr.Button("Download PNG", size="sm")
                                bind_dl_pdf = gr.Button("Download PDF", size="sm")
                            bind_dl_file = gr.File(visible=False)

                # ---- Selectivity sub-tab ----
                with gr.TabItem("Selectivity"):
                    gr.Markdown("### Drug Selectivity Explorer")
                    gr.Markdown("**Examples:** click to load inputs")
                    with gr.Row():
                        sel_ex_btns = []
                        for label, *_ in SELECTIVITY_EXAMPLES:
                            sel_ex_btns.append(gr.Button(label, size="sm"))
                    with gr.Row():
                        with gr.Column(scale=1):
                            sel_drug_input = gr.Textbox(label="Drug ChEMBL ID", placeholder="e.g., CHEMBL1229517")
                            sel_type_dropdown = gr.Dropdown(
                                label="Selectivity Type",
                                choices=["All", "Highly Selective", "Moderate poly-target", "Broad-spectrum"],
                                value="All"
                            )
                            sel_search_btn = gr.Button("Search", variant="primary")
                        with gr.Column(scale=2):
                            with gr.Row():
                                sel_bars_plot = gr.Plot(label="Target Affinities")
                                sel_umap_plot = gr.Plot(label="UMAP Landscape")
                            sel_info_html = gr.HTML()
                            sel_table_html = gr.HTML()
                            with gr.Row():
                                sel_dl_csv = gr.Button("Download CSV", size="sm")
                                sel_dl_png = gr.Button("Download PNG", size="sm")
                                sel_dl_pdf = gr.Button("Download PDF", size="sm")
                            sel_dl_file = gr.File(visible=False)

                # ---- EHR sub-tab ----
                with gr.TabItem("EHR"):
                    gr.Markdown("### Electronic Health Records Explorer")
                    gr.Markdown("**Examples:** click to load inputs")
                    with gr.Row():
                        ehr_ex_btns = []
                        for label, *_ in EHR_EXAMPLES:
                            ehr_ex_btns.append(gr.Button(label, size="sm"))
                    with gr.Row():
                        with gr.Column(scale=1):
                            ehr_drug_id_input = gr.Textbox(label="Drug ChEMBL ID", placeholder="e.g., CHEMBL716")
                            ehr_drug_name_input = gr.Textbox(label="Drug Name", placeholder="e.g., aspirin")
                            ehr_icd_input = gr.Textbox(label="ICD-10 Code", placeholder="e.g., C61, I10")
                            ehr_disease_input = gr.Textbox(label="Disease Name", placeholder="e.g., melanoma")
                            ehr_source_dropdown = gr.Dropdown(
                                label="EHR Source",
                                choices=["Both", "Mount Sinai", "UK Biobank"],
                                value="Both"
                            )
                            ehr_search_btn = gr.Button("Search", variant="primary")
                        with gr.Column(scale=2):
                            ehr_risk_html = gr.HTML()
                            with gr.Row():
                                ehr_forest_plot = gr.Plot(label="Odds Ratios")
                                ehr_comparison_plot = gr.Plot(label="Risk Assessment")
                            ehr_table_html = gr.HTML()
                            with gr.Row():
                                ehr_dl_csv = gr.Button("Download CSV", size="sm")
                                ehr_dl_png = gr.Button("Download PNG", size="sm")
                                ehr_dl_pdf = gr.Button("Download PDF", size="sm")
                            ehr_dl_file = gr.File(visible=False)

        # ============================================================
        # TAB 2: AGENT
        # ============================================================
        with gr.TabItem("Agent"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Model Configuration")
                    provider_dropdown = gr.Dropdown(
                        choices=list(PROVIDER_MAP.keys()),
                        value="OpenAI",
                        label="LLM Provider"
                    )
                    _default_models = ", ".join(PROVIDERS["openai"]["models"])
                    model_input = gr.Textbox(
                        label="Model Name",
                        value=PROVIDERS["openai"]["default"],
                        placeholder=f"e.g., {_default_models}"
                    )
                    api_key_input = gr.Textbox(
                        label="API Key",
                        type="password",
                        placeholder="Session only — not saved"
                    )
                    init_agent_btn = gr.Button("Initialize Agent", variant="primary")
                    agent_status = gr.Textbox(label="Agent Status", interactive=False, lines=2)

                    gr.Markdown("---")
                    gr.Markdown("### Pre-Run Examples")
                    gr.Markdown("*No API key required — view saved results*")
                    prerun_btns = []
                    for label, _ in PRERUN_EXAMPLES:
                        prerun_btns.append(gr.Button(label, size="sm"))

                    gr.Markdown("---")
                    gr.Markdown("### LLM Example Queries")
                    gr.Markdown("*Requires API key*")
                    example_btns = []
                    for i, (name, query) in enumerate(EXAMPLE_QUERIES):
                        btn = gr.Button(name, size="sm")
                        example_btns.append(btn)

                    gr.Markdown("### History")
                    history_btn = gr.Button("View History", size="sm")
                    history_display = gr.HTML()

                with gr.Column(scale=2):
                    gr.Markdown("### Enter Your Query")
                    query_input = gr.Textbox(
                        label="Analysis Query",
                        placeholder="e.g., How strong is the evidence that vemurafenib binds to BRAF?",
                        lines=4
                    )
                    with gr.Row():
                        generate_btn = gr.Button("Generate Plan", variant="primary")
                        execute_btn = gr.Button("Execute Plan", variant="secondary")
                    plan_status = gr.Textbox(label="Plan Status", interactive=False)
                    plan_display = gr.HTML(label="Generated Plan")
                    execution_status = gr.Textbox(label="Execution Status", interactive=False, lines=3, value="Ready to execute plan...")
                    results_display = gr.HTML(label="Analysis Results", value="<p style='color: #666; font-style: italic; font-family: Arial;'>Results will appear here after execution.</p>")

    # ================================================================
    # Event Handlers
    # ================================================================

    # Agent tab: model config
    def update_model_suggestions(provider_name):
        provider_key, _ = PROVIDER_MAP.get(provider_name, ("openai", []))
        models = PROVIDERS[provider_key]["models"]
        default = PROVIDERS[provider_key]["default"]
        return gr.Textbox(value=default, placeholder=f"e.g., {', '.join(models)}")

    provider_dropdown.change(fn=update_model_suggestions, inputs=provider_dropdown, outputs=model_input)
    init_agent_btn.click(
        fn=initialize_agent,
        inputs=[provider_dropdown, model_input, api_key_input],
        outputs=agent_status
    )

    # Agent tab: pre-run examples
    for i, btn in enumerate(prerun_btns):
        _, filepath = PRERUN_EXAMPLES[i]
        btn.click(fn=lambda fp=filepath: load_prerun_example(fp),
                  outputs=[query_input, plan_status, plan_display, execution_status, results_display])

    # Agent tab
    def make_example_handler(idx):
        return lambda: load_example(idx)
    for i, btn in enumerate(example_btns):
        btn.click(fn=make_example_handler(i), outputs=query_input)
    generate_btn.click(fn=generate_plan, inputs=query_input, outputs=[plan_status, plan_display, generate_btn, execute_btn])
    execute_btn.click(fn=execute_plan, outputs=[execution_status, results_display])
    history_btn.click(fn=get_history, outputs=history_display)

    # Database Explorer: Overview downloads
    overview_dl_png.click(fn=lambda: _save_plotly_image(_overview_fig, "png"), outputs=overview_dl_file)
    overview_dl_pdf.click(fn=lambda: _save_plotly_image(_overview_fig, "pdf"), outputs=overview_dl_file)

    # Database Explorer: Binding examples
    for i, btn in enumerate(bind_ex_btns):
        _, gene, drug, aff = BINDING_EXAMPLES[i]
        btn.click(fn=lambda g=gene, d=drug, a=aff: (g, d, a),
                  outputs=[binding_gene_input, binding_drug_input, binding_affinity_input])

    # Database Explorer: Binding
    binding_search_btn.click(
        fn=binding_module_search,
        inputs=[binding_gene_input, binding_drug_input, binding_affinity_input],
        outputs=[binding_landscape_plot, binding_radar_plot, binding_stats_html, binding_table_html]
    )

    # Database Explorer: Selectivity examples
    for i, btn in enumerate(sel_ex_btns):
        _, drug, stype = SELECTIVITY_EXAMPLES[i]
        btn.click(fn=lambda d=drug, t=stype: (d, t),
                  outputs=[sel_drug_input, sel_type_dropdown])

    # Database Explorer: Selectivity
    sel_search_btn.click(
        fn=selectivity_module_search,
        inputs=[sel_drug_input, sel_type_dropdown],
        outputs=[sel_bars_plot, sel_umap_plot, sel_info_html, sel_table_html]
    )

    # Database Explorer: EHR examples
    for i, btn in enumerate(ehr_ex_btns):
        _, did, dname, icd, disease, src = EHR_EXAMPLES[i]
        btn.click(fn=lambda a=did, b=dname, c=icd, d=disease, e=src: (a, b, c, d, e),
                  outputs=[ehr_drug_id_input, ehr_drug_name_input, ehr_icd_input, ehr_disease_input, ehr_source_dropdown])

    # Database Explorer: EHR
    ehr_search_btn.click(
        fn=ehr_module_search,
        inputs=[ehr_drug_id_input, ehr_drug_name_input, ehr_icd_input, ehr_disease_input, ehr_source_dropdown],
        outputs=[ehr_risk_html, ehr_forest_plot, ehr_comparison_plot, ehr_table_html]
    )

    # Download handlers
    bind_dl_csv.click(fn=lambda: _save_csv(_last_results.get('binding_df'), "binding"), outputs=bind_dl_file)
    bind_dl_png.click(fn=lambda: _save_plotly_image(_last_results.get('binding_fig'), "png"), outputs=bind_dl_file)
    bind_dl_pdf.click(fn=lambda: _save_plotly_image(_last_results.get('binding_fig'), "pdf"), outputs=bind_dl_file)
    sel_dl_csv.click(fn=lambda: _save_csv(None, "selectivity"), outputs=sel_dl_file)
    sel_dl_png.click(fn=lambda: _save_plotly_image(_last_results.get('sel_fig'), "png"), outputs=sel_dl_file)
    sel_dl_pdf.click(fn=lambda: _save_plotly_image(_last_results.get('sel_fig'), "pdf"), outputs=sel_dl_file)
    ehr_dl_csv.click(fn=lambda: _save_csv(_last_results.get('ehr_df'), "ehr"), outputs=ehr_dl_file)
    ehr_dl_png.click(fn=lambda: _save_plotly_image(_last_results.get('ehr_fig'), "png"), outputs=ehr_dl_file)
    ehr_dl_pdf.click(fn=lambda: _save_plotly_image(_last_results.get('ehr_fig'), "pdf"), outputs=ehr_dl_file)


# ============================================================
# Launch
# ============================================================

if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", 7860))
    share_public = os.getenv("GRADIO_SHARE", "True").lower() == "true"
    try:
        demo.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=share_public,
            theme=gr.themes.Soft(),
            css=custom_css if custom_css else None
        )
    except Exception as e:
        if share_public and "share" in str(e).lower():
            print("\n" + "=" * 60)
            print("Could not create public share link. Retrying local only...")
            print("=" * 60 + "\n")
            demo.launch(
                server_name="0.0.0.0",
                server_port=port,
                share=False,
                theme=gr.themes.Soft(),
                css=custom_css if custom_css else None
            )
        else:
            raise
