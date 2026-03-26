"""
LLM Planning Agent Module for Multi-Step Analysis

This module provides an LLM-powered planning agent that can:
1. Generate step-by-step analysis plans from natural language queries
2. Execute plans step by step
3. Track progress and show which steps are completed
4. Combine multiple data sources (binding affinity, EHR, drug response)
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .database_query_module import DrugDiseaseTargetDB, load_database
import pandas as pd

try:
    from .llm_client import LLMClient, PROVIDERS
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False

# Backward compat: try direct OpenAI import as fallback
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class PlanStep:
    """Represents a single step in an analysis plan."""
    step_number: int
    description: str
    data_sources: List[str]  # e.g., ["binding_affinity", "ehr", "drug_response"]
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class AnalysisPlan:
    """Container for a complete analysis plan."""
    query: str
    steps: List[PlanStep] = field(default_factory=list)
    overall_status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    summary: Optional[str] = None


class LLMPlanningAgent:
    """
    LLM-powered planning agent for multi-step drug-disease-target analysis.
    """
    
    def __init__(self,
                 database_dir: str = "Database",
                 openai_api_key: Optional[str] = None,
                 model: str = "gpt-4o-mini",
                 load_full_data: bool = True,
                 llm_client=None,
                 db=None):
        """
        Initialize the planning agent.

        Args:
            database_dir: Path to database directory
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var) — backward compat
            model: Model name (used with openai_api_key fallback)
            load_full_data: If True, load full data even for large files
            llm_client: LLMClient instance (preferred — supports OpenAI, Gemini, Claude)
            db: Pre-loaded database instance (optional, avoids reloading)
        """
        # Load database (reuse if provided)
        if db is not None:
            self.db = db
        else:
            print("Loading database...")
            self.db = load_database(database_dir, load_full_data=load_full_data)

        # Initialize LLM client
        if llm_client is not None:
            self.llm_client = llm_client
        elif LLM_CLIENT_AVAILABLE:
            # Backward compat: create OpenAI LLMClient from api_key
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm_client = LLMClient(provider="openai", api_key=api_key, model=model)
            else:
                self.llm_client = None
                print("Warning: No API key provided. LLM features will be unavailable.")
        elif OPENAI_AVAILABLE:
            # Direct OpenAI fallback if llm_client module not available
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._legacy_client = OpenAI(api_key=api_key)
                self._legacy_model = model
                self.llm_client = None  # use _legacy path
            else:
                self.llm_client = None
                self._legacy_client = None
                print("Warning: No API key provided. LLM features will be unavailable.")
        else:
            self.llm_client = None
            print("Warning: No LLM package available. Install openai, google-generativeai, or anthropic.")
    
    def generate_plan(self, query: str) -> AnalysisPlan:
        """
        Generate a step-by-step analysis plan from a natural language query.
        
        Args:
            query: Natural language query describing the analysis needed
        
        Returns:
            AnalysisPlan with steps to execute
        """
        if not self.llm_client and not getattr(self, '_legacy_client', None):
            raise ValueError("LLM client not available. Provide an API key or llm_client.")
        
        planning_prompt = f"""You are an expert biomedical data analyst. Given a query about drugs, diseases, or targets, create a step-by-step analysis plan.

Available data sources:
1. **Binding Affinity Data**: Drug-target binding affinities (pKd, aff_local), selectivity scores from DrugTargetMetrics/
2. **EHR Data**: Real-world drug-disease associations from Mount Sinai and UK Biobank (odds ratios, hazard ratios)
3. **Drug Response Data**: CRISPR gene knockout correlations with drug response (AUC, IC50 correlations)
4. **Target Information**: Gene roles, target priority scores, disease associations
5. **Drug Information**: Clinical trial phases, mechanisms of action, drug-target associations

Query: "{query}"

Create a JSON plan with the following structure:
{{
    "steps": [
        {{
            "step_number": 1,
            "description": "Brief description of what to do in this step",
            "data_sources": ["binding_affinity", "ehr", "drug_response", "target_info", "drug_info"],
            "query_type": "binding_affinity|ehr|drug_response|target_search|drug_search|comprehensive"
        }},
        ...
    ]
}}

Guidelines:
- Break down complex queries into logical steps
- Use multiple data sources when relevant
- Order steps logically (e.g., find drug first, then check binding, then check EHR)
- Be specific about what data to retrieve
- Include steps that combine evidence from multiple sources

