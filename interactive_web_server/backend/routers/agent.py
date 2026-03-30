import os
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from services import db, planning_agent, PROVIDER_MAP, PROVIDERS, _last_results
import services

router = APIRouter()


def _format_result(result) -> str:
    """Format step result into readable text with actual data."""
    import pandas as pd
    if result is None:
        return "No data returned."
    if isinstance(result, pd.DataFrame):
        n = len(result)
        # Show top drug/gene names if available
        names = []
        for col in ["Drug Name", "Drug Chembl ID", "Gene", "Disease Description"]:
            if col in result.columns:
                top = result[col].dropna().unique()[:5]
                if len(top) > 0:
                    names.append(f"{col}: {', '.join(str(x) for x in top)}")
        preview = "; ".join(names) if names else ", ".join(list(result.columns)[:5])
        return f"Found {n} records. {preview}"
    if isinstance(result, dict):
        parts = []
        for k, v in result.items():
            if isinstance(v, pd.DataFrame):
                n = len(v)
                # Extract actual names
                drug_names = []
                for col in ["Drug Name", "Drug Chembl ID"]:
                    if col in v.columns:
                        drug_names = v[col].dropna().unique()[:5].tolist()
                        break
                if drug_names:
                    parts.append(f"{k}: {n} records — {', '.join(str(x) for x in drug_names)}")
                else:
                    parts.append(f"{k}: {n} records")
            elif isinstance(v, dict):
                if "data" in v and isinstance(v["data"], list) and len(v["data"]) > 0:
                    # Show actual drug names from data
                    names = []
                    for row in v["data"][:5]:
                        name = row.get("Drug Name") or row.get("drugId") or row.get("Drug Chembl ID", "")
                        if name:
                            names.append(str(name))
                    count = v.get("count", len(v["data"]))
                    if names:
                        parts.append(f"{k}: {count} records — {', '.join(names)}")
                    else:
                        parts.append(f"{k}: {count} records")
                else:
                    summary_keys = [sk for sk in v if isinstance(v[sk], (int, float, str)) and sk not in ('Sequence', 'Entry', 'Entry Name')]
                    items = [f"{sk}: {v[sk]}" for sk in summary_keys[:6]]
                    if items:
                        parts.append(f"{k}: {', '.join(items)}")
                    else:
                        parts.append(f"{k}: found")
            elif isinstance(v, list):
                parts.append(f"{k}: {len(v)} items")
            elif isinstance(v, (int, float)):
                parts.append(f"{k}: {v}")
            elif isinstance(v, str) and len(v) < 100:
                parts.append(f"{k}: {v}")
        return "; ".join(parts) if parts else f"{len(result)} fields returned"
    if isinstance(result, list):
        return f"Found {len(result)} items"
    return str(result)[:200]


class InitRequest(BaseModel):
    provider: str = "OpenAI"
    model: str = "gpt-4o-mini"
    api_key: str = ""


class PlanRequest(BaseModel):
    query: str


@router.post("/agent/init")
def agent_init(req: InitRequest):
    """Initialize the LLM agent with provider, model, and API key."""
    key = req.api_key.strip()
    if not key:
        provider_key = PROVIDER_MAP.get(req.provider, ("openai", []))[0]
        env_var = PROVIDERS[provider_key]["env_key"]
        key = os.getenv(env_var, "")
    # Fallback: free Gemini key from server env
    if not key and req.provider == "Google Gemini":
        key = os.getenv("GEMINI_FREE_KEY", "")
    if not key:
        provider_key = PROVIDER_MAP.get(req.provider, ("openai", []))[0]
        return {"status": "error", "message": f"Please enter an API key for {req.provider} (or set {PROVIDERS[provider_key]['env_key']} in .env)."}

    provider_key = PROVIDER_MAP[req.provider][0]
    try:
        from agent import LLMClient, LLMPlanningAgent
        llm_client = LLMClient(provider=provider_key, api_key=key, model=req.model)
        services.planning_agent = LLMPlanningAgent(llm_client=llm_client, db=db)
        return {"status": "ok", "message": f"Agent initialized with {req.provider} / {req.model}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/agent/plan")
def agent_plan(req: PlanRequest):
    """Generate an analysis plan from a natural language query."""
    if services.planning_agent is None:
        return {"status": "error", "message": "Please initialize the agent first."}
    if not req.query.strip():
        return {"status": "error", "message": "Please enter a query."}

    try:
        plan = services.planning_agent.generate_plan(req.query)
        services.current_plan = plan
        steps = []
        for step in plan.steps:
            steps.append({
                "step_number": step.step_number,
                "description": step.description,
                "data_sources": step.data_sources,
                "status": step.status,
            })
        return {"status": "ok", "steps": steps, "query": plan.query}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/agent/execute")
def agent_execute():
    """Execute the current plan. Returns results synchronously."""
    if services.planning_agent is None:
        return {"status": "error", "message": "Agent not initialized."}
    if services.current_plan is None:
        return {"status": "error", "message": "No plan to execute. Generate a plan first."}

    try:
        plan = services.planning_agent.execute_plan(services.current_plan)
        services.current_plan = plan

        steps_results = []
        for step in plan.steps:
            step_data = {
                "step_number": step.step_number,
                "description": step.description,
                "status": step.status,
                "error": step.error,
            }
            if step.result is not None:
                step_data["result_summary"] = _format_result(step.result)
            steps_results.append(step_data)

        # Save to history
        from datetime import datetime
        services.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "query": plan.query,
            "steps": len(plan.steps),
            "completed": sum(1 for s in plan.steps if s.status == "completed"),
        })

        return {
            "status": "ok",
            "steps": steps_results,
            "summary": plan.summary or "",
            "overall_status": plan.overall_status,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/agent/history")
def agent_history():
    """Return execution history."""
    return {"history": services.execution_history}


@router.get("/agent/providers")
def agent_providers():
    """Return available LLM providers and their suggested models."""
    result = {}
    for display_name, (key, models) in PROVIDER_MAP.items():
        result[display_name] = {
            "key": key,
            "models": models,
            "default": PROVIDERS[key]["default"],
            "env_key": PROVIDERS[key]["env_key"],
        }
    return result
