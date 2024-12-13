# Prompt Refinement

## Project Overview

This project aims to improve the prompts used for Intelligent Document Processing (IDP) data extraction from mortgage documents. It achieves this by analyzing the accuracy of existing prompts and iteratively refining those that fall below a specified accuracy threshold.

## Files

- **`main.py`:** The main script that orchestrates the prompt refinement process. It handles authentication, data loading, accuracy analysis, prompt retrieval, and refinement.
- **`api_functions.py`:** Contains functions for interacting with the IDP API, including authentication, downloading responses, and retrieving/testing prompts.
- **`data_functions.py`:** Contains functions for data processing, such as calculating accuracy, converting JSON to DataFrame, and adding UIDs to the DataFrame.
- **`requirements.txt`:** Lists all the project's dependencies.

## Workflow

1.  **Authentication:** Authenticates with the IDP API using credentials stored in a `.env` file.
2.  **Data Loading:** Loads loan data from a CSV file (`loans.csv`) and document categories from the IDP API.
3.  **Data Extraction and Accuracy Analysis:**
    -   Extracts data from actual and expected output JSON files for each loan.
    -   Compares actual and expected values to calculate datapoint accuracy.
4.  **Prompt Retrieval and Refinement:**
    -   Retrieves existing prompts for all document categories from the IDP API.
    -   Filters prompts based on a user-defined accuracy threshold.
    -   Iteratively refines prompts that fall below the threshold by:
        -   Querying the IDP API with the current prompt and a request for improvement.
        -   Testing the new prompt against a set of loans.
        -   Repeating until the accuracy threshold is met.
5.  **Output:** Saves the updated prompts to a CSV file (`updated\_prompts.csv`).

## Requirements

-   Python 3.7 or higher
-   `requests` library
-   `pandas` library
-   `python-dotenv` library

## Setup

1.  **Install required libraries:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Create a `.env` file:**
    -   Create a file named `creds.env` in the `API` directory.
    -   Add the following environment variables, replacing placeholders with your actual values:
        ```
        email=[email address removed]
        password=your_password
        idp_url=your_idp_api_url 
        ```
3.  **Prepare input data:**
    -   Ensure you have a CSV file named `loans.csv` containing loan data (including "Harvester UID" and "Loan Num" columns).
    -   Make sure the actual and expected output JSON files for each loan are in the specified directories (see `data_functions.py`).

## Usage

1.  Run the `main.py` script:
    ```bash
    python main.py
    ```
2.  Enter the desired accuracy threshold when prompted.
3.  The script will process the data, refine the prompts, and save the updated prompts to `updated_prompts.csv`.

## Notes

-   You may need to adjust file paths and placeholders in the code based on your specific environment and data structure.
-   Ensure you have the necessary permissions to access the IDP API and file paths.
-   This project assumes a specific JSON structure for the actual and expected output files. You may need to modify the code if your JSON structure is different.
-   The `improve_prompt` function uses a fixed loan number and page range for testing new prompts. Consider modifying this to use a more representative sample of loans.

## Future Improvements

-   Implement more sophisticated prompt refinement strategies.
-   Incorporate user feedback in the prompt refinement loop.
-   Add logging and error handling for improved monitoring and debugging.
-   Develop a user interface for easier interaction and visualization.