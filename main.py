# main.py
import api_functions
import data_functions
from dotenv import load_dotenv
import os
import pandas as pd
import datetime

# Load environment variables
load_dotenv('creds.env')
email = os.getenv('email')
password = os.getenv('password')
idp_url = os.getenv('idp_url')
idp_auth_url = f'{idp_url}/auth/token'

# Authenticate
idp_auth_token, expiry_time = api_functions.load_token()

if idp_auth_token and expiry_time > datetime.datetime.now():
  print("Using existing token.")
else:
  print("Token expired or not found. Reauthenticating...")
  idp_auth_token = api_functions.get_idp_auth_token(idp_auth_url, email, password)
  if idp_auth_token:
    print(f"Authentication successful. Token: {idp_auth_token}")
    expiry_time = datetime.datetime.now() + datetime.timedelta(hours=8)
    api_functions.save_token(idp_auth_token, expiry_time)
  else:
    print("Authentication failed.")
    exit()

# Load loan data
loans = pd.read_csv('loans.csv') 
idp_headers = {'authorizationToken': f'{idp_auth_token}'}

# Load or download categories
categories = 'categories.json'
if not os.path.exists(categories):
    categories_url = f'{idp_url}/categories'
    api_functions.download_api_response(categories_url, categories, idp_headers)

# Process all loans 
results = loans.apply(lambda row: data_functions.process_loan(row, idp_url, idp_headers), axis=1)
datapoints = pd.concat(results.tolist()) 

# Calculate datapoint accuracy
datapoint_accuracy = data_functions.calculate_field_accuracy(datapoints)
datapoint_accuracy = data_functions.add_uid_to_dataframe(datapoint_accuracy, categories)

# Retrieve prompts for all categories
prompt_list = datapoint_accuracy.groupby('Document Category', group_keys=False).apply(
    lambda group: data_functions.retrieve_prompts(group, idp_url, idp_headers)
)

prompts = prompt_list.merge(datapoint_accuracy, left_on=['Document Category', 'dataPointName'],
                        right_on=['Document Category', 'Datapoint Name'], how='left')
prompts = prompts.rename(columns={'llmPrompt': 'prompt'}) 
prompts.to_csv('prompts.csv')
# Get accuracy threshold from user
while True:
    try:
        threshold = float(input("What is the threshold for prompt accuracy? (e.g., 0.85): "))
        if 0 <= threshold <= 1:
            break
        else:
            print("Threshold must be between 0 and 1.")
    except ValueError:
        print("Invalid input. Please enter a number between 0 and 1.")

# Filter for failed prompts
failed_prompts = prompts[prompts['Accuracy'] <= threshold]
# Improve prompts 
updated_prompts = failed_prompts.apply(
    lambda row: data_functions.improve_prompt(row, datapoints, idp_url, idp_headers, threshold), axis=1, result_type='expand'
)

# Log the updated prompts
updated_prompts.to_csv("prompt_out.csv", index=False) 

