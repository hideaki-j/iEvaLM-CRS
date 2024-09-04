import os
import requests
from urllib.parse import urlparse
from persona_interface.gpt import get_gpt_response
dummy_query = 'Take Off Your Clothes and Live!'  # Removed the year for a more general search

def _check_url_validity(url: str) -> bool:
    parsed_url = urlparse(url)
    # return false if the url is not valid
    if parsed_url.netloc != "en.wikipedia.org" or parsed_url.scheme not in ("http", "https"):
        return False
    # check if that url exists
    response = requests.get(url)
    if response.status_code != 200:
        return False
    return True

def _generate_full_url_with_gpt(query: str) -> str:
    """Generate a full Wikipedia URL for a given query using GPT.

    Note:
        Knowing the difficulty of fetching a correct URL from wikipedia search API,
        utilizing GPT's memory of wikipedia pages, we can generate a full URL for a given query.
    """
    
    try:

        generated_url = get_gpt_response(
            system_prompt="You are a helpful assistant that generates Wikipedia URLs. You must only generate a full Wikipedia URL for the query. You must not generate any other text.",
            prompt=f"Generate a full Wikipedia URL for the query: {query}"
        )
        
        if _check_url_validity(generated_url):
            print(f'GPT successfully generated a valid URL {generated_url}')
            title = generated_url.split("/")[-1].replace("_", " ")
            return {"title": title, "url": generated_url}
        else:
            print(f'GPT could NOT generate a valid URL for {query}. GPT generated: {generated_url}')

    except Exception as e:
        print(f"Error in GPT URL generation: {e}")
    
    return None

# def _construct_search_string(query: str) -> str:
#     query_words = query.split()
#     search_string = ' '.join(f'intitle:{word}' for word in query_words)
#     return search_string

def _wikipedia_search(query: str, limit: int = 1) -> dict:
    assert limit == 1, "Limit 1 is only supported at the moment"
    # search_string = _construct_search_string(query)
    search_string = query
    # Define the API endpoint and parameters
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": search_string,
        "srnamespace": 0,  # Limit to main namespace
        "srlimit": limit,
        # "srprop": "snippet",
    }

    response = requests.get(api_url, params=params)
    data = response.json()

    if data["query"]["search"]:
        item = data["query"]["search"][0]
        title = item["title"]
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        if _check_url_validity(url):
            return {"title": title, "url": url}
    
    return None

def _get_full_text(title: str) -> str:
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "extracts",
        "explaintext": True,
        "exsectionformat": "plain"
    }

    response = requests.get(api_url, params=params)
    data = response.json()

    page = next(iter(data["query"]["pages"].values()))
    full_text = page.get("extract", "No text found")
    return full_text[:500]  # Return only the first 500 characters

def wikipedia_search_process(query: str) -> dict:
    # First, try to generate URL using GPT
    result = _generate_full_url_with_gpt(query)
    
    # If GPT fails, fall back to Wikipedia API search
    if result is None:
        result = _wikipedia_search(query)
    
    # If we have a result, get the full text
    if result:
        result["full_text"] = _get_full_text(result["title"])
    
    return result

# Example usage
if __name__ == "__main__":
    dummy_query = 'Take Off Your Clothes and Live!'
    result = wikipedia_search_process(dummy_query)

    if result:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Full Text (first 500 characters): {result['full_text']}")
    else:
        print("No results found.")