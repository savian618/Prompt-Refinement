# api_functions.py
import requests
import pandas as pd
import time
import datetime

idp_url = "https://harvester-api-stg.pnmac.com/v2"

def get_idp_auth_token(url, email, password):
    """
    Authenticates with the API and returns an authentication token.

    Args:
        email: The email address.
        password: The password.

    Returns:
        The authentication token, or None if authentication failed.
    """
    headers = {"Content-Type": "application/json"} 
    data = {
        "email": email,
        "password": password
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        try:
            token = response.json()["access_token"]  
            return token
        except KeyError:
            print("Error: Authentication token not found in response.")
            return None
    else:
        print(f"Error: Authentication failed with status code {response.status_code}")
        print(response.text)
        return None
    
def save_token(token, expiry_time):
  """Saves the token and expiry time to a file."""
  with open("auth_token.txt", "w") as f:
    f.write(f"{token}\n{expiry_time.timestamp()}")

def load_token():
  """Loads the token and expiry time from the file."""
  try:
    with open("auth_token.txt", "r") as f:
      token, expiry_timestamp = f.read().splitlines()
      expiry_time = datetime.datetime.fromtimestamp(float(expiry_timestamp))
      return token, expiry_time
  except FileNotFoundError:
    return None, None

def download_api_response(url, filename, headers):
    """
    Hits an API endpoint and downloads the response to a file.

    Args:
        url: The URL of the API endpoint.
        filename: The name of the file to save the response to.
    """

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 

        with open(filename, 'wb') as f:
            f.write(response.content)

        print(f"Successfully downloaded response to {filename}")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading API response: {e}")

def get_prompt(key_name, id, headers, timeout=60, retry_interval=5):
    """
    Retrieves a prompt with retry logic to handle delayed responses.

    Args:
        key_name: The name of the key to retrieve from the 'prompt-result'.
        id: The record ID.
        headers: The request headers.
        timeout: The maximum time to wait for the response (in seconds).
        retry_interval: The time interval between retries (in seconds).

    Returns:
        The retrieved API key, or None if the key is not found or timeout occurs.
    """
    url = f'{idp_url}/test-llm-prompt?record_id={id}'
    start_time = time.time()

    while True:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            get_response = response.json()

            if 'prompt-result' in get_response:  # Check if 'prompt-result' exists
                api_key = get_response['prompt-result'].get(key_name)
                if api_key:
                    return api_key
                else:
                    print(f"Key '{key_name}' not found in API response.")
                    return None
            else:
                print("Waiting for 'prompt-result'...")

        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")

        elapsed_time = time.time() - start_time
        if elapsed_time > timeout:
            print("Timeout occurred while waiting for 'prompt-result'")
            return None

        time.sleep(retry_interval)  # Wait before retrying
    

def test_prompt(url, data, headers):
    get_headers = headers
    headers['Content-Type'] = 'application/json'
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    out = response.json() 
    api_key = out.get('uid')
    print(f"Promptuid :{api_key}")
    data_point_name = data['prompts'][0]['data_point_name']
    value = get_prompt(data_point_name, api_key, get_headers)
    return value, api_key

def prompt_retrieval(url, headers):
    """
    Extracts specific data points from the given API response and returns a DataFrame.

    Args:
        api_response: The JSON object representing the API response.

    Returns:
        A pandas DataFrame with columns 'dataPointName', 'llmPrompt', 
        'useVisualLlm', and 'dataPointType'.
    """
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() 
        data = response.json()
        extracted_data = []
        for point in data['points']:
            data_point = {
                'dataPointName': point.get('dataPointName', ''),  # Use .get() with default value
                'llmPrompt': point.get('llmPrompt', ''),        # Use .get() with default value
                'useVisualLlm': point.get('useVisualLlm', False),  # Use .get() with default value
                'dataPointType': point.get('dataPointType', '')   # Use .get() with default value
            }
            extracted_data.append(data_point)
        df = pd.DataFrame(extracted_data)

    except requests.exceptions.RequestException as e:
        print(f"Error downloading API response: {e}")
    
    return df