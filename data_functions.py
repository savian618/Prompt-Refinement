# data_functions.py
import api_functions
import pandas as pd
import json
import time

def calculate_field_accuracy(df, datapoint_column='Datapoint Name', match_column='Match'):
  """
  Calculates the accuracy for each datapoint in a DataFrame with 'datapoint' 
  and 'match' columns.

  Args:
    df: The pandas DataFrame.
    datapoint_column: The name of the column containing the datapoints.
    match_column: The name of the column containing the match results (boolean).

  Returns:
    The DataFrame with a new column called 'Accuracy' containing the calculated 
    accuracies for each datapoint.
  """

  accuracy = df.groupby(datapoint_column)[match_column].mean()

  df['Accuracy'] = df[datapoint_column].map(accuracy)

  return df

def json_to_dataframe(json_file):
  """
  Converts a JSON file with the specified structure into a pandas DataFrame.

  Args:
    json_file: The path to the JSON file.

  Returns:
    A pandas DataFrame with columns 'Document Category', 'Page Range', 
    'Datapoint Name', and 'Value'.
  """

  with open(json_file, 'r') as f:
    data = json.load(f)

  rows = []
  for result in data['results']:
    doc_category = result['documentCategory']
    page_range = result['pageRange']
    extracted_data = result['extractedData']

    for datapoint_name, value in extracted_data.items():
      rows.append([doc_category, page_range, datapoint_name, value])

  df = pd.DataFrame(rows, columns=['Document Category', 'Page Range', 'Datapoint Name', 'Value'])
  return df

def add_uid_to_dataframe(df, json_file, doc_category_column='Document Category'):
    """
    Adds a 'UID' column to the DataFrame by matching 'Document Category' with 
    'documentCategory' in the JSON file.

    Args:
      df: The pandas DataFrame.
      json_file: The path to the JSON file containing document categories and UIDs.
      doc_category_column: The name of the column in the DataFrame containing 
                           document categories.

    Returns:
      The DataFrame with a new column 'UID' containing the corresponding UIDs.
    """

    with open(json_file, 'r') as f:
        categories_data = json.load(f)

    # Create a dictionary mapping document categories to UIDs
    category_uid_map = {category['documentCategory']: category['uid'] 
                        for category in categories_data['categories']}

    # Map UIDs to the DataFrame based on 'Document Category'
    df['UID'] = df[doc_category_column].map(category_uid_map)

    return df

def process_loan(row, idp_url, idp_headers):
    """Processes a single loan to extract and compare data."""
    uploadId = row['Harvester UID']
    loan = row['Loan Num']
    extraction_url = f'{idp_url}/extraction/{uploadId}?extractionKey=combined-extraction'
    actual_path = rf"M:\Mortgage Operations\interim_tools\idp_testing\QA Automation\Extraction\Actual\{loan}.json"
    expected_path = rf"M:\Mortgage Operations\interim_tools\idp_testing\QA Automation\Extraction\Expected\{loan}.json"

    api_functions.download_api_response(extraction_url, actual_path, idp_headers)
    actual_df = json_to_dataframe(actual_path)
    expected_df = json_to_dataframe(expected_path)
    actual_df['Page Range'] = actual_df['Page Range'].apply(tuple)
    expected_df['Page Range'] = expected_df['Page Range'].apply(tuple)
    temp = pd.merge(actual_df, expected_df, on=['Document Category', 'Page Range', 'Datapoint Name'],
                    how='inner', suffixes=('_1', '_2'))
    temp.rename(columns={'Value_1': 'Actual', 'Value_2': 'Expected'}, inplace=True)
    temp = temp.groupby(['Document Category', 'Page Range', 'Datapoint Name'])[['Actual', 'Expected']].first().reset_index()
    temp['Match'] = (temp['Actual'] == temp['Expected']) | (temp['Actual'].isnull() & temp['Expected'].isnull())
    temp['Loan'] = loan
    temp['Page Range'] = temp['Page Range'].apply(list)
    return temp

