from langsmith import traceable
from tavily import TavilyClient
import requests
from typing import Literal, Optional, Union, Dict, List

class SearxngClient:
    """Client for interacting with a SearXNG instance."""
    
    def __init__(self, base_url: str):
        """Initialize SearXNG client.
        
        Args:
            base_url (str): Base URL of the SearXNG instance (e.g., 'http://localhost:8888')
        """
        self.base_url = base_url.rstrip('/')
        
    def search(self, query: str, max_results: int = 3, include_raw_content: bool = True) -> Dict:
        """Perform a search using SearXNG.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            include_raw_content (bool): Whether to fetch full page content (not implemented for SearXNG)
            
        Returns:
            dict: Search results in a format compatible with Tavily's response
        """
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={
                    'q': query,
                    'format': 'json',
                    'engines': 'google,bing,duckduckgo',
                    'max_results': max_results
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Convert SearXNG results to Tavily-compatible format
            results = []
            for result in data.get('results', [])[:max_results]:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', ''),
                    'raw_content': None  # SearXNG doesn't provide full content
                })
            
            return {'results': results}
            
        except requests.RequestException as e:
            raise Exception(f"SearXNG search failed: {str(e)}")

@traceable
def web_search(
    query: str,
    search_provider: Literal["tavily", "searxng"] = "tavily",
    searxng_url: Optional[str] = None,
    include_raw_content: bool = True,
    max_results: int = 3
) -> Dict:
    """Unified search function supporting both Tavily and SearXNG.
    
    Args:
        query (str): The search query to execute
        search_provider (str): Either "tavily" or "searxng"
        searxng_url (str, optional): Base URL for SearXNG instance if using SearXNG
        include_raw_content (bool): Whether to include raw content (only applicable for Tavily)
        max_results (int): Maximum number of results to return
        
    Returns:
        dict: Search response containing results in Tavily-compatible format
    """
    if search_provider == "tavily":
        tavily_client = TavilyClient()
        return tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content
        )
    elif search_provider == "searxng":
        if not searxng_url:
            raise ValueError("searxng_url must be provided when using SearXNG")
        searxng_client = SearxngClient(searxng_url)
        return searxng_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content
        )
    else:
        raise ValueError(f"Unsupported search provider: {search_provider}")

def deduplicate_and_format_sources(search_results: Dict, max_tokens_per_source: int = 1000) -> str:
    """Format and deduplicate search results."""
    results = search_results.get('results', [])
    formatted_results = []
    
    for result in results:
        content = result.get('raw_content') if result.get('raw_content') else result.get('content', '')
        if content:
            formatted_results.append(
                f"Source: {result.get('url', '')}\n"
                f"Title: {result.get('title', '')}\n"
                f"Content: {content[:max_tokens_per_source]}"
            )
    
    return "\n\n".join(formatted_results)

def format_sources(search_results: Dict) -> str:
    """Format sources for citation."""
    sources = []
    for result in search_results.get('results', []):
        sources.append(f"- {result.get('title', 'Untitled')} ({result.get('url', '')})")
    return "\n".join(sources)