Return only valid JSON."""

        try:
            messages = [
                {"role": "system", "content": "You are a biomedical data analysis planner. Return only valid JSON."},
                {"role": "user", "content": planning_prompt}
            ]
            if self.llm_client:
                response_text = self.llm_client.chat(messages, temperature=0.2, json_mode=True)
            else:
                response = self._legacy_client.chat.completions.create(
                    model=self._legacy_model, messages=messages,
                    temperature=0.2, response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content

            plan_data = json.loads(response_text)
            
            # Convert to AnalysisPlan
            steps = []
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    step_number=step_data.get("step_number", len(steps) + 1),
                    description=step_data.get("description", ""),
                    data_sources=step_data.get("data_sources", []),
                    status="pending"
                )
                steps.append(step)
            
            plan = AnalysisPlan(query=query, steps=steps)
            return plan
            
        except Exception as e:
            print(f"Error generating plan: {e}")
            # Return a simple fallback plan
            return AnalysisPlan(
                query=query,
                steps=[PlanStep(
                    step_number=1,
                    description=f"Analyze query: {query}",
                    data_sources=["drug_info", "target_info"],
                    status="pending"
                )]
            )
    
    def _extract_entities(self, query: str) -> Dict[str, Optional[str]]:
        """
        Extract entities (drug_id, gene, disease, icd_code) from query.
        
        Args:
            query: Natural language query
        
        Returns:
            Dictionary with extracted entities
        """
        import re
        
        entities = {
            "drug_id": None,
            "drug_name": None,
            "gene": None,
            "disease": None,
            "icd_code": None
        }
        
        query_lower = query.lower()
        
        # Extract ChEMBL IDs
        chembl_match = re.search(r'CHEMBL\d+', query, re.IGNORECASE)
        if chembl_match:
            entities["drug_id"] = chembl_match.group(0)
        
        # Extract ICD codes
        icd_match = re.search(r'[A-Z]\d{2,3}', query, re.IGNORECASE)
        if icd_match:
            entities["icd_code"] = icd_match.group(0).upper()
        
        # Look for common gene names (extended list)
        common_genes = [
            "BRAF", "EGFR", "TP53", "KRAS", "PIK3CA", "PTEN", "MYC", "HER2", 
            "ALK", "MET", "VEGFR", "PDGFR", "FGFR", "IGF1R", "KIT", "FLT3",
            "ABL1", "SRC", "JAK2", "STAT3", "AKT1", "MTOR", "CDK4", "CDK6"
        ]
        for g in common_genes:
            if g.lower() in query_lower or f" {g} " in query or query.startswith(g):
                entities["gene"] = g
                break
        
        # Try to extract drug names (common drugs)
        common_drugs = {
            "vemurafenib": "CHEMBL1229517",
            "cetirizine": "CHEMBL1000",
            "erlotinib": "CHEMBL1862",
            "imatinib": "CHEMBL941",
            "gefitinib": "CHEMBL1234"
        }
        for drug_name, chembl_id in common_drugs.items():
            if drug_name.lower() in query_lower:
                entities["drug_name"] = drug_name
                if not entities["drug_id"]:
                    entities["drug_id"] = chembl_id
                break
        
        # Try to find drug ID from database if drug name found
        if entities["drug_name"] and not entities["drug_id"]:
            try:
                drugs = self.db.search_drugs()
                if not drugs.empty and 'drugId' in drugs.columns:
                    drug_match = drugs[drugs['drugId'].str.contains(entities["drug_name"], case=False, na=False)]
                    if not drug_match.empty:
                        entities["drug_id"] = drug_match.iloc[0]['drugId']
            except:
                pass
        
        return entities
    
    def execute_step(self, step: PlanStep, query: str) -> PlanStep:
        """
        Execute a single plan step.
        
        Args:
            step: PlanStep to execute
            query: Original query for context
        
        Returns:
            Updated PlanStep with result
        """
        step.status = "in_progress"
        print(f"\n{'='*80}")
        print(f"Step {step.step_number}: {step.description}")
        print(f"Data sources: {', '.join(step.data_sources)}")
        print(f"{'='*80}")
        
        try:
            result_data = {}
            
            # Extract entities from query
            entities = self._extract_entities(query)
            drug_id = entities.get("drug_id")
            drug_name = entities.get("drug_name")
            gene = entities.get("gene")
            disease = entities.get("disease")
            icd_code = entities.get("icd_code")
            
            # Execute based on data sources
            if "binding_affinity" in step.data_sources:
                if drug_id and gene:
                    binding = self.db.get_drug_target_binding_affinity(drug_id, gene)
                    if binding:
                        result_data["binding_affinity"] = binding
                        print(f"  ✓ Found binding affinity: {binding.get('binding_affinity', 'N/A')}")
                    else:
                        print(f"  ⚠ No binding affinity data found")
                
                if gene:
                    target_stats = self.db.get_target_binding_stats(gene=gene)
                    if target_stats:
                        result_data["target_binding_stats"] = target_stats
                        print(f"  ✓ Found target binding statistics")
            
            if "drug_response" in step.data_sources:
                if drug_id or gene:
                    drug_response = self.db.get_drug_response_associations(
                        drug_id=drug_id,
                        gene=gene,
                        significant_only=True
                    )
                    if not drug_response.empty:
                        result_data["drug_response"] = {
                            "count": len(drug_response),
                            "avg_auc_corr": drug_response['AUC_corr'].mean() if 'AUC_corr' in drug_response.columns else None,
                            "avg_ic50_corr": drug_response['IC50_corr'].mean() if 'IC50_corr' in drug_response.columns else None,
                            "data": drug_response.head(10).to_dict('records')
                        }
                        print(f"  ✓ Found {len(drug_response)} drug response associations")
                    else:
                        print(f"  ⚠ No drug response data found")
            
            if "ehr" in step.data_sources:
                if drug_id:
                    ehr_data = self.db.get_ehr_drug_disease_associations(drug_id=drug_id, icd_code=icd_code)
                    if not ehr_data.empty:
                        # Separate by source
                        mount_sinai_count = 0
                        uk_biobank_count = 0
                        if 'ehr_source' in ehr_data.columns:
                            mount_sinai_count = len(ehr_data[ehr_data['ehr_source'] == 'ehr_mount_sinai'])
                            uk_biobank_count = len(ehr_data[ehr_data['ehr_source'] == 'ehr_uk_biobank'])
                        elif 'source' in ehr_data.columns:
                            mount_sinai_count = len(ehr_data[ehr_data['source'] == 'mount_sinai'])
                            uk_biobank_count = len(ehr_data[ehr_data['source'] == 'uk_biobank'])
                        else:
                            # Try to identify by checking which dataframe it came from
                            mount_sinai_count = len(ehr_data)
                            uk_biobank_count = 0
                        
                        result_data["ehr"] = {
                            "count": len(ehr_data),
                            "mount_sinai": mount_sinai_count,
                            "uk_biobank": uk_biobank_count,
                            "data": ehr_data.head(10).to_dict('records')
                        }
                        print(f"  ✓ Found {len(ehr_data)} EHR associations")
                        
                        # If specific ICD code, try prevention risk assessment
                        if drug_id and icd_code:
                            try:
                                risk = self.db.assess_prevention_risk(drug_id, icd_code)
                                if risk:
                                    result_data["prevention_risk"] = risk
                                    print(f"  ✓ Prevention risk assessed")
                            except:
                                pass
                    else:
                        print(f"  ⚠ No EHR data found")
            
            if "target_info" in step.data_sources:
                if gene:
                    target_info = self.db.get_target_info(gene)
                    if target_info:
                        result_data["target_info"] = target_info
                        print(f"  ✓ Found target information")
            
            if "drug_info" in step.data_sources or "selectivity" in step.data_sources:
                if drug_id or drug_name:
                    # Get drug selectivity info
                    selectivity_info = self.db.get_drug_selectivity_info(drug_id=drug_id, drug_name=drug_name)
                    if selectivity_info:
                        result_data["drug_selectivity"] = selectivity_info
                        print(f"  ✓ Found drug selectivity information")
                    
                    # Get general drug info
                    if drug_id:
                        drugs = self.db.search_drugs(drug_id=drug_id)
                        if not drugs.empty:
                            result_data["drug_info"] = {
                                "count": len(drugs),
                                "data": drugs.head(5).to_dict('records')
                            }
                            print(f"  ✓ Found drug information")
            
            if "comprehensive" in step.data_sources or len(step.data_sources) > 2:
                # Comprehensive evidence
                if drug_id and gene:
                    evidence = self.db.get_comprehensive_drug_target_evidence(drug_id, gene)
                    if evidence:
                        result_data["comprehensive_evidence"] = evidence
                        print(f"  ✓ Generated comprehensive evidence")
                        print(f"    Overall evidence strength: {evidence.get('overall_strength', 'unknown')}")
            
            # If no specific entities but query mentions targets, try to get target info
            if "target_info" in step.data_sources and not gene:
                # Try to extract from query or use default
                if "target" in query.lower() or "gene" in query.lower():
                    # Could use LLM to extract, but for now skip
                    pass
            
            step.result = result_data
            step.status = "completed"
            print(f"  ✅ Step {step.step_number} completed")
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            print(f"  ❌ Step {step.step_number} failed: {e}")
        
        return step
    
    def execute_plan(self, plan: AnalysisPlan, show_progress: bool = True) -> AnalysisPlan:
        """
        Execute all steps in a plan sequentially.
        
        Args:
            plan: AnalysisPlan to execute
            show_progress: Whether to print progress updates
        
        Returns:
            Updated AnalysisPlan with all results
        """
        plan.overall_status = "in_progress"
        
        if show_progress:
            print(f"\n{'='*80}")
            print(f"EXECUTING ANALYSIS PLAN")
            print(f"{'='*80}")
            print(f"Query: {plan.query}")
            print(f"Total steps: {len(plan.steps)}")
            print(f"{'='*80}\n")
        
        for step in plan.steps:
            if step.status == "pending":
                self.execute_step(step, plan.query)
                
                if show_progress:
                    self._print_progress(plan)
        
        # Generate summary
        plan.summary = self._generate_summary(plan)
        plan.overall_status = "completed"
        
        if show_progress:
            print(f"\n{'='*80}")
            print(f"PLAN EXECUTION COMPLETE")
            print(f"{'='*80}")
            print(f"Summary:\n{plan.summary}")
        
        return plan
    
    def _print_progress(self, plan: AnalysisPlan):
        """Print current progress of plan execution."""
        print(f"\n📊 Progress: {sum(1 for s in plan.steps if s.status == 'completed')}/{len(plan.steps)} steps completed")
        for step in plan.steps:
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(step.status, "❓")
            print(f"  {status_icon} Step {step.step_number}: {step.description}")
    
    def _generate_summary(self, plan: AnalysisPlan) -> str:
        """Generate a summary of the analysis results."""
        if not self.llm_client and not getattr(self, '_legacy_client', None):
            return "Analysis completed. See step results for details."
        
        # Collect all results
        results_summary = []
        for step in plan.steps:
            if step.status == "completed" and step.result:
                results_summary.append(f"Step {step.step_number}: {step.description}")
                for key, value in step.result.items():
                    if isinstance(value, dict):
                        if "count" in value:
                            results_summary.append(f"  - {key}: {value['count']} records found")
                        else:
                            results_summary.append(f"  - {key}: Data retrieved")
        
        summary_prompt = f"""Summarize the following analysis results in a clear, concise way:

