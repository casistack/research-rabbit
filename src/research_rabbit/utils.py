from langsmith import traceable
from tavily import TavilyClient
import requests
from typing import Literal, Optional, Union, Dict, List

class SearxngClient:
    """Client for interacting with a SearXNG instance."""
    
    def __init__(self, base_url: str):
        """Initialize SearxNG client.
        
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
        raise ValueError(f"Unsupported search provider: {search_provider}. Must be either 'tavily' or 'searxng'.")

def deduplicate_and_format_sources(search_response, max_tokens_per_source, include_raw_content=True):
    """
    Takes either a single search response or list of responses from Tavily API and formats them.
    Limits the raw_content to approximately max_tokens_per_source.
    include_raw_content specifies whether to include the raw_content from Tavily in the formatted string.
    
    Args:
        search_response: Either:
            - A dict with a 'results' key containing a list of search results
            - A list of dicts, each containing search results
            
    Returns:
        str: Formatted string with deduplicated sources
    """
    # Convert input to list of results
    if isinstance(search_response, dict):
        sources_list = search_response['results']
    elif isinstance(search_response, list):
        sources_list = []
        for response in search_response:
            if isinstance(response, dict) and 'results' in response:
                sources_list.extend(response['results'])
            else:
                sources_list.extend(response)
    else:
        raise ValueError("Input must be either a dict with 'results' or a list of search results")
    
    # Deduplicate by URL
    unique_sources = {}
    for source in sources_list:
        if source['url'] not in unique_sources:
            unique_sources[source['url']] = source
    
    # Format output
    formatted_text = "Sources:\n\n"
    for i, source in enumerate(unique_sources.values(), 1):
        formatted_text += f"Source {source['title']}:\n===\n"
        formatted_text += f"URL: {source['url']}\n===\n"
        formatted_text += f"Most relevant content from source: {source['content']}\n===\n"
        if include_raw_content:
            # Using rough estimate of 4 characters per token
            char_limit = max_tokens_per_source * 4
            # Handle None raw_content
            raw_content = source.get('raw_content', '')
            if raw_content is None:
                raw_content = ''
                print(f"Warning: No raw_content found for source {source['url']}")
            if len(raw_content) > char_limit:
                raw_content = raw_content[:char_limit] + "... [truncated]"
            formatted_text += f"Full source content limited to {max_tokens_per_source} tokens: {raw_content}\n\n"
                
    return formatted_text.strip()

def format_sources(search_results):
    """Format search results into a bullet-point list of sources.
    
    Args:
        search_results (dict): Tavily search response containing results
        
    Returns:
        str: Formatted string with sources and their URLs
    """
    return '\n'.join(
        f"* {source['title']} : {source['url']}"
        for source in search_results['results']
    )
