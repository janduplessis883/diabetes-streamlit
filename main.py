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



# Mapping of online pre-assessment criteria names to the corresponding due status
# column names in the DataFrame. Used for filtering patients based on selected criteria.


# List of columns that contain date information and need to be converted to datetime objects.
date_cols = ['dob', 'first_dm_diagnosis', 'annual_review_done',
 'hba1c',
 'bp',
 'cholesterol',
 'bmi',
 'egfr',
 'urine_acr',
 'smoking',
 'foot_risk',
 'mh_screen_-_dds_or_phq',
 'patient_goals',
 'care_plan',
 'education',
 'hypo_monitoring',
 'next_appt_date',
 '9_kcp_complete',
 '3_levels_to_target',
 'retinal_screening',
 'care_planning_consultation',
 'statin_date',
 'review_due'
]

# List of columns that should be checked for being due based on a 15-month threshold.
fiveteen_m_columns = ['annual_review_done','smoking','foot_risk','retinal_screening','mh_screen_-_dds_or_phq','patient_goals','care_plan']

# List of columns to be dropped from the DataFrame during preprocessing.
columns_to_drop=['column1',
 'column2',
 'column3',
 'column4',
 'column5',
 'column6',
 'column7',
 'column8',
 'column9',
 'group_consultations',
 'hypo_mon_denom',
 'month_of_birth',
 'efi_score',
 'frailty',
 'qof_invites_done',
 'qof_dm006d',
 'qof_dm006_achieved',
 'qof_dm012d',
 'qof_dm012_achieved',
 'qof_dm014d',
 'qof_dm014_achieved',
 'qof_bp_done',
 'qof_dm019d',
 'qof_dm019_achieved',
 'qof_hba1c_done',
 'qof_dm020d',
 'qof_dm020_achieved',
 'qof_dm021d',
 'qof_dm021_achieved',
 'qof_dm022d',
 'qof_dm022_achieved',
 'qof_dm023d',
 'qof_dm023_achieved',
 'hba1c_trend',
 'diag_l6y_hba1c_<=53',
 'type_1',
 'type_2',
 'both_types_recorded',
 'no_type_recorded',
 'outstanding_es_count',
 'outstanding_qof_count',
 'total_outstanding',
 'next_appt_date',
 'next_appt_with',
 'number_future_appts',
 'covid-19_high_risk',
 'glp-1_or_insulin',
 'unnamed:_110',
 'unnamed:_111',
 'unnamed:_112',
 'unnamed:_113',
 'unnamed:_114',
 'unnamed:_115',
 'unnamed:_116',
 'unnamed:_117']





# # List of columns that contain date information and need to be converted to datetime objects.
# col_list = [
#     "dob",
#     "first_dm_diagnosis",
#     "annual_review_done",
#     "hba1c",
#     "bp",
#     "cholesterol",
#     "bmi",
#     "egfr",
#     "urine_acr",
#     "smoking",
#     "foot_risk",
#     "retinal_screening",
#     "9_kcp_complete",
#     "3_levels_to_target",
#     "mh_screen_-_dds_or_phq",
#     "patient_goals",
#     "care_plan",
#     "education",
#     "care_planning_consultation",
#     "review_due",
# ]

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


def convert_date_columns(df, date_columns):
    """
    Converts specified columns in a DataFrame to datetime objects.
    """
    for col in date_columns:
        print(f"Converting {col} to datetime - ⏳")
        df[col] = df[col].replace('01/01/1900', '')
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def mark_due(df, date_cols):
    """
    Adds boolean columns indicating if dates in given columns are more than 15 months old.
    Assumes date columns are already converted to datetime objects.
    """
    today = pd.Timestamp.today()
    cutoff = today - pd.DateOffset(months=15)

    for col in date_cols:
        df[f"{col}_due"] = df[col] < cutoff

    return df



