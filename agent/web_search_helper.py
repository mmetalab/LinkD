"""
Web Search Helper Module

This module provides web search functionality that can be integrated
with the LLM agent for fetching additional context.
"""

import os
from typing import Optional, List, Dict
import requests


class WebSearchHelper:
    """Helper class for web search integration."""
    
    def __init__(self, search_provider: str = "serpapi", api_key: Optional[str] = None):
        """
        Initialize web search helper.
        
        Args:
            search_provider: "serpapi", "google", "bing", or "duckduckgo"
            api_key: API key for the search provider
        """
        self.search_provider = search_provider.lower()
        self.api_key = api_key or os.getenv(f"{search_provider.upper()}_API_KEY")
    
    def search(self, query: str, num_results: int = 5) -> Optional[str]:
        """
        Perform web search and return formatted results.
        
        Args:
            query: Search query
            num_results: Number of results to return
        
        Returns:
            Formatted search results as string, or None if search fails
        """
        if self.search_provider == "serpapi":
            return self._serpapi_search(query, num_results)
        elif self.search_provider == "google":
            return self._google_search(query, num_results)
        elif self.search_provider == "bing":
            return self._bing_search(query, num_results)
        elif self.search_provider == "duckduckgo":
            return self._duckduckgo_search(query, num_results)
        else:
            print(f"Unknown search provider: {self.search_provider}")
            return None
    
    def _serpapi_search(self, query: str, num_results: int) -> Optional[str]:
        """Search using SerpAPI."""
        if not self.api_key:
            print("SerpAPI key not found. Set SERPAPI_API_KEY environment variable.")
            return None
        
        try:
            import serpapi
            from serpapi import GoogleSearch
            
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "engine": "google"
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "organic_results" in results:
                formatted = []
                for result in results["organic_results"][:num_results]:
                    title = result.get("title", "")
                    snippet = result.get("snippet", "")
                    link = result.get("link", "")
                    formatted.append(f"- {title}\n  {snippet}\n  Source: {link}")
                
                return "\n\n".join(formatted)
            
            return None
        except ImportError:
            print("serpapi package not installed. Install with: pip install google-search-results")
            return None
        except Exception as e:
            print(f"SerpAPI search error: {e}")
            return None
    
    def _google_search(self, query: str, num_results: int) -> Optional[str]:
        """Search using Google Custom Search API."""
        if not self.api_key:
            print("Google API key not found. Set GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables.")
            return None
        
        cse_id = os.getenv("GOOGLE_CSE_ID")
        if not cse_id:
            print("Google CSE ID not found. Set GOOGLE_CSE_ID environment variable.")
            return None
        
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": cse_id,
                "q": query,
                "num": min(num_results, 10)  # Google API max is 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "items" in data:
                formatted = []
                for item in data["items"][:num_results]:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    link = item.get("link", "")
                    formatted.append(f"- {title}\n  {snippet}\n  Source: {link}")
                
                return "\n\n".join(formatted)
            
            return None
        except Exception as e:
            print(f"Google search error: {e}")
            return None
    
    def _bing_search(self, query: str, num_results: int) -> Optional[str]:
        """Search using Bing Search API."""
        if not self.api_key:
            print("Bing API key not found. Set BING_API_KEY environment variable.")
            return None
        
        try:
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            params = {"q": query, "count": num_results}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "webPages" in data and "value" in data["webPages"]:
                formatted = []
                for item in data["webPages"]["value"][:num_results]:
                    title = item.get("name", "")
                    snippet = item.get("snippet", "")
                    link = item.get("url", "")
                    formatted.append(f"- {title}\n  {snippet}\n  Source: {link}")
                
                return "\n\n".join(formatted)
            
            return None
        except Exception as e:
            print(f"Bing search error: {e}")
            return None
    
    def _duckduckgo_search(self, query: str, num_results: int) -> Optional[str]:
        """Search using DuckDuckGo (no API key required)."""
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))
                
                formatted = []
                for result in results[:num_results]:
                    title = result.get("title", "")
                    body = result.get("body", "")
                    href = result.get("href", "")
                    formatted.append(f"- {title}\n  {body}\n  Source: {href}")
                
                return "\n\n".join(formatted) if formatted else None
        except ImportError:
            print("duckduckgo_search package not installed. Install with: pip install duckduckgo-search")
            return None
        except Exception as e:
            print(f"DuckDuckGo search error: {e}")
            return None


# Convenience function
def create_web_searcher(provider: str = "duckduckgo", api_key: Optional[str] = None) -> WebSearchHelper:
    """Create a web search helper."""
    return WebSearchHelper(search_provider=provider, api_key=api_key)
