"""
LLM Agent Module for Natural Language Drug-Disease-Target Queries

This module integrates OpenAI GPT with the database query system to provide
natural language query capabilities with web search for additional context.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .database_query_module import DrugDiseaseTargetDB, load_database
import pandas as pd

# Optional web search integration
try:
    from .web_search_helper import WebSearchHelper
    WEB_SEARCH_AVAILABLE = True
except ImportError:
    WEB_SEARCH_AVAILABLE = False
    WebSearchHelper = None

try:
    from .llm_client import LLMClient, PROVIDERS
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    LLM_CLIENT_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class QueryResult:
    """Container for query results."""
    query_type: str
    data: Any
    summary: str
    sources: List[str]
    needs_web_search: bool = False
    web_context: Optional[str] = None


class DrugDiseaseTargetAgent:
    """
    AI Agent for querying drug-disease-target database using natural language.
    """
    
    def __init__(self,
                 database_dir: str = "Database",
                 openai_api_key: Optional[str] = None,
                 model: str = "gpt-4o-mini",
                 enable_web_search: bool = True,
                 web_search_provider: str = "duckduckgo",
                 web_search_api_key: Optional[str] = None,
                 load_full_data: bool = True,
                 llm_client=None,
                 db=None):
        """
        Initialize the agent.

        Args:
            database_dir: Path to database directory
            openai_api_key: OpenAI API key (backward compat)
            model: Model name (used with openai_api_key fallback)
            enable_web_search: Whether to enable web search
            web_search_provider: Web search provider
            web_search_api_key: API key for web search provider
            load_full_data: If True, load full data even for large files
            llm_client: LLMClient instance (preferred — supports OpenAI, Gemini, Claude)
            db: Pre-loaded database instance (optional)
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
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm_client = LLMClient(provider="openai", api_key=api_key, model=model)
            else:
                self.llm_client = None
        elif OPENAI_AVAILABLE:
            api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self._legacy_client = OpenAI(api_key=api_key)
                self._legacy_model = model
                self.llm_client = None
            else:
                self.llm_client = None
                self._legacy_client = None
        else:
            self.llm_client = None
        self.enable_web_search = enable_web_search
        
        # Initialize web search helper
        if enable_web_search and WEB_SEARCH_AVAILABLE and WebSearchHelper:
            self.web_searcher = WebSearchHelper(
                search_provider=web_search_provider,
                api_key=web_search_api_key
            )
        else:
            self.web_searcher = None
            if enable_web_search:
                print("Note: Web search helper not available. Install web_search_helper dependencies.")
        
        # System prompt for the agent
        self.system_prompt = """You are an expert biomedical AI assistant specializing in drugs, diseases, and gene targets.
Your role is to:
1. Understand natural language queries about drugs, diseases, and targets
2. Extract key entities (drug names, gene symbols, disease names, etc.)
3. Determine the type of query (drug search, disease search, target search, association query)
4. Format query results in a clear, informative way

You have access to a comprehensive database containing:
- Drug-target-disease associations with clinical trial information
- Causal gene-disease relationships
- Oncogene and tumor suppressor gene information
- Target priority scores

When answering:
- Be precise and cite specific data
- Use proper scientific terminology
- Format results clearly with relevant details
- If information is not in the database, indicate this clearly
"""
    
    def _classify_query(self, query: str) -> Dict[str, Any]:
        """
        Use GPT to classify the query and extract entities.
        
        Returns:
            Dictionary with query_type, entities, and intent
        """
        if not self.llm_client and not getattr(self, '_legacy_client', None):
            # Fallback classification without GPT
            return self._simple_classify_query(query)
        
        classification_prompt = f"""Analyze this query about drugs, diseases, or targets: "{query}"

Classify the query and extract entities. Return a JSON object with:
- query_type: one of ["drug_search", "disease_search", "target_search", "association", "binding_affinity", "selectivity", "general_info", "statistics"]
- entities: object with keys:
  - "gene": gene symbol (e.g., "BRAF", "TP53", "EGFR") or null
  - "drug": drug name or ChEMBL ID (e.g., "vemurafenib", "CHEMBL1234") or null
  - "disease": disease name or ID (e.g., "cancer", "DOID_10113") or null
  - "phase": clinical trial phase (0.5, 1.0, 2.0, 3.0, 4.0) or null
  - "status": trial status (e.g., "Completed", "Active") or null
  - "icd_code": ICD code (e.g., "C16", "A54") or null
- intent: brief description of what the user wants

Important: Extract gene symbols in standard format (uppercase, e.g., "BRAF", "TP53", "EGFR", "KRAS", "PIK3CA")

Examples:
Query: "What drugs target BRAF?"
Response: {{"query_type": "drug_search", "entities": {{"gene": "BRAF", "drug": null, "disease": null, "phase": null, "status": null, "icd_code": null}}, "intent": "Find drugs targeting BRAF gene"}}

Query: "What diseases are associated with TP53?"
Response: {{"query_type": "disease_search", "entities": {{"gene": "TP53", "drug": null, "disease": null, "phase": null, "status": null, "icd_code": null}}, "intent": "Find diseases linked to TP53 gene"}}

Query: "Tell me about EGFR"
Response: {{"query_type": "target_search", "entities": {{"gene": "EGFR", "drug": null, "disease": null, "phase": null, "status": null, "icd_code": null}}, "intent": "Get comprehensive information about EGFR"}}

Query: "What are the Phase 3 drugs for cancer?"
Response: {{"query_type": "drug_search", "entities": {{"gene": null, "drug": null, "disease": "cancer", "phase": 3.0, "status": null, "icd_code": null}}, "intent": "Find Phase 3 drugs for cancer"}}

Query: "Tell me about BRAF and what diseases it's associated with"
Response: {{"query_type": "disease_search", "entities": {{"gene": "BRAF", "drug": null, "disease": null, "phase": null, "status": null, "icd_code": null}}, "intent": "Find diseases associated with BRAF gene"}}

Query: "What is the relationship between KRAS and lung cancer?"
Response: {{"query_type": "association", "entities": {{"gene": "KRAS", "drug": null, "disease": "lung cancer", "phase": null, "status": null, "icd_code": null}}, "intent": "Find relationship between KRAS gene and lung cancer"}}

Query: "What is the binding affinity of CHEMBL1000 to BRAF?"
Response: {{"query_type": "binding_affinity", "entities": {{"gene": "BRAF", "drug": "CHEMBL1000", "disease": null, "phase": null, "status": null, "icd_code": null}}, "intent": "Get binding affinity for drug-target pair"}}

Query: "What is the selectivity profile of vemurafenib?"
Response: {{"query_type": "selectivity", "entities": {{"gene": null, "drug": "vemurafenib", "disease": null, "phase": null, "status": null, "icd_code": null}}, "intent": "Get drug selectivity information"}}

Important: 
- Use "association" ONLY when BOTH gene and disease are mentioned
- Use "disease_search" when asking about diseases associated with a gene (even if word "associated" is used)
- Use "target_search" for general information about a gene/target
- Use "binding_affinity" when asking about binding strength/affinity between a drug and target
- Use "selectivity" when asking about drug selectivity profile or selectivity scores

Query: "{query}"
Response:"""

        try:
            messages = [
                {"role": "system", "content": "You are a query classification assistant. Return only valid JSON."},
                {"role": "user", "content": classification_prompt}
            ]
            if self.llm_client:
                response_text = self.llm_client.chat(messages, temperature=0.1, json_mode=True)
            else:
                response = self._legacy_client.chat.completions.create(
                    model=self._legacy_model, messages=messages,
                    temperature=0.1, response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content

            result = json.loads(response_text)
            return result
        except Exception as e:
            print(f"Error in query classification: {e}")
            return self._simple_classify_query(query)
    
    def _simple_classify_query(self, query: str) -> Dict[str, Any]:
        """Simple rule-based classification fallback."""
        query_lower = query.lower()
        
        # Extract common patterns
        entities = {"drug": None, "gene": None, "disease": None, "phase": None, "status": None}
        
        # Try to extract gene names first (common oncogenes/tumor suppressors)
        common_genes = ["BRAF", "EGFR", "TP53", "KRAS", "PIK3CA", "PTEN", "MYC", "HER2", "ALK", "MET"]
        for gene in common_genes:
            if gene.lower() in query_lower:
                entities["gene"] = gene
                break
        
        # Check for query type keywords
        # Check for association first (requires both entities)
        has_gene_and_disease = False
        if any(word in query_lower for word in ["associate", "link", "relate", "connect", "relationship"]):
            # Check if query mentions both gene and disease
            gene_keywords = ["gene", "target", "protein", "oncogene"]
            has_gene_mention = entities["gene"] is not None or any(word in query_lower for word in gene_keywords)
            disease_keywords = ["disease", "disorder", "condition", "syndrome", "cancer"]
            has_disease_mention = any(word in query_lower for word in disease_keywords)
            if has_gene_mention and has_disease_mention:
                query_type = "association"
                has_gene_and_disease = True
            elif has_gene_mention:
                # "associated with" + gene = disease_search
                query_type = "disease_search"
            else:
                query_type = "association"
        elif any(word in query_lower for word in ["drug", "medicine", "compound", "treatment"]):
            query_type = "drug_search"
        elif any(word in query_lower for word in ["disease", "disorder", "condition", "syndrome"]):
            query_type = "disease_search"
        elif any(word in query_lower for word in ["gene", "target", "protein", "oncogene", "tell me about"]):
            query_type = "target_search"
        elif any(word in query_lower for word in ["statistic", "summary", "overview", "count"]):
            query_type = "statistics"
        else:
            query_type = "general_info"
        
        return {
            "query_type": query_type,
            "entities": entities,
            "intent": f"Query about {query_type}"
        }
    
    def _execute_database_query(self, classification: Dict[str, Any]) -> pd.DataFrame:
        """Execute database query based on classification."""
        query_type = classification["query_type"]
        entities = classification["entities"]
        
        if query_type == "drug_search":
            if entities.get("gene"):
                gene = entities["gene"]
                print(f"   Executing: get_drugs_by_target('{gene}')")
                result = self.db.get_drugs_by_target(gene)
                print(f"   Query returned {len(result)} rows")
                return result
            elif entities.get("disease"):
                return self.db.get_drugs_by_disease(entities["disease"])
            else:
                # General drug search
                return self.db.search_drugs(
                    phase=entities.get("phase"),
                    status=entities.get("status")
                )
        
        elif query_type == "disease_search":
            if entities.get("gene"):
                return self.db.get_diseases_by_gene(entities["gene"])
            else:
                return self.db.search_diseases(
                    disease_name=entities.get("disease"),
                    icd_code=entities.get("icd_code")
                )
        
        elif query_type == "target_search":
            if entities.get("gene"):
                # Get comprehensive target info
                target_info = self.db.get_target_info(entities["gene"])
                # Convert to DataFrame for consistency
                result_data = []
                if target_info.get("drugs"):
                    for drug in target_info["drugs"]:
                        result_data.append({
                            "type": "drug",
                            "gene": entities["gene"],
                            **drug
                        })
                if target_info.get("diseases"):
                    for disease in target_info["diseases"]:
                        result_data.append({
                            "type": "disease",
                            "gene": entities["gene"],
                            **disease
                        })
                return pd.DataFrame(result_data) if result_data else pd.DataFrame()
            else:
                return self.db.search_targets(
                    target_name=entities.get("target")
                )
        
        elif query_type == "association":
            # Association queries need both entities
            if entities.get("gene") and entities.get("disease"):
                return self.db.get_disease_target_associations(
                    disease_id=entities.get("disease"),
                    gene=entities.get("gene")
                )
            elif entities.get("drug") and entities.get("disease"):
                return self.db.get_drug_disease_associations(
                    drug_id=entities.get("drug"),
                    disease_id=entities.get("disease")
                )
            # If only gene is present, treat as disease_search to find associated diseases
            elif entities.get("gene"):
                print(f"   Note: Association query with only gene, treating as disease search for {entities.get('gene')}")
                return self.db.get_diseases_by_gene(entities.get("gene"))
            # If only disease is present, treat as target_search to find associated targets
            elif entities.get("disease"):
                print(f"   Note: Association query with only disease, treating as target search for {entities.get('disease')}")
                return self.db.search_targets(disease_id=entities.get("disease"))
            else:
                return pd.DataFrame()
        
        elif query_type == "binding_affinity":
            drug_id = entities.get("drug")
            gene = entities.get("gene")
            if drug_id and gene:
                # Try to get ChEMBL ID if drug name provided
                if not drug_id.startswith("CHEMBL"):
                    # Try to find drug ID from name
                    drugs = self.db.search_drugs()
                    if not drugs.empty and 'drugId' in drugs.columns:
                        drug_match = drugs[drugs['drugId'].str.contains(drug_id, case=False, na=False)]
                        if not drug_match.empty:
                            drug_id = drug_match.iloc[0]['drugId']
                
                binding = self.db.get_drug_target_binding_affinity(drug_id, gene)
                if binding:
                    # Convert to DataFrame for consistent handling
                    return pd.DataFrame([binding])
            return pd.DataFrame()
        
        elif query_type == "selectivity":
            drug_id = entities.get("drug")
            drug_name = entities.get("drug")
            if drug_id or drug_name:
                # Try to get ChEMBL ID if drug name provided
                if drug_name and not drug_name.startswith("CHEMBL"):
                    drugs = self.db.search_drugs()
                    if not drugs.empty and 'drugId' in drugs.columns:
                        drug_match = drugs[drugs['drugId'].str.contains(drug_name, case=False, na=False)]
                        if not drug_match.empty:
                            drug_id = drug_match.iloc[0]['drugId']
                
                selectivity = self.db.get_drug_selectivity_info(drug_id=drug_id, drug_name=drug_name)
                if selectivity:
                    # Convert to DataFrame for consistent handling
                    return pd.DataFrame([selectivity])
            return pd.DataFrame()
        
        elif query_type == "statistics":
            stats = self.db.get_statistics()
            # Convert stats to DataFrame for display
            stats_list = []
            for category, data in stats.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        stats_list.append({
                            "category": category,
                            "metric": key,
                            "value": value
                        })
            return pd.DataFrame(stats_list)
        
        return pd.DataFrame()
    
    def _format_results(self, query: str, classification: Dict[str, Any], 
                       results: pd.DataFrame, web_context: Optional[str] = None) -> str:
        """Format query results using GPT."""
        if not self.llm_client and not getattr(self, '_legacy_client', None):
            return self._simple_format_results(results, classification)
        
        # Prepare results summary
        if results.empty:
            results_text = "No results found in the database."
        else:
            results_text = f"Found {len(results)} results:\n"
            # Include sample of results - limit columns for readability
            display_cols = ['drugId', 'Gene', 'targetName', 'mechanismOfAction', 'diseaseId', 'subject_label', 'phase', 'status']
            available_cols = [col for col in display_cols if col in results.columns]
            
            if len(results) <= 20:
                if available_cols:
                    results_text += results[available_cols].to_string()
                else:
                    results_text += results.to_string()
            else:
                results_text += f"Showing first 10 of {len(results)} results:\n"
                if available_cols:
                    results_text += results[available_cols].head(10).to_string()
                else:
                    results_text += results.head(10).to_string()
                results_text += f"\n... and {len(results) - 10} more results"
        
        formatting_prompt = f"""Based on the user's query and the database results, provide a clear, informative answer.

User Query: "{query}"

Query Intent: {classification.get('intent', 'Unknown')}
Query Type: {classification.get('query_type', 'Unknown')}

Database Results:
{results_text}

{"Additional Web Context: " + web_context if web_context else ""}

Instructions:
1. Provide a clear, natural language answer
2. Include specific details from the database results
3. Use proper scientific terminology
4. If results are empty, suggest alternative queries or explain why no results were found
5. Format lists and tables clearly
6. If web context is provided, integrate it naturally

Answer:"""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": formatting_prompt}
            ]
            if self.llm_client:
                return self.llm_client.chat(messages, temperature=0.3)
            else:
                response = self._legacy_client.chat.completions.create(
                    model=self._legacy_model, messages=messages, temperature=0.3
                )
                return response.choices[0].message.content
        except Exception as e:
            print(f"Error in result formatting: {e}")
            return self._simple_format_results(results, classification)
    
    def _simple_format_results(self, results: pd.DataFrame, classification: Dict[str, Any]) -> str:
        """Simple formatting without GPT."""
        if results.empty:
            return f"No results found for {classification.get('intent', 'your query')}."
        
        response = f"Found {len(results)} results:\n\n"
        
        if len(results) <= 10:
            response += results.to_string()
        else:
            response += results.head(10).to_string()
            response += f"\n\n... and {len(results) - 10} more results"
        
        return response
    
    def _web_search(self, query: str, entities: Dict[str, Any]) -> Optional[str]:
        """Perform web search for additional context."""
        if not self.enable_web_search or not self.web_searcher:
            return None
        
        # Determine search query
        search_queries = []
        
        if entities.get("gene"):
            search_queries.append(f"{entities['gene']} gene function mechanism disease")
        if entities.get("disease"):
            search_queries.append(f"{entities['disease']} disease treatment drugs")
        if entities.get("drug"):
            search_queries.append(f"{entities['drug']} drug mechanism action target")
        
        # If no specific entities, use the original query
        if not search_queries:
            search_queries = [query]
        
        # Use the first search query
        search_query = search_queries[0]
        
        try:
            results = self.web_searcher.search(search_query, num_results=3)
            if results:
                return f"Additional context from web search:\n\n{results}"
            return None
        except Exception as e:
            print(f"Web search error: {e}")
            return None
    
    def query(self, user_query: str, use_web_search: Optional[bool] = None) -> QueryResult:
        """
        Process a natural language query.
        
        Args:
            user_query: Natural language query
            use_web_search: Override default web search setting
        
        Returns:
            QueryResult object with formatted response
        """
        # Classify query
        print(f"\n🔍 Analyzing query: {user_query}")
        classification = self._classify_query(user_query)
        print(f"   Query type: {classification['query_type']}")
        print(f"   Entities: {classification['entities']}")
        
        # Execute database query
        print("📊 Querying database...")
        results = self._execute_database_query(classification)
        print(f"   Found {len(results)} results")
        if not results.empty:
            print(f"   Sample columns: {list(results.columns)[:5]}")
            print(f"   First result preview:")
            print(f"   {results.head(1).to_string() if len(results) > 0 else 'N/A'}")
        
        # Web search if needed and enabled
        web_context = None
        needs_web = False
        if use_web_search if use_web_search is not None else self.enable_web_search:
            if results.empty or classification.get('query_type') == 'general_info':
                print("🌐 Searching web for additional context...")
                web_context = self._web_search(user_query, classification['entities'])
                needs_web = web_context is not None
        
        # Format results
        print("📝 Formatting response...")
        formatted_response = self._format_results(
            user_query, 
            classification, 
            results, 
            web_context
        )
        
        # Debug: Show what we're returning
        if results.empty:
            print("   ⚠️  Warning: No results found in database!")
            print(f"   Query was: {classification['query_type']} with entities: {classification['entities']}")
        else:
            print(f"   ✅ Successfully formatted {len(results)} results")
        
        return QueryResult(
            query_type=classification['query_type'],
            data=results,
            summary=formatted_response,
            sources=["database"],
            needs_web_search=needs_web,
            web_context=web_context
        )
    
    def chat(self, user_query: str) -> str:
        """
        Simple chat interface that returns just the formatted response.
        
        Args:
            user_query: Natural language query
        
        Returns:
            Formatted response string
        """
        result = self.query(user_query)
        return result.summary


# Convenience function
def create_agent(database_dir: str = "Database",
                openai_api_key: Optional[str] = None,
                model: str = "gpt-4o-mini",
                enable_web_search: bool = True,
                web_search_provider: str = "duckduckgo",
                web_search_api_key: Optional[str] = None,
                load_full_data: bool = True) -> DrugDiseaseTargetAgent:
    """
    Create and return a configured agent.
    
    Args:
        database_dir: Path to database directory
        openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        model: OpenAI model to use
        enable_web_search: Whether to enable web search for additional context
        web_search_provider: Web search provider ("duckduckgo", "serpapi", "google", "bing")
        web_search_api_key: API key for web search provider
        load_full_data: If True, load full data even for large files (>200MB).
                       If False, sample large files to 100,000 rows for performance.
    
    Returns:
        DrugDiseaseTargetAgent instance
    """
    return DrugDiseaseTargetAgent(
        database_dir=database_dir,
        openai_api_key=openai_api_key,
        model=model,
        enable_web_search=enable_web_search,
        web_search_provider=web_search_provider,
        web_search_api_key=web_search_api_key,
        load_full_data=load_full_data
    )
