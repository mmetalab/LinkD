"""
Example usage of the LLM Agent for Drug-Disease-Target queries

This script demonstrates how to use the natural language agent to query
the database and get formatted responses.
"""

from .llm_agent import create_agent, DrugDiseaseTargetAgent
import os

def main():
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Warning: OPENAI_API_KEY not set. Set it to use GPT features.")
        print("   You can still use the database module directly.")
        return
    
    # Create agent
    print("Initializing agent...")
    agent = create_agent(
        database_dir="Database",
        openai_api_key=api_key,
        model="gpt-4o-mini",  # Use gpt-4o-mini for cost efficiency, or gpt-4o for better results
        enable_web_search=True,  # Enable web search for additional context
        web_search_provider="duckduckgo"  # No API key needed for DuckDuckGo
    )
    
    # Example queries
    example_queries = [
        "What drugs target BRAF?",
        "What diseases are associated with TP53?",
        "Tell me about EGFR",
        "What are the Phase 3 drugs for cancer?",
        "Which oncogenes have approved drugs?",
        "What is the relationship between KRAS and lung cancer?",
    ]
    
    print("\n" + "="*80)
    print("EXAMPLE QUERIES")
    print("="*80)
    
    for i, query in enumerate(example_queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}: {query}")
        print('='*80)
        
        try:
            # Get response
            result = agent.query(query)
            
            # Print formatted response
            print("\n📋 Response:")
            print(result.summary)
            
            # Print metadata
            print(f"\n📊 Query Type: {result.query_type}")
            print(f"📈 Results Found: {len(result.data)}")
            if result.needs_web_search:
                print("🌐 Web search was used for additional context")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Interactive mode
    print("\n" + "="*80)
    print("INTERACTIVE MODE")
    print("="*80)
    print("Enter queries (type 'quit' to exit):\n")
    
    while True:
        try:
            user_query = input("Query: ").strip()
            if user_query.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_query:
                continue
            
            result = agent.query(user_query)
            print("\n" + result.summary + "\n")
            
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
