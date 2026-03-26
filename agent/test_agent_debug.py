"""
Debug script to test the agent query flow
"""

from .database_query_module import load_database
from .llm_agent import DrugDiseaseTargetAgent
import os

# Test direct database query
print("=" * 80)
print("TEST 1: Direct Database Query")
print("=" * 80)
db = load_database("Database")
drugs = db.get_drugs_by_target("BRAF")
print(f"Direct query result: {len(drugs)} rows")
if not drugs.empty:
    print(f"Columns: {list(drugs.columns)}")
    print(f"\nFirst 3 rows:")
    print(drugs.head(3))
else:
    print("No results found!")

# Test agent query
print("\n" + "=" * 80)
print("TEST 2: Agent Query")
print("=" * 80)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  OPENAI_API_KEY not set. Testing without GPT...")
    # Test classification only
    agent = DrugDiseaseTargetAgent(
        database_dir="Database",
        openai_api_key=None,
        model="gpt-4o-mini",
        enable_web_search=False
    )
    # Force it to use simple classification
    agent.client = None
    
    classification = agent._classify_query("What drugs target BRAF?")
    print(f"Classification: {classification}")
    
    results = agent._execute_database_query(classification)
    print(f"Agent query result: {len(results)} rows")
    if not results.empty:
        print(f"Columns: {list(results.columns)}")
        print(f"\nFirst 3 rows:")
        print(results.head(3))
    else:
        print("No results found!")
else:
    print("✅ OpenAI API key found. Testing with GPT...")
    agent = DrugDiseaseTargetAgent(
        database_dir="Database",
        openai_api_key=api_key,
        model="gpt-4o-mini",
        enable_web_search=False
    )
    
    result = agent.query("What drugs target BRAF?")
    print(f"\nQuery result summary:")
    print(result.summary)
    print(f"\nRaw data: {len(result.data)} rows")
    if not result.data.empty:
        print(result.data.head(3))