Query: {plan.query}

Results:
{chr(10).join(results_summary)}

Provide a comprehensive summary that:
1. Answers the original query
2. Highlights key findings
3. Integrates evidence from multiple sources
4. Provides actionable insights

Summary:"""

        try:
            messages = [
                {"role": "system", "content": "You are a biomedical data analyst. Provide clear, concise summaries."},
                {"role": "user", "content": summary_prompt}
            ]
            if self.llm_client:
                return self.llm_client.chat(messages, temperature=0.3)
            else:
                response = self._legacy_client.chat.completions.create(
                    model=self._legacy_model, messages=messages, temperature=0.3
                )
                return response.choices[0].message.content
        except Exception as e:
            return f"Analysis completed. {len([s for s in plan.steps if s.status == 'completed'])}/{len(plan.steps)} steps completed successfully."
    
    def analyze_query(self, query: str, show_progress: bool = True) -> AnalysisPlan:
        """
        Complete workflow: generate plan and execute it.
        
        Args:
            query: Natural language query
            show_progress: Whether to show progress updates
        
        Returns:
            Completed AnalysisPlan
        """
        print(f"\n{'='*80}")
        print(f"GENERATING ANALYSIS PLAN")
        print(f"{'='*80}")
        print(f"Query: {query}\n")
        
        plan = self.generate_plan(query)
        
        if show_progress:
            print(f"Generated plan with {len(plan.steps)} steps:")
            for step in plan.steps:
                print(f"  Step {step.step_number}: {step.description}")
                print(f"    Data sources: {', '.join(step.data_sources)}")
        
        return self.execute_plan(plan, show_progress=show_progress)