def retrieve_prompts(group, idp_url, idp_headers):
    """Retrieves prompts for a specific category."""
    uid = group['UID'].iloc[0]
    prompts_url = f'{idp_url}/categories/{uid}/data-points'
    prompt_temp = api_functions.prompt_retrieval(prompts_url, idp_headers)
    prompt_temp['Document Category'] = group.name  
    return prompt_temp


def improve_prompt(prompt_row, datapoints, idp_url, idp_headers, threshold):
    """Improves a single prompt iteratively until accuracy threshold is met."""
    start_time = time.time()
    prompt_accuracy = prompt_row['Accuracy']
    datapoint = prompt_row['dataPointName']
    final_prompt = prompt_row['prompt']
    datapoints_view = datapoints[datapoints['Datapoint Name'] == datapoint]
    test_prompt_url = f'{idp_url}/test-llm-prompt'
    example_actual = prompt_row['Actual']
    example_excpected = prompt_row['Expected']
    prompt_history = set()
    prompts_attempted = 10
    while prompt_accuracy <= threshold and prompts_attempted <= 10:
        question_prompt = f"This is my current prompt: *{final_prompt}* It returns {example_actual} and I want it to return {example_excpected}. Make corrections to the prompt as needed and improve it so that you are able to better extract that data. Please return the new prompt text."
        prompts_attempted+=1
        # 1. Get a new prompt from the API
        data_for_new_prompt = {
            "loan_number": str(datapoints_view['Loan'].iloc[0]),  # Use any loan from datapoints_view
            "page_range": list(datapoints_view['Page Range'].iloc[0]),  # Use corresponding page range
            "prompts": [
                {
                    "data_point_name": prompt_row['dataPointName'],
                    "data_point_type": prompt_row['dataPointType'],
                    "llm_prompt": question_prompt
                }
            ],
            "is_visual": prompt_row['useVisualLlm']
        }
        new_prompt, test_uid = api_functions.test_prompt(test_prompt_url, data_for_new_prompt, idp_headers)
        if new_prompt in prompt_history:  
            print("LLM suggested a previously tried prompt. Skipping...")
            continue
        
        prompt_history.add(new_prompt)

        # 2. Test the new prompt on all loans
        results = []
        for _, data_row in datapoints_view.iterrows():
            data_for_testing = {
                "loan_number": str(data_row['Loan']),
                "page_range": list(data_row['Page Range']),
                "prompts": [
                    {
                        "data_point_name": data_row['Datapoint Name'],
                        "data_point_type": prompt_row['dataPointType'],
                        "llm_prompt": new_prompt  # Use the new_prompt here
                    }
                ],
                "is_visual": prompt_row['useVisualLlm']
            }
            result, results_id = api_functions.test_prompt(test_prompt_url, data_for_testing, idp_headers)
            results.append(result == data_row['Expected'])
            if data_row['Loan'] == datapoints_view['Loan'].iloc[0]:
               example_actual = result
            with open("prompt_out.log", "a") as f:
              f.write(f"Document: {prompt_row['Document Category']}\n")
              f.write(f"Datapoint: {datapoint}\n")
              f.write(f"Prompt: {new_prompt}\n")
              f.write(f"New Value: {result}\n")  # Include accuracy in the log
              f.write(f"Expected: {data_row['Expected']}\n")
              f.write(f"UID for Prompt Refinement:{test_uid}\n")
              f.write(f"UID for Prompt Test:{results_id}\n")
              f.write("-----------------------------\n")

        prompt_accuracy = sum(results) / len(results)
        if prompt_accuracy > prompt_row['Accuracy']:
          end_time = time.time()  # Record the end time
          elapsed_time = end_time - start_time
          print(f"LLM took {elapsed_time:.2f} seconds to find a better prompt")
        final_prompt = new_prompt

    return {'Document': prompt_row['Document Category'], 'datapoint': datapoint, 'new_prompt': final_prompt, 'old_prompt': prompt_row['prompt']}