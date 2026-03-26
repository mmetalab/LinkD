# Methods

## LinkD: Multi-Evidence Supported Drug Discovery Platform

### System Overview

LinkD is an AI-powered platform designed to integrate and query multi-source biomedical data for drug-disease-target associations. The platform provides four interconnected modules:

- **LinkD-DTI**: Drug-target interaction binding affinity analysis (1,068 targets with pKd values)
- **LinkD-Select**: Drug selectivity profiling via UMAP clustering (14,981 drugs)
- **LinkD-Pheno**: Phenotype-drug associations from electronic health records (41K+ associations)
- **LinkD-Agent**: AI-powered multi-step analysis using LLMs (OpenAI, Google Gemini, Anthropic Claude)

The system combines structured database queries with large language model capabilities to enable natural language querying and multi-step analysis planning. The web interface is built with FastAPI (Python backend) and React with TypeScript (frontend), serving interactive Plotly.js visualizations.

### Core Modules

#### 1. Database Query Module (`database_query_module.py`)

The database query module serves as the foundational data access layer, providing programmatic access to multiple integrated data sources.

**Data Sources Integrated:**

- **Drug-Target-Disease Associations**: Clinical trial data including 276,147 records covering 4,274 unique drugs, 1,520 targets, and 2,684 diseases across clinical phases (0.5-4.0)
- **Causal Gene-Disease Associations**: 13,008 records linking 3,400 genes to 3,859 diseases with causal mutation annotations
- **Oncogene Information**: 1,029 oncogenes and tumor suppressor genes with role classifications
- **Drug-Target Binding Affinity Metrics**: Predicted binding affinities (pKd values) and selectivity scores for ~15,000 drugs across 20,000+ targets, stored in memory-efficient parquet format
- **Electronic Health Records (EHR)**: 
  - Mount Sinai cohort: Drug-disease associations with statistical measures (odds ratios, hazard ratios)
  - UK Biobank cohort: Drug-cancer associations with epidemiological evidence
- **Drug Response Data**: CRISPR gene knockout correlations with drug response metrics (AUC, IC50) from PRISM and GDSC datasets

**Key Functions:**

The module implements 30+ query functions organized into categories:
- Drug queries: `search_drugs()`, `get_drugs_by_target()`, `get_drugs_by_disease()`
- Disease queries: `search_diseases()`, `get_diseases_by_gene()`
- Target queries: `search_targets()`, `get_target_info()`
- Association queries: `get_drug_disease_associations()`, `get_disease_target_associations()`, `get_causal_gene_disease_associations()`
- Binding affinity queries: `get_drug_target_binding_affinity()`, `get_targets_for_drug_with_affinity()`, `get_target_binding_stats()`
- Selectivity queries: `get_drug_selectivity_info()`, `get_drugs_by_selectivity_type()`
- EHR queries: `get_ehr_drug_disease_associations()`, `assess_prevention_risk()`
- Drug response queries: `get_drug_response_associations()`, `get_drug_target_evidence()`
- Evidence aggregation: `get_comprehensive_drug_target_evidence()`

**Memory Management:**

For large datasets (>200MB), the module implements configurable loading strategies:
- Full data loading: Complete dataset in memory for comprehensive queries
- On-demand loading: Parquet files loaded only when specific queries require them
- Sampling mode: Optional 100,000-row sampling for rapid exploration

#### 2. LLM Agent Module (`llm_agent.py`)

The LLM agent module provides natural language understanding and query routing using OpenAI's GPT models.

**Architecture:**

- **Query Classification**: Uses GPT-4o or GPT-4o-mini to classify queries into types:
  - `drug_search`: Find drugs by target, disease, or properties
  - `disease_search`: Find diseases by gene or name
  - `target_search`: Find targets/genes by name or disease
  - `association`: Find relationships between entities
  - `binding_affinity`: Query drug-target binding affinities
  - `selectivity`: Query drug selectivity metrics
- **Entity Extraction**: Extracts drug IDs (ChEMBL), gene names, disease names, ICD codes, and clinical trial phases from natural language
- **Query Routing**: Automatically routes classified queries to appropriate database functions
- **Result Formatting**: Uses GPT to format structured database results into natural language summaries

**Fallback Mechanism:**

When GPT is unavailable, the module uses rule-based classification with:
- Pattern matching for common query structures
- Gene name extraction from curated lists
- Keyword-based classification

**Web Search Integration:**

Optional web search capability (via `web_search_helper.py`) supports multiple providers:
- DuckDuckGo (no API key required)
- SerpAPI
- Google Custom Search
- Bing Search

#### 3. LLM Planning Agent Module (`llm_planning_agent.py`)

The planning agent extends the LLM agent with multi-step analysis capabilities.

**Planning Process:**

1. **Plan Generation**: Given a natural language query, GPT generates a structured analysis plan with:
   - Step-by-step analysis tasks
   - Required data sources for each step
   - Logical sequencing of queries

2. **Plan Execution**: Executes steps sequentially, tracking:
   - Step status (pending, in_progress, completed, failed)
   - Step results
   - Error handling

3. **Multi-Source Integration**: Combines evidence from:
   - Binding affinity data (predicted pKd values, selectivity scores)
   - EHR data (real-world associations, odds ratios)
   - Drug response data (CRISPR correlations, AUC/IC50)
   - Clinical trial data (phases, status)
   - Causal gene-disease associations

4. **Summary Generation**: Uses GPT to synthesize results from all steps into a comprehensive analysis summary

**Data Structure:**

- `AnalysisPlan`: Container for query and list of `PlanStep` objects
- `PlanStep`: Individual step with description, data sources, status, and results

#### 4. Interactive Web Server (`interactive_web_server/app.py`)

The web server provides a user-friendly interface built with Gradio.

**Features:**

- **Query Interface**: Natural language query input with example queries
- **Plan Visualization**: Real-time display of generated analysis plans
- **Execution Tracking**: Live progress updates showing:
  - Current step being executed
  - Completed steps
  - Processed time for each step and total execution
- **Results Display**: Formatted results with:
  - Analysis results summary (bullet points with findings)
  - LLM-generated comprehensive summary
  - Processing details and timing information
- **History**: Execution history tracking for previous queries

**Technical Implementation:**

- Built with Gradio 6.0+ for web interface
- Custom CSS for styling (Helvetica font, color-coded status)
- Generator functions for real-time updates
- Markdown-to-HTML conversion for formatted summaries
- Configurable port and public link sharing

### Data Integration Pipeline

#### Data Loading Strategy

1. **Initialization**: Database module loads all CSV files into pandas DataFrames
2. **Large File Handling**: Files >200MB can be sampled (100K rows) or loaded fully based on `load_full_data` parameter
3. **Parquet File Handling**: Target-centric binding affinity data stored in 100 parquet files, loaded on-demand for specific queries
4. **Memory Efficiency**: On-demand loading prevents memory overflow for 20,000+ target datasets

#### Data Normalization

- Drug IDs standardized to ChEMBL format
- Gene names normalized to standard symbols
- Disease names mapped to ICD codes where applicable
- Clinical trial phases standardized (0.5, 1.0, 2.0, 3.0, 4.0)

### Query Processing Pipeline

#### Natural Language Query Flow

1. **Input**: User provides natural language query (e.g., "Analyze vemurafenib targeting BRAF with binding affinity and EHR evidence")

2. **LLM Processing**:
   - Query classification via GPT
   - Entity extraction (drug IDs, genes, diseases)
   - Intent understanding

3. **Plan Generation** (Planning Agent):
   - GPT generates step-by-step plan
   - Identifies required data sources
   - Sequences logical analysis steps

4. **Execution**:
   - Each step queries appropriate database functions
   - Results aggregated per step
   - Status tracked in real-time

5. **Synthesis**:
   - GPT generates comprehensive summary
   - Results formatted for display
   - Evidence from multiple sources integrated

#### Query Types Supported

- **Simple Queries**: Single-entity lookups (e.g., "What drugs target BRAF?")
- **Association Queries**: Relationship discovery (e.g., "What diseases are associated with TP53?")
- **Multi-Source Queries**: Evidence aggregation (e.g., "Analyze erlotinib with binding affinity, drug response, and EHR data")
- **Complex Analysis**: Multi-step investigations (e.g., "Prioritize targets for EGFR with comprehensive evidence")

### Technical Specifications

**Programming Language**: Python 3.7+

**Core Dependencies**:
- pandas: Data manipulation and querying
- numpy: Numerical computations
- openai: GPT model integration
- gradio: Web interface framework

**Data Formats**:
- CSV: Primary data storage format
- Parquet: Efficient storage for large binding affinity datasets
- JSON: Configuration and API responses

**LLM Models**:
- Primary: GPT-4o-mini (cost-effective, fast)
- Alternative: GPT-4o (higher quality, slower)

### Validation and Quality Assurance

**Data Validation**:
- File existence checks before loading
- Column presence validation
- Data type consistency checks
- Missing value handling

**Error Handling**:
- Graceful degradation when GPT unavailable
- Fallback to rule-based classification
- Error messages for missing data
- Step failure tracking in planning agent

**Performance Optimization**:
- Configurable data sampling for large files
- On-demand parquet file loading
- Memory-efficient query execution
- Caching of frequently accessed data structures

### Reproducibility

**Configuration**:
- Environment variables for API keys
- Configurable model selection
- Adjustable data loading strategies
- Customizable web server settings

**Documentation**:
- Comprehensive README with usage examples
- Jupyter notebooks for exploration
- Code comments and docstrings
- Technology log for change tracking
