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
        
        planning_prompt = f"""You are an expert biomedical data analyst for the LinkD drug discovery platform.
Given a user query, create a step-by-step analysis plan using LinkD's data sources.

## Available Data Sources and What They Can Query:

1. **drug_info**: Drug-target-disease associations from ChEMBL (276K records)
   - Search by: drug name, drug ChEMBL ID, gene/target name, or disease name
   - Returns: drugs, targets, clinical trial phases, mechanisms of action
   - Use when: user asks about drugs for a disease, or what a drug targets

2. **target_info**: Gene/target information (1,520 genes)
   - Search by: gene symbol (e.g., EGFR, BRAF, TP53, KRAS)
   - Returns: associated drugs, diseases, oncogene/TSG status, target priority scores
   - Use when: user asks about a specific gene or target

3. **binding_affinity**: Drug-target binding affinity measurements (1,068 targets with pKd)
   - Search by: gene symbol alone (returns top drugs by binding), or drug + gene (returns specific pKd)
   - Returns: pKd values (higher = stronger, >7 is strong), selectivity scores
   - Use when: user asks about binding strength or drug potency

4. **drug_response**: CRISPR gene knockout drug response (464K records)
   - Search by: drug name/ID and/or gene symbol
   - Returns: AUC/IC50 correlations showing if gene affects drug sensitivity
   - Use when: user asks about functional evidence or drug sensitivity

5. **ehr**: Cancer drug-disease associations from EHR data (Mount Sinai 11.5M patients + UK Biobank 500K)
   - Search by: drug name/ID, OR disease/cancer name, OR ICD-10 code
   - CAN SEARCH BY DISEASE ALONE to find ALL drugs associated with that cancer
   - Returns: odds ratios (OR < 1 = protective, OR > 1 = risk), p-values, patient counts
   - Covers 55 cancer types: lung, breast, prostate, colon, melanoma, liver, etc.
   - Use when: user asks about real-world evidence, drug repurposing, or cancer associations

6. **comprehensive**: Multi-source evidence aggregation
   - Requires: both drug ID and gene symbol
   - Returns: combined evidence strength (strong/moderate/weak) from all sources
   - Use when: assessing overall evidence for a specific drug-target pair

## Recommended Workflows:

**Drug repurposing for a cancer/disease:**
1. Search EHR by disease name to find drugs with significant associations
2. Search drug_info for drugs associated with the disease
3. For top drug candidates, check binding_affinity to known targets
4. Synthesize and rank candidates

**Drugs targeting a specific gene:**
1. Get target_info for the gene (role, priority, diseases)
2. Search binding_affinity for top drugs by pKd
3. Check drug_response for functional evidence
4. Check EHR for real-world clinical evidence

**Generic disease question (e.g., "best treatments for X"):**
1. Search drug_info by disease to find associated drugs and targets
2. Search EHR by disease for real-world protective associations
3. For key targets found, check binding_affinity data
4. Summarize multi-source evidence

**Evidence assessment for a drug-target pair:**
1. Get binding_affinity for the pair
2. Check drug_response correlations
3. Search EHR for clinical evidence
4. Run comprehensive evidence aggregation

Query: "{query}"

Create a JSON plan with 3-6 steps. Each step specifies data_sources to query.
Return ONLY valid JSON:
{{
    "steps": [
        {{
            "step_number": 1,
            "description": "What to do in this step",
            "data_sources": ["drug_info"]
        }}
    ]
}}"""

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
    
    # Disease name → ICD-10 code mapping
    DISEASE_MAP = {
        "lung cancer": ("C34", "Malignant neoplasm of bronchus and lung"),
        "breast cancer": ("C50", "Malignant neoplasm of breast"),
        "prostate cancer": ("C61", "Malignant neoplasm of prostate"),
        "colon cancer": ("C18", "Malignant neoplasm of colon"),
        "colorectal cancer": ("C18", "Malignant neoplasm of colon"),
        "liver cancer": ("C22", "Malignant neoplasm of liver"),
        "hepatocellular carcinoma": ("C22", "Malignant neoplasm of liver"),
        "melanoma": ("C43", "Malignant melanoma of skin"),
        "skin cancer": ("C44", "Other malignant neoplasm of skin"),
        "leukemia": ("C95", "Leukemia of unspecified cell type"),
        "lymphoma": ("C85", "Non-Hodgkin lymphoma"),
        "pancreatic cancer": ("C25", "Malignant neoplasm of pancreas"),
        "kidney cancer": ("C64", "Malignant neoplasm of kidney"),
        "renal cell carcinoma": ("C64", "Malignant neoplasm of kidney"),
        "bladder cancer": ("C67", "Malignant neoplasm of bladder"),
        "thyroid cancer": ("C73", "Malignant neoplasm of thyroid gland"),
        "ovarian cancer": ("C56", "Malignant neoplasm of ovary"),
        "stomach cancer": ("C16", "Malignant neoplasm of stomach"),
        "gastric cancer": ("C16", "Malignant neoplasm of stomach"),
        "brain cancer": ("C71", "Malignant neoplasm of brain"),
        "glioblastoma": ("C71", "Malignant neoplasm of brain"),
        "glioma": ("C71", "Malignant neoplasm of brain"),
        "multiple myeloma": ("C90", "Multiple myeloma"),
        "esophageal cancer": ("C15", "Malignant neoplasm of esophagus"),
        "cervical cancer": ("C53", "Malignant neoplasm of cervix uteri"),
        "uterine cancer": ("C54", "Malignant neoplasm of corpus uteri"),
        "endometrial cancer": ("C54", "Malignant neoplasm of corpus uteri"),
        "laryngeal cancer": ("C32", "Malignant neoplasm of larynx"),
        "head and neck cancer": ("C10", "Malignant neoplasm of oropharynx"),
        "oral cancer": ("C06", "Malignant neoplasm of other parts of mouth"),
        "tongue cancer": ("C01", "Malignant neoplasm of base of tongue"),
        "rectal cancer": ("C20", "Malignant neoplasm of rectum"),
        "testicular cancer": ("C62", "Malignant neoplasm of testis"),
        "mesothelioma": ("C45", "Mesothelioma"),
        "neuroblastoma": ("C74", "Malignant neoplasm of adrenal gland"),
        "sarcoma": ("C49", "Malignant neoplasm of connective tissue"),
        "nsclc": ("C34", "Malignant neoplasm of bronchus and lung"),
        "non-small cell lung cancer": ("C34", "Malignant neoplasm of bronchus and lung"),
        "small cell lung cancer": ("C34", "Malignant neoplasm of bronchus and lung"),
    }

    def _extract_entities(self, query: str) -> Dict[str, Optional[str]]:
        """
        Extract entities (drug_id, gene, disease, icd_code) from query.
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
        icd_match = re.search(r'\bC\d{2,3}\b', query, re.IGNORECASE)
        if icd_match:
            entities["icd_code"] = icd_match.group(0).upper()

        # Extract disease name (match longest first)
        for disease_name in sorted(self.DISEASE_MAP.keys(), key=len, reverse=True):
            if disease_name in query_lower:
                icd, desc = self.DISEASE_MAP[disease_name]
                entities["disease"] = desc
                if not entities["icd_code"]:
                    entities["icd_code"] = icd
                break

        # Look for common gene names
        common_genes = [
            "BRAF", "EGFR", "TP53", "KRAS", "PIK3CA", "PTEN", "MYC", "HER2", "ERBB2",
            "ALK", "MET", "VEGFR", "PDGFR", "FGFR", "IGF1R", "KIT", "FLT3",
            "ABL1", "SRC", "JAK2", "STAT3", "AKT1", "MTOR", "CDK4", "CDK6",
            "RET", "ROS1", "NTRK", "IDH1", "IDH2", "BRCA1", "BRCA2", "ATM",
            "RAF1", "MAP2K1", "ERBB3", "ERBB4", "FGFR1", "FGFR2", "FGFR3",
        ]
        for g in common_genes:
            pattern = rf'\b{g}\b'
            if re.search(pattern, query, re.IGNORECASE):
                entities["gene"] = g
                break

        # Extract drug names (expanded list)
        common_drugs = {
            "vemurafenib": "CHEMBL1229517", "cetirizine": "CHEMBL1000",
            "erlotinib": "CHEMBL553", "imatinib": "CHEMBL941",
            "gefitinib": "CHEMBL939", "osimertinib": "CHEMBL3353410",
            "afatinib": "CHEMBL1173655", "lapatinib": "CHEMBL554",
            "sorafenib": "CHEMBL1647", "sunitinib": "CHEMBL535",
            "dabrafenib": "CHEMBL2028663", "trametinib": "CHEMBL2103875",
            "crizotinib": "CHEMBL601719", "pembrolizumab": "CHEMBL3137343",
            "nivolumab": "CHEMBL3137309", "trastuzumab": "CHEMBL1201585",
            "rituximab": "CHEMBL1201576", "bevacizumab": "CHEMBL1201583",
            "tamoxifen": "CHEMBL83", "metformin": "CHEMBL1431",
            "aspirin": "CHEMBL25", "doxorubicin": "CHEMBL53463",
            "cisplatin": "CHEMBL11359", "paclitaxel": "CHEMBL428647",
            "carboplatin": "CHEMBL1351", "gemcitabine": "CHEMBL888",
            "docetaxel": "CHEMBL92", "5-fluorouracil": "CHEMBL185",
            "temozolomide": "CHEMBL810", "vincristine": "CHEMBL100",
        }
        for drug_name, chembl_id in common_drugs.items():
            if drug_name.lower() in query_lower:
                entities["drug_name"] = drug_name
                if not entities["drug_id"]:
                    entities["drug_id"] = chembl_id
                break

        # Try to find drug name from database
        if entities["drug_name"] and not entities["drug_id"]:
            try:
                dtd = self.db.dfs.get("drug_target_disease")
                if dtd is not None and "Drug Name" in dtd.columns:
                    match = dtd[dtd["Drug Name"].str.lower() == entities["drug_name"].lower()]
                    if not match.empty and "drugId" in match.columns:
                        entities["drug_id"] = match.iloc[0]["drugId"]
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
                if drug_id or icd_code or disease:
                    ehr_data = self.db.get_ehr_drug_disease_associations(
                        drug_id=drug_id, icd_code=icd_code, disease_name=disease)
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
        
        # Enrich with external knowledge from LLM, then generate combined summary
        external_context = self._get_external_knowledge(plan)
        plan.summary = self._generate_summary(plan, external_context=external_context)
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
    
    def _get_external_knowledge(self, plan: AnalysisPlan) -> str:
        """Ask LLM to provide clinical context for LinkD findings using training knowledge."""
        if not self.llm_client and not getattr(self, '_legacy_client', None):
            return ""

        # Extract key entities from query and results
        drugs, genes, diseases = [], [], []
        entities = self._extract_entities(plan.query)
        if entities.get("drug_name"):
            drugs.append(entities["drug_name"])
        if entities.get("gene"):
            genes.append(entities["gene"])
        if entities.get("disease"):
            diseases.append(entities["disease"])

        # Also extract from step results
        for step in plan.steps:
            if step.result and isinstance(step.result, dict):
                for key, val in step.result.items():
                    if isinstance(val, dict) and "data" in val and isinstance(val["data"], list):
                        for row in val["data"][:5]:
                            if row.get("Drug Name") and row["Drug Name"] not in drugs:
                                drugs.append(row["Drug Name"])
                            if row.get("Gene") and row["Gene"] not in genes:
                                genes.append(row["Gene"])

        drugs = drugs[:10]
        genes = genes[:5]
        disease_str = ", ".join(diseases) if diseases else plan.query

        prompt = f"""Based on your biomedical training knowledge, provide clinical context for these drug discovery findings.

