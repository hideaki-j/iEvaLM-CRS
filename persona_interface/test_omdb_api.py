import requests
import os

# Replace this with your actual OMDb API key
API_KEY = os.environ.get('OMDB_API_KEY')
if API_KEY is None:
    raise ValueError("OMDB_API_KEY environment variable is not set")
else:
    print(f"DEBUG: OMDB_API_KEY environment variable is set to: {API_KEY}")

# NOTE: OMDB API key is not working...

dummy_query = 'Take Off Your Clothes and Live!'

def omdb_search(query, limit=10):
    print(f"DEBUG: Entering omdb_search with query: {query}, limit: {limit}")
    api_url = "http://www.omdbapi.com/"
    params = {
        "apikey": API_KEY,
        "s": query,
        "type": "movie",
    }

    print("DEBUG: Sending API request for search")
    response = requests.get(api_url, params=params)
    print(f"DEBUG: API response status code: {response.status_code}")
    
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"DEBUG: Failed to decode JSON. Raw response: {response.text}")
        return []

    print(f"DEBUG: Full API response: {data}")

    if data.get("Response") == "True":
        results = []
        for item in data["Search"][:limit]:
            results.append({
                "title": item["Title"],
                "year": item["Year"],
                "imdb_id": item["imdbID"],
            })
        print(f"DEBUG: Search successful. Found {len(results)} results")
        return results
    else:
        error_message = data.get("Error", "Unknown error")
        print(f"DEBUG: Search failed or no results found. Error: {error_message}")
        return []

def get_movie_details(imdb_id):
    print(f"DEBUG: Entering get_movie_details with imdb_id: {imdb_id}")
    api_url = "http://www.omdbapi.com/"
    params = {
        "apikey": API_KEY,
        "i": imdb_id,
        "plot": "full",
    }

    print("DEBUG: Sending API request for movie details")
    response = requests.get(api_url, params=params)
    data = response.json()

    if data.get("Response") == "True":
        print("DEBUG: Successfully retrieved movie details")
        return {
            "title": data["Title"],
            "year": data["Year"],
            "rated": data["Rated"],
            "released": data["Released"],
            "runtime": data["Runtime"],
            "genre": data["Genre"],
            "director": data["Director"],
            "writer": data["Writer"],
            "actors": data["Actors"],
            "plot": data["Plot"],
            "awards": data["Awards"],
            "poster": data["Poster"],
            "imdb_rating": data["imdbRating"],
            "imdb_votes": data["imdbVotes"],
            "imdb_id": data["imdbID"],
        }
    else:
        print("DEBUG: Failed to retrieve movie details")
        return None

def omdb_search_with_details(query, limit=1):
    print(f"DEBUG: Entering omdb_search_with_details with query: {query}, limit: {limit}")
    search_results = omdb_search(query, limit)
    detailed_results = []
    for result in search_results:
        details = get_movie_details(result["imdb_id"])
        if details:
            detailed_results.append(details)
    print(f"DEBUG: Found {len(detailed_results)} detailed results")
    return detailed_results

# Perform the search and print the results
print(f"DEBUG: Starting search with dummy query: {dummy_query}")
search_results = omdb_search_with_details(dummy_query)
for result in search_results:
    print(f"Title: {result['title']}")
    print(f"Year: {result['year']}")
    print(f"Director: {result['director']}")
    print(f"IMDb Rating: {result['imdb_rating']}")
    print(f"Plot: {result['plot'][:500]}...")
    print()

print("DEBUG: Search and result printing completed")