def filter_due_patients(data, selected_tests):
    """
    Filters the DataFrame to include only patients who are due for all of the selected tests.

    Parameters:
    data (pd.DataFrame): DataFrame containing patient data with due status columns.
    selected_tests (list): A list of strings, where each string is the base name of a test (e.g., "smoking", "foot_risk"). The function will look for columns named like "{test}_due".

    Returns:
    pd.DataFrame: A filtered DataFrame containing only the patients who are due for all of the selected tests. Returns an empty DataFrame if no tests are selected or no patients are due.
    """
    filter_conditions = [
        data[f"{test}_due"] for test in selected_tests if f"{test}_due" in data.columns
    ]

    if not filter_conditions:
        return data.iloc[0:0]

    # Combine filter conditions using AND logic
    combined_filter = filter_conditions[0]
    for condition in filter_conditions[1:]:
        combined_filter &= condition

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
        dob = datetime.strptime(dob, "%d/%m/%Y").date()
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





def filter_due_patients(data, selected_tests):
    """
    Filters the DataFrame to include only patients who are due for all of the selected tests.

    Parameters:
    data (pd.DataFrame): DataFrame containing patient data with due status columns.
    selected_tests (list): A list of strings, where each string is the base name of a test (e.g., "smoking", "foot_risk"). The function will look for columns named like "{test}_due".

    Returns:
    pd.DataFrame: A filtered DataFrame containing only the patients who are due for all of the selected tests. Returns an empty DataFrame if no tests are selected or no patients are due.
    """
    filter_conditions = [
        data[f"{test}_due"] for test in selected_tests if f"{test}_due" in data.columns
    ]

    if not filter_conditions:
        return data.iloc[0:0]

    # Combine filter conditions using AND logic
    combined_filter = filter_conditions[0]
    for condition in filter_conditions[1:]:
        combined_filter &= condition

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
        print("DOB is a string")
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



@st.cache_data
def load_and_preprocess_dashboard(file_path, col_list):
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
    df['nhs_number'] = (
        df['nhs_number']
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)  # Remove trailing .0 if present
        .str.replace(" ", "")  # Remove any spaces
    )

    # Convert valid numbers to integers, ignoring invalid entries
    df['nhs_number'] = pd.to_numeric(df['nhs_number'], errors='coerce').astype('Int64')


    # Convert date columns to datetime objects
    df = convert_date_columns(df, col_list)

    # Apply 'mark_due' for columns in fiveteen_m_columns
    df = mark_due(df, col_list) # Note: mark_due should use fiveteen_m_columns, not col_list

    # Calculate age and length of diagnosis
    if 'dob' in df.columns:
        df['age'] = df['dob'].apply(calculate_age)
    if 'first_dm_diagnosis' in df.columns:
        df['lenght_of_diagnosis_years'] = df['first_dm_diagnosis'].apply(calculate_length_of_diagnosis)

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
        elif col == "hba1c_value":
            color = "#b92a1b"
        elif col == "dbp" or col == "sbp":
            color = "#98c25e"
        elif col == "latest_egfr":
            color = "#971e57"
        elif col == "total_chol" or col =="latest_ldl" or col == "latest_hdl" or col == "non-hdl_chol":
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
    # Attempt to find and rename the NHS number column to 'nhs_number'
    nhs_col_candidates = ['NHS number', 'NHS Number', 'NHS_number', 'NHS_Number', 'NHSNo', 'NHS No', 'NHS_No']
    nhs_col_found = None
    for col in nhs_col_candidates:
        if col in df.columns:
            nhs_col_found = col
            break

    if nhs_col_found:
        df.rename(columns={nhs_col_found: 'nhs_number'}, inplace=True)
        df['nhs_number'] = df['nhs_number'].astype(str).replace("", np.nan)
        df = df.dropna(subset=['nhs_number'])
        df['nhs_number'] = pd.to_numeric(df['nhs_number'], errors='coerce').astype('Int64') # Use Int64 for nullable integer
    else:
        st.warning("NHS number column not found in Google Sheet with common names. Returning empty DataFrame.")
        return pd.DataFrame() # Return empty DataFrame if NHS number column is not found

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
    # Ensure 'nhs_number' is consistent across dataframes and handle missing columns
    if 'nhs_number' not in intervention_df.columns:
        st.error("Intervention DataFrame is missing 'nhs_number' column.")
        return pd.DataFrame()
    if 'nhs_number' not in sms_df.columns:
        st.error("SMS DataFrame is missing 'nhs_number' column.")
        return pd.DataFrame()
    if 'nhs_number' not in notion_df.columns:
        st.error("Notion DataFrame is missing 'nhs_number' column.")
        return pd.DataFrame()

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