Query: {plan.query}
Drugs identified by LinkD: {', '.join(drugs) if drugs else 'none identified'}
Target genes: {', '.join(genes) if genes else 'none identified'}
Disease context: {disease_str}

For EACH drug listed above, provide (2-3 sentences each):
1. Approved indications and clinical trial status
2. Mechanism of action and key molecular pathways
3. Relevance to the disease context (why this drug might have therapeutic potential)

Also provide:
4. Key biomarkers for patient selection (if applicable)
5. Known resistance mechanisms or safety concerns

Be SPECIFIC and FACTUAL. Use drug names from the list above.
Total response under 300 words."""

        try:
            result = self.llm_client.chat([
                {"role": "system", "content": "You are a clinical pharmacology expert. Provide factual, well-established biomedical knowledge. Do not speculate."},
                {"role": "user", "content": prompt}
            ], temperature=0.2)
            return result
        except Exception as e:
            print(f"  External knowledge enrichment failed: {e}")
            return ""

    def _generate_summary(self, plan: AnalysisPlan, external_context: str = "") -> str:
        """Generate a summary combining LinkD data and external clinical context."""
        if not self.llm_client and not getattr(self, '_legacy_client', None):
            return "Analysis completed. See step results for details."

        import pandas as pd

        import math

        # Field name mapping for human-readable output
        FIELD_NAMES = {
            "logit_or": "Odds Ratio", "odds_ratio": "Odds Ratio",
            "logit_p": "P-value", "raw_fisher_p": "P-value",
            "cox_hr": "Hazard Ratio", "cox_p": "Cox P-value",
            "Drug Chembl ID": "Drug ID", "drugId": "Drug ID",
            "Drug Name": "Drug", "Gene": "Target Gene",
            "ICD10": "ICD-10", "Disease Description": "Disease",
            "mechanismOfAction": "Mechanism", "phase": "Clinical Phase",
            "AUC_corr": "AUC Correlation", "IC50_corr": "IC50 Correlation",
            "Avg_pKd": "Avg Binding (pKd)", "Max_pKd": "Max Binding (pKd)",
            "N_hit": "Drug Hits", "TPI": "Target Priority Index",
            "Selectivity_Score": "Selectivity Score",
            "overall_strength": "Overall Evidence",
        }

        def _clean_val(v):
            """Clean a value for display — remove NaN, round floats."""
            if v is None:
                return None
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    return None
                return round(v, 4)
            return v

        def _format_row(row):
            """Format a data row with clean field names and OR interpretation."""
            parts = []
            or_added = False

            for raw_key in ["Drug Name", "Gene", "ICD10", "Disease Description",
                            "logit_or", "odds_ratio", "logit_p", "cox_hr",
                            "phase", "mechanismOfAction", "AUC_corr", "IC50_corr"]:
                if raw_key not in row:
                    continue
                val = _clean_val(row[raw_key])
                if val is None:
                    continue

                # Unify logit_or and odds_ratio into one "Odds Ratio" with interpretation
                if raw_key in ("logit_or", "odds_ratio"):
                    if or_added:
                        continue  # skip duplicate
                    or_added = True
                    direction = "protective" if val < 1 else "risk-increasing" if val > 1 else "neutral"
                    parts.append(f"Odds Ratio: {val} ({direction})")
                elif raw_key == "logit_p":
                    if val < 0.001:
                        parts.append(f"P-value: {val:.2e} (highly significant)")
                    elif val < 0.05:
                        parts.append(f"P-value: {val:.4f} (significant)")
                    else:
                        parts.append(f"P-value: {val:.4f}")
                elif raw_key == "cox_hr":
                    direction = "reduced risk" if val < 1 else "increased risk"
                    parts.append(f"Hazard Ratio: {val} ({direction})")
                elif raw_key == "AUC_corr":
                    direction = "gene may be target" if val < 0 else "resistance factor"
                    parts.append(f"AUC Correlation: {val} ({direction})")
                else:
                    display_key = FIELD_NAMES.get(raw_key, raw_key)
                    parts.append(f"{display_key}: {val}")

            return ", ".join(parts[:8])

        # Collect actual data from results
        results_detail = []
        for step in plan.steps:
            if step.status == "completed" and step.result:
                results_detail.append(f"\nStep {step.step_number} — {step.description}:")
                for key, value in step.result.items():
                    if isinstance(value, pd.DataFrame):
                        n = len(value)
                        # Show top rows with clean formatting
                        rows = []
                        for _, r in value.head(10).iterrows():
                            rows.append(_format_row(r.to_dict()))
                        results_detail.append(f"  {key}: {n} records")
                        for r in rows:
                            if r:
                                results_detail.append(f"    • {r}")
                    elif isinstance(value, dict):
                        if "data" in value and isinstance(value["data"], list):
                            count = value.get("count", len(value["data"]))
                            results_detail.append(f"  {key}: {count} records")
                            for row in value["data"][:10]:
                                formatted = _format_row(row)
                                if formatted:
                                    results_detail.append(f"    • {formatted}")
                        else:
                            items = []
                            for k, v in value.items():
                                v = _clean_val(v)
                                if v is not None and k not in ("Sequence", "data") and not isinstance(v, (list, dict)):
                                    display_key = FIELD_NAMES.get(k, k)
                                    items.append(f"{display_key}: {v}")
                            if items:
                                results_detail.append(f"  {key}: {', '.join(items[:8])}")
            elif step.status == "failed":
                results_detail.append(f"\nStep {step.step_number} — FAILED: {step.error}")

        # Build external context section
        ext_section = ""
        if external_context:
            ext_section = f"""

CLINICAL CONTEXT (from biomedical knowledge base):
{external_context}
"""

        summary_prompt = f"""You are a senior biomedical scientist writing a comprehensive drug discovery report that integrates database evidence with clinical knowledge.

INSTRUCTIONS:
- Write in scientific style, like a results section in a research paper
- Use SPECIFIC drug names, odds ratios, p-values, and pKd values from the LinkD data
- Interpret values: OR < 1 = protective/reduced risk, OR > 1 = increased risk, pKd > 7 = strong binding
- Integrate the Clinical Context to explain WHY these drugs show these associations
- Round numbers to 2-3 significant figures
- Do NOT write generic templates or ask for more data
- Keep under 400 words total

FORMAT:
1. "LinkD Database Findings" section: specific results with drug names and values (bullet points)
2. "Clinical & Mechanistic Context" section: integrate external knowledge to explain findings
3. "Top Candidates" section: ranked list with rationale
4. "Conclusion" section: 1-2 sentences on next steps

QUERY: {plan.query}

DATA FROM LINKD:
{chr(10).join(results_detail)}
{ext_section}
Write the comprehensive report now:"""

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
