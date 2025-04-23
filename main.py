"""
This module contains functions for loading, preprocessing, and analyzing diabetes patient data.
It includes functionalities for calculating due statuses for various tests, filtering patients,
calculating age and length of diagnosis, plotting histograms, and handling data from Notion
and Google Sheets.
"""

import pandas as pd
import pendulum
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import numpy as np
import gspread
from google.oauth2 import service_account
from dateutil.relativedelta import relativedelta

from notionhelper import *
from jan883_eda import *

# Dictionary containing information about different tests and their due calculation parameters.
# Each key represents a test (e.g., "hba1c_due"), and the value is a dictionary
# specifying the date column, optional value column, threshold value, and the
# name of the column to store the due status.
test_info = {
    "hba1c_due": {
        "date_col": "hba1c",
        "value_col": "hba1c_value",
        "threshold_value": 53,
        "due_col": "hba1c_due",
    },
    "lipids_due": {"date_col": "cholesterol", "due_col": "lipids_due"},
    "egfr_due": {
        "date_col": "egfr",
        "value_col": "latest_egfr",
        "threshold_value": 30,
        "due_col": "egfr_due",
    },
    "urine_acr_due": {
        "date_col": "urine_acr",
        "value_col": "",
        "threshold_value": None,
        "due_col": "urine_acr_due",
    },
    "bp_due": {
        "date_col": "bp",
        "value_col": "",
        "threshold_value": None,
        "due_col": "bp_due",
    },
}

# Mapping of user-friendly test names to the corresponding due status column names
# in the DataFrame. Used for filtering patients based on selected tests.
test_mapping = {
    "HbA1c": "hba1c_due",
    "Lipids": "lipids_due",
    "eGFR": "egfr_due",
    "Urine ACR": "urine_acr_due",
    "Foot Check": "foot_due", # This mapping might need adjustment if foot_risk is the new column
}

# Mapping of online pre-assessment criteria names to the corresponding due status
# column names in the DataFrame. Used for filtering patients based on selected criteria.


# List of columns that contain date information and need to be converted to datetime objects.
col_list = [
    "dob",
    "first_dm_diagnosis",
    "annual_review_done",
    "hba1c",
    "bp",
    "cholesterol",
    "bmi",
    "egfr",
    "urine_acr",
    "smoking",
    "foot_risk",
    "retinal_screening",
    "9_kcp_complete",
    "3_levels_to_target",
    "mh_screen_-_dds_or_phq",
    "patient_goals",
    "care_plan",
    "education",
    "care_planning_consultation",
    "review_due",
]

# List of columns that should be checked for being due based on a 15-month threshold.
fiveteen_m_columns = ['annual_review_done','smoking','foot_risk','retinal_screening','mh_screen_-_dds_or_phq','patient_goals','care_plan']

# List of columns to be dropped from the DataFrame during preprocessing.
columns_to_drop=[
            "Column1", # Assuming these columns are consistently named and can be dropped before renaming
            "Column2",
            "Column3",
            "Column4",
            "Column5",
            "Column6",
            "Column7",
            "Column8",
            "Column9",
            "Group consultations",
            "Hypo Mon Denom",
            "Month of Birth",
            "EFi Score",
            "Frailty",
            "QoF Invites Done",
            "QoF DM006D",
            "QoF DM006 Achieved",
            "QoF DM012D",
            "QoF DM012 Achieved",
            "QoF DM014D",
            "QoF DM014 Achieved",
            "QoF BP Done",
            "QoF DM019D",
            "QoF DM019 Achieved",
            "QoF HbA1c Done",
            "QoF DM020D",
            "QoF DM020 Achieved",
            "QoF DM021D",
            "QoF DM021 Achieved",
            "QoF DM022D",
            "QoF DM022 Achieved",
            "QoF DM023D",
            "QoF DM023 Achieved",
            "HbA1c Trend",
            "Diag L6y HbA1c <=53",
            "Type 1",
            "Type 2",
            "Both Types Recorded",
            "No Type Recorded",
            "Outstanding ES Count",
            "Outstanding QoF Count",
            "Total Outstanding",
            "Next Appt Date",
            "Next Appt with",
            "Number Future Appts",
            "COVID-19 High Risk",
            "GLP-1 or Insulin",
            "Unnamed: 110",
            "Unnamed: 111",
            "Unnamed: 112",
            "Unnamed: 113",
            "Unnamed: 114",
            "Unnamed: 115",
            "Unnamed: 116",
            "Unnamed: 117",
        ]

# Mapping of user-friendly test names to the corresponding due status column names
# in the DataFrame. Used for filtering patients based on selected tests.
test_mapping = {
    "HbA1c": "hba1c_due",
    "Lipids": "lipids_due",
    "eGFR": "egfr_due",
    "Urine ACR": "urine_acr_due",
}



# List of columns that contain date information and need to be converted to datetime objects.
col_list = [
    "dob",
    "first_dm_diagnosis",
    "annual_review_done",
    "hba1c",
    "bp",
    "cholesterol",
    "bmi",
    "egfr",
    "urine_acr",
    "smoking",
    "foot_risk",
    "retinal_screening",
    "9_kcp_complete",
    "3_levels_to_target",
    "mh_screen_-_dds_or_phq",
    "patient_goals",
    "care_plan",
    "education",
    "care_planning_consultation",
    "review_due",
]

# List of columns that should be checked for being due based on a 15-month threshold.
fiveteen_m_columns = ['annual_review_done','smoking','foot_risk','retinal_screening','mh_screen_-_dds_or_phq','patient_goals','care_plan']

# List of columns to be dropped from the DataFrame during preprocessing.
columns_to_drop=[
            "Column1", # Assuming these columns are consistently named and can be dropped before renaming
            "Column2",
            "Column3",
            "Column4",
            "Column5",
            "Column6",
            "Column7",
            "Column8",
            "Column9",
            "Group consultations",
            "Hypo Mon Denom",
            "Month of Birth",
            "EFi Score",
            "Frailty",
            "QoF Invites Done",
            "QoF DM006D",
            "QoF DM006 Achieved",
            "QoF DM012D",
            "QoF DM012 Achieved",
            "QoF DM014D",
            "QoF DM014 Achieved",
            "QoF BP Done",
            "QoF DM019D",
            "QoF DM019 Achieved",
            "QoF HbA1c Done",
            "QoF DM020D",
            "QoF DM020 Achieved",
            "QoF DM021D",
            "QoF DM021 Achieved",
            "QoF DM022D",
            "QoF DM022 Achieved",
            "QoF DM023D",
            "QoF DM023 Achieved",
            "HbA1c Trend",
            "Diag L6y HbA1c <=53",
            "Type 1",
            "Type 2",
            "Both Types Recorded",
            "No Type Recorded",
            "Outstanding ES Count",
            "Outstanding QoF Count",
            "Total Outstanding",
            "Next Appt Date",
            "Next Appt with",
            "Number Future Appts",
            "COVID-19 High Risk",
            "GLP-1 or Insulin",
            "Unnamed: 110",
            "Unnamed: 111",
            "Unnamed: 112",
            "Unnamed: 113",
            "Unnamed: 114",
            "Unnamed: 115",
            "Unnamed: 116",
            "Unnamed: 117",
        ]




def filter_due_patients(data, selected_tests, test_mapping):
    """
    Filters the DataFrame to include only patients who are due for at least one of the selected tests.

    Parameters:
    data (pd.DataFrame): DataFrame containing patient data with due status columns.
    selected_tests (list): A list of strings, where each string is a user-friendly name of a test (e.g., "HbA1c", "Foot Check").
    test_mapping (dict): A dictionary mapping user-friendly test names to the corresponding due status column names in the DataFrame.

    Returns:
    pd.DataFrame: A filtered DataFrame containing only the patients who are due for any of the selected tests. Returns an empty DataFrame if no tests are selected or no patients are due.
    """
    filter_conditions = [
        data[test_mapping[test]] for test in selected_tests if test in test_mapping
    ]

    if not filter_conditions:
        return data.iloc[0:0]

    combined_filter = filter_conditions[0]
    for condition in filter_conditions[1:]:
        combined_filter |= condition

    return data[combined_filter]


def calculate_age(dob):
    """
    Calculates the age in years based on a given date of birth.

    Parameters:
    dob (str or datetime.date): The date of birth. Can be a string in 'YYYY-MM-DD' format or a datetime.date object.

    Returns:
    int: The calculated age in full years.
    """
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    elif isinstance(dob, datetime):
        dob = dob.date()

    today = datetime.today().date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age

def calculate_length_of_diagnosis(diagnosis_date):
    """
    Calculates the length of diabetes diagnosis in years based on the first diagnosis date.

    Parameters:
    diagnosis_date (str or datetime.date): The date of the first diabetes diagnosis. Can be a string in 'YYYY-MM-DD' format or a datetime.date object.

    Returns:
    int: The calculated length of diagnosis in full years.
    """
    if isinstance(diagnosis_date, str):
        diagnosis_date = datetime.strptime(diagnosis_date, "%Y-%m-%d").date()
    elif isinstance(diagnosis_date, datetime):
        diagnosis_date = diagnosis_date.date()

    today = datetime.today().date()
    years = (today.year - diagnosis_date.year) + today.month - diagnosis_date.month

    # If the current day is earlier in the month than the diagnosis day, subtract one month
    if today.day < diagnosis_date.day:
        years -= 1

    return years



def calculate_due_status(
    data,
    date_col,
    value_col=None,
    threshold_value=None,
    timeframe_years=1.25,
    due_col="due_status",
):
    """
    Calculates the due status for a specific test based on the last test date and an optional threshold value.

    Parameters:
    data (pd.DataFrame): DataFrame containing the patient data.
    date_col (str): The name of the column containing the date of the last test.
    value_col (str, optional): The name of the column containing the test value (e.g., HbA1c value). Defaults to None.
    threshold_value (float, optional): A threshold value for the test value that affects the due timeframe. Defaults to None.
    timeframe_years (float): The default timeframe in years after which the test is considered due. Defaults to 1.25.
    due_col (str): The name of the new column to be created to store the due status (True if due, False otherwise). Defaults to "due_status".

    Returns:
    pd.DataFrame: The input DataFrame with an added column indicating the due status for the specified test.
    """
    now = pendulum.now()

    def is_due(row):
        last_date = row[date_col]
        test_value = row[value_col] if value_col else None

        if pd.isnull(last_date) or (value_col and pd.isnull(test_value)):
            return False  # Insufficient data

        if value_col and test_value <= threshold_value:
            timeframe = timeframe_years / 2  # Adjust timeframe based on value threshold
        else:
            timeframe = timeframe_years

        # Parse last_date and calculate due status
        last_date = pendulum.parse(str(last_date))
        return (now - last_date).in_years() >= timeframe

    data[due_col] = data.apply(is_due, axis=1)
    return data


def filter_due_patients(data, selected_tests, test_mapping):
    """
    Filters the DataFrame to include only patients who are due for at least one of the selected tests.

    Parameters:
    data (pd.DataFrame): DataFrame containing patient data with due status columns.
    selected_tests (list): A list of strings, where each string is a user-friendly name of a test (e.g., "HbA1c", "Foot Check").
    test_mapping (dict): A dictionary mapping user-friendly test names to the corresponding due status column names in the DataFrame.

    Returns:
    pd.DataFrame: A filtered DataFrame containing only the patients who are due for any of the selected tests. Returns an empty DataFrame if no tests are selected or no patients are due.
    """
    filter_conditions = [
        data[test_mapping[test]] for test in selected_tests if test in test_mapping
    ]

    if not filter_conditions:
        return data.iloc[0:0]

    combined_filter = filter_conditions[0]
    for condition in filter_conditions[1:]:
        combined_filter |= condition

    return data[combined_filter]


def calculate_age(dob):
    """
    Calculates the age in years based on a given date of birth.

    Parameters:
    dob (str or datetime.date): The date of birth. Can be a string in 'YYYY-MM-DD' format or a datetime.date object.

    Returns:
    int: The calculated age in full years.
    """
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    elif isinstance(dob, datetime):
        dob = dob.date()

    today = datetime.today().date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age

def calculate_length_of_diagnosis(diagnosis_date):
    """
    Calculates the length of diabetes diagnosis in years based on the first diagnosis date.

    Parameters:
    diagnosis_date (str or datetime.date): The date of the first diabetes diagnosis. Can be a string in 'YYYY-MM-DD' format or a datetime.date object.

    Returns:
    int: The calculated length of diagnosis in full years.
    """
    if isinstance(diagnosis_date, str):
        diagnosis_date = datetime.strptime(diagnosis_date, "%Y-%m-%d").date()
    elif isinstance(diagnosis_date, datetime):
        diagnosis_date = diagnosis_date.date()

    today = datetime.today().date()
    years = (today.year - diagnosis_date.year) + today.month - diagnosis_date.month

    # If the current day is earlier in the month than the diagnosis day, subtract one month
    if today.day < diagnosis_date.day:
        years -= 1

    return years

def calculate_annual_review_due(df, review_due_col="Review Due", due_col="annual_review_due"):
    """
    Determines if the annual review is due for each patient based on the 'Review Due' date column.

    Parameters:
    df (pd.DataFrame): DataFrame containing the patient data, including a 'Review Due' column.
    review_due_col (str): The name of the column containing the annual review due date (expected format 'Mon-YY', e.g., 'Jan-25'). Defaults to "Review Due".
    due_col (str): The name of the new column to be created to store the annual review due status (True if due, False otherwise). Defaults to "annual_review_due".

    Returns:
    pd.DataFrame: The input DataFrame with an added column indicating the annual review due status.
    """
    now = datetime.now().date()

    def is_annual_review_due(review_date_str):
        if pd.isnull(review_date_str) or review_date_str == "":
            return False # No review date provided

        try:
            # Parse the month-year string (e.g., 'Jan-25')
            # Assumes the year is in the current century (20xx)
            review_date = datetime.strptime(str(review_date_str), "%b-%y").date()
            return review_date < now
        except ValueError:
            # Handle cases where the date string is not in the expected format
            return False

    df[due_col] = df[review_due_col].apply(is_annual_review_due)
    return df

from dateutil.relativedelta import relativedelta

def mark_due(df, date_columns):
    """
    Adds boolean columns indicating if dates in given columns are more than 15 months old.

    Parameters:
    - df: pandas DataFrame
    - date_columns: list of column names (strings)

    Returns:
    - DataFrame with new columns: `<column>_due` for each date column
    """
    today = date.today()
    cutoff = today - relativedelta(months=15)

    for col in date_columns:
        if col in df.columns: # Check if column exists
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
            df[f"{col}_due"] = df[col] < cutoff

    return df


@st.cache_data
def load_and_preprocess_dashboard(file_path, col_list, test_info, fiveteen_m_columns):
    """
    Loads the raw diabetes dashboard data from a CSV file, preprocesses it,
    calculates age and length of diagnosis, and determines the due status for various tests.

    Parameters:
    file_path (str): The path to the raw diabetes dashboard CSV file.
    col_list (list): A list of column names that should be treated as dates.
    test_info (dict): A dictionary containing information about different tests and their due calculation parameters.
    fiveteen_m_columns (list): A list of column names for which to calculate due status based on a 15-month threshold.

    Returns:
    pd.DataFrame: A preprocessed and enriched DataFrame with calculated age, length of diagnosis, and due statuses for various tests.
    """
    # Load the CSV file
    df = pd.read_csv(file_path)

    # Check if columns are in DataFrame, and drop only those present
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    # Update column names to lowercase with underscores
    df = update_column_names(df)

    # Handle NHS number - clean and convert
    df.rename(columns= {'nhs_number': 'nhs_number'}, inplace=True) # Ensure 'nhs_number' is consistent after renaming
    df['nhs_number'] = (
        df['nhs_number']
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)  # Remove trailing .0 if present
        .str.replace(" ", "")  # Remove any spaces
    )

    # Convert valid numbers to integers, ignoring invalid entries
    df['nhs_number'] = pd.to_numeric(df['nhs_number'], errors='coerce').astype('Int64')

    # Convert specified columns to date only (no time part)
    for col in col_list:
        if col in df.columns: # Check if column exists after renaming
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # Calculate age and length of diagnosis
    if 'dob' in df.columns:
        df['age'] = df['dob'].apply(calculate_age)
    if 'first_dm_diagnosis' in df.columns:
        df['lenght_of_diagnosis_years'] = df['first_dm_diagnosis'].apply(calculate_length_of_diagnosis)

    # Apply 'calculate_due_status' based on 'test_info' dictionary for relevant tests
    for test_name, params in test_info.items():
        # Ensure date_col and value_col exist after renaming
        if params['date_col'] in df.columns and (params['value_col'] == "" or params['value_col'] in df.columns):
             df = calculate_due_status(df, **params)


    # Apply 'mark_due' for columns in fiveteen_m_columns
    df = mark_due(df, [col for col in fiveteen_m_columns if col in df.columns]) # Ensure columns exist

    # Calculate annual review due status using the dedicated function
    if 'review_due' in df.columns:
        df = calculate_annual_review_due(df, review_due_col='review_due', due_col='annual_review_due') # Use correct column name

    return df

plot_columns = [
    "age",
    "lenght_of_diagnosis_years",
    "hba1c_value",
    "dbp",
    "sbp",
    "latest_egfr",
    "total_chol",
    "latest_ldl",
    "latest_hdl",
    "non-hdl_chol",
]

def plot_histograms(data, columns, color="#e3964a"):
    """
    Generates and displays a grid of histograms for specified numerical columns in a DataFrame using Seaborn and Matplotlib,
    tailored for display in a Streamlit application.

    Parameters:
    - data (pd.DataFrame): The DataFrame containing the data to plot.
    - columns (list of str): A list of column names from the DataFrame for which to generate histograms.
    - color (str): The base color (hex code) to use for the histograms. Note that specific columns have overridden colors. Defaults to "#e3964a".
    """

    fig, axes = plt.subplots(2, 5, figsize=(22, 6), sharey=True)

    # Loop over each column and create a histogram
    for i, col in enumerate(columns):

        if col == 'age':
            color = "#459aca"
        elif col == "lenght_of_diagnosis_years":
            color = "#1d2d3d"
        elif col == "HbA1c value":
            color = "#b92a1b"
        elif col == "DBP" or col == "SBP":
            color = "#98c25e"
        elif col == "Latest eGFR":
            color = "#971e57"
        elif col == "Total Chol" or col =="Latest LDL" or col == "Latest HDL" or col == "Non-HDL Chol":
            color = "#e3964a"

        row, col_index = divmod(i, 5)  # Determine row and column index in 2x5 grid
        sns.histplot(
            data=data,
            x=col,
            ax=axes[row, col_index],
            color=color,
            bins=15,
            kde = False
        )

        # Remove top and right borders
        axes[row, col_index].spines["top"].set_visible(False)
        axes[row, col_index].spines["right"].set_visible(False)
        axes[row, col_index].spines["left"].set_visible(False)

        # Add horizontal grid lines with specific thickness
        axes[row, col_index].yaxis.grid(True, linewidth=0.5)
        axes[row, col_index].grid(axis="x", visible=False)  # Optional: hides vertical grid lines if not desired

    # Hide any unused subplots if columns are less than 10
    for j in range(len(columns), 10):
        fig.delaxes(axes.flatten()[j])

    # Display the plot in Streamlit
    st.pyplot(fig)


@st.cache_resource
def load_notion_df(notion_token, notion_database):
    """
    Loads data from a Notion database into a Pandas DataFrame.

    Parameters:
    - notion_token (str): The Notion API token.
    - notion_database (str): The ID of the Notion database.

    Returns:
    - pd.DataFrame: DataFrame containing data from the Notion database,
                    or an empty DataFrame if token or database ID is missing.
    """
    if notion_token != "" and notion_database != "":
        nh = NotionHelper(notion_token, notion_database)
        notion_df = nh.get_all_pages_as_dataframe()
        # Ensure 'NHS number' is consistent in the returned DataFrame
        if 'NHS number' in notion_df.columns:
             notion_df.rename(columns={'NHS number': 'nhs_number'}, inplace=True)
        return notion_df
    return pd.DataFrame() # Return empty DataFrame if credentials are not provided

@st.cache_resource
def load_google_sheet_df(sheet_url, sheet_index):
    """
    Loads data from a Google Sheet into a Pandas DataFrame using service account credentials.

    Parameters:
    - sheet_url (str): The URL of the Google Sheet.
    - sheet_index (int): The index of the worksheet to load (0-based).

    Returns:
    - pd.DataFrame: DataFrame containing data from the Google Sheet.
    """
    credentials = {
        "type": st.secrets.google_sheets.type,
        "project_id": st.secrets.google_sheets.project_id,
        "private_key_id": st.secrets.google_sheets.private_key_id,
        "private_key": st.secrets.google_sheets.private_key,
        "client_email": st.secrets.google_sheets.client_email,
        "client_id": st.secrets.google_sheets.client_id,
        "auth_uri": st.secrets.google_sheets.auth_uri,
        "token_uri": st.secrets.google_sheets.token_uri,
        "auth_provider_x509_cert_url": st.secrets.google_sheets.auth_provider_x509_cert_url,
        "client_x509_cert_url": st.secrets.google_sheets.client_x509_cert_url,
}

    gc = gspread.service_account_from_dict(credentials)

    sh = gc.open_by_url(sheet_url)
    sheet = sh.get_worksheet_by_id(sheet_index)
    records = sheet.get_all_records()
    df = pd.DataFrame.from_dict(records)
    # Ensure 'NHS number' is consistent in the loaded DataFrame
    if 'NHS number' in df.columns:
        df.rename(columns={'NHS number': 'nhs_number'}, inplace=True)
    df['nhs_number'] = df['nhs_number'].astype(str).replace("", np.nan)
    df = df.dropna(subset=['nhs_number'])
    df['nhs_number'] = pd.to_numeric(df['nhs_number'], errors='coerce').astype('Int64') # Use Int64 for nullable integer
    return df


def extract_sms_df(intervention_df, sms_df, notion_df):
    """
    Extracts a subset of the SMS DataFrame based on patients present in the intervention DataFrame
    and not present in the Notion DataFrame.

    Parameters:
    - intervention_df (DataFrame): DataFrame containing patients for intervention.
    - sms_df (DataFrame): The original SMS DataFrame.
    - notion_df (DataFrame): DataFrame containing patients already actioned in Notion.

    Returns:
    - pd.DataFrame: DataFrame of patients to contact via SMS.
    """
    # Ensure 'nhs_number' is consistent across dataframes
    intervention_df['nhs_number'] = pd.to_numeric(intervention_df['nhs_number'], errors='coerce').astype('Int64')
    sms_df["nhs_number"] = pd.to_numeric(sms_df["nhs_number"], errors='coerce').astype('Int64')
    notion_df["nhs_number"] = pd.to_numeric(notion_df["nhs_number"], errors='coerce').astype('Int64')

    output_sms_df = sms_df.merge(intervention_df[["nhs_number"]], on="nhs_number", how="inner")

    patients_to_contact = output_sms_df[~output_sms_df['nhs_number'].isin(notion_df['nhs_number'])]
    return patients_to_contact


def update_column_names(df):
    """
    Updates column names in a Pandas DataFrame by converting them to lower case and replacing spaces with underscores.

    Parameters:
        df (pd.DataFrame): Input DataFrame
    Returns:
        pd.DataFrame: The input DataFrame with updated column names
    """
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    return df




def download_sms_csv(rewind_df, sms_df, notion_df, filename="dm_rewind_sms.csv"):
    """
    Extracts an SMS DataFrame, converts it to CSV, and provides a Streamlit download button.

    Parameters:
    - rewind_df (DataFrame): The DataFrame used as input for the SMS extraction.
    - sms_df (DataFrame): The SMS DataFrame to be extracted.
    - notion_df (DataFrame): DataFrame containing patients already actioned in Notion.
    - filename (str): The name of the CSV file to be downloaded. Default is 'dm_rewind_sms.csv'.
    """

    # Extract the SMS DataFrame
    output_sms_df = extract_sms_df(rewind_df, sms_df, notion_df)

    # Convert DataFrame to CSV format
    csv = output_sms_df.to_csv(index=False)

    # Display download button in Streamlit
    st.download_button(
        label=f"Download **{filename}**",
        data=csv,
        file_name=filename,
        mime="text/csv",
    )
