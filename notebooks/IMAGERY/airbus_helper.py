import json
import os
import requests

import pandas as pd
import geopandas as gpd

from datetime import datetime
from pathlib import Path
from shapely.geometry import shape


def get_api_key(key_name: str, file_path: str = "api_keys.json") -> str:
    """
    Read an API key from a JSON file. If the key doesn't exist, prompt the user
    to enter it and store it in the file.
    
    Args:
        key_name: The name of the API key to retrieve
        file_path: Path to the JSON file storing API keys (default: api_keys.json)
    
    Returns:
        The API key string
    """
    file_path = Path(file_path)
    
    # Load existing keys if file exists
    if file_path.exists():
        with open(file_path, "r") as f:
            keys = json.load(f)
    else:
        keys = {}
    
    # Return key if it exists
    if key_name in keys:
        return keys[key_name]
    
    # Prompt user for new key
    api_key = input(f"Enter {key_name}: ").strip()
    
    # Store key in file
    keys[key_name] = api_key
    with open(file_path, "w") as f:
        json.dump(keys, f, indent=2)
    
    return api_key

def get_airbus_token(api_token: str, token_endpoint: str = "https://authenticate.foundation.api.oneatlas.airbus.com/auth/realms/IDP/protocol/openid-connect/token") -> str:
    """
    Get an access token from the Airbus API using the provided API token.
    
    Args:
        api_token: The API token for authentication
        token_endpoint: The endpoint URL to obtain the access token
    
    Returns:
        The access token string
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    data = [
        ('apikey', api_token),
        ('grant_type', 'api_key'),
        ('client_id', 'IDP'),
    ]

    response = requests.post(token_endpoint, headers=headers, data=data)
    access_token = response.json().get('access_token')
    return access_token

def search_airbus_imagery(access_token: str, bbox: str, 
                          search_endpoint: str = "https://search.foundation.api.oneatlas.airbus.com/api/v2/opensearch", 
                          query_params: dict = None) -> dict:
    """
    Search for imagery using the Airbus API with the provided access token and query parameters.
    
    Args:
        access_token: The access token for authentication
        bbox: The bounding box for the search (format str: "minLon,minLat,maxLon,maxLat")
        search_endpoint: The endpoint URL for searching imagery
        query_params: A dictionary of query parameters for the search
    
    Returns:
        The search results as a dictionary
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    if query_params is None:
        query_params = {
            "itemsPerPage": 100,
            "startPage": 1,
            "cloudCover": "[0,30]",
            "incidenceAngle": "[0,40]",
            "relation": "intersects",
            'constellation': ["PHR", "PNEO"],
            'productType':'mono',
            "bbox": bbox
        }

    # The response may require pagination handling if there are many result
    response = requests.post(search_endpoint, json=query_params, headers=headers)
    itemsPerPage = response.json().get('itemsPerPage', 100)
    total_results = response.json().get('totalResults', 0)
    all_results = response.json().get('features', [])        
    if total_results > itemsPerPage:
        cPage = 1
        while len(all_results) < total_results:
            cPage += 1
            query_params['startPage'] = cPage
            response = requests.post(search_endpoint, json=query_params, headers=headers)
            try:
                all_results.extend(response.json().get('features', []))
            except:
                print(f"Error in response: {response.status_code} - {response.text}")
                break
    
    all_res = []
    try:
        for image in all_results:
            try:
                del image['properties']['geometryCentroid']
            except:
                pass
            image['properties']['geometry'] = shape(image['geometry'])
            c_res = pd.DataFrame(image['properties'], index=[0])
            all_res.append(c_res)

        image_df = pd.concat(all_res)
        # convert to geodataframe
        image_gdf = gpd.GeoDataFrame(image_df, geometry='geometry', crs=4326)
        # convert acquisitionDate to datetime
        image_gdf['acquisitionDate'] = [datetime.fromisoformat(x[:10]) for x in image_gdf['acquisitionDate']]
        return image_gdf    
    except:
        print("Error processing search results")
        return all_results