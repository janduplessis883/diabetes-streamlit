import pandas as pd
import pendulum
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
import numpy as np
import gspread
from google.oauth2 import service_account

from notionhelper import *

test_info = {
    "hba1c_due": {
        "date_col": "HbA1c",
        "value_col": "HbA1c value",
        "threshold_value": 53,
        "due_col": "hba1c_due",
    },
    "lipids_due": {"date_col": "Cholesterol", "due_col": "lipids_due"},
    "egfr_due": {
        "date_col": "eGFR",
        "value_col": "Latest eGFR",
        "threshold_value": 30,
        "due_col": "egfr_due",
    },
    "foot_due": {"date_col": "Foot Risk", "due_col": "foot_due"},
    "urine_acr_due": {
        "date_col": "Urine ACR",
        "value_col": "",
        "threshold_value": None,
        "due_col": "urine_acr_due",
    },
    "annual_review_due": {
        "date_col": "Annual Review Done",
        "value_col": "",
        "threshold_value": None,
        "due_col": "annual_review_due",
    },
    "bp_due": {
        "date_col": "BP",
        "value_col": "",
        "threshold_value": None,
        "due_col": "bp_due",
    },
    "dds2_due": {
        "date_col": "MH Screen - DDS or PHQ",
        "value_col": "",
        "threshold_value": None,
        "due_col": "dds2_due",
    },
    "goals_due": {
        "date_col": "Urine ACR",
        "value_col": "",
        "threshold_value": None,
        "due_col": "goals_due",
    },
    "care_plan_due": {
        "date_col": "Care plan",
        "value_col": "",
        "threshold_value": None,
        "due_col": "care_plan_due",
    },
    "eductation_due": {
        "date_col": "Education",
        "value_col": "",
        "threshold_value": None,
        "due_col": "education_due",
    },
}

test_mapping = {
    "HbA1c": "hba1c_due",
    "Lipids": "lipids_due",
    "eGFR": "egfr_due",
    "Urine ACR": "urine_acr_due",
    "Foot Check": "foot_due",
}

online_mapping = {
    "Annual Review Done": "annual_review_due",
    "BP": "bp_due",
    "MH Screen - DDS or PHQ": "dds2_due",
    "Patient goals": "goals_due",
    "Care plan": "care_plan_due",
    "Education": "education_due",
}

col_list = [
    "DOB",
    "First DM Diagnosis",
    "Annual Review Done",
    "HbA1c",
    "BP",
    "Cholesterol",
    "BMI",
    "eGFR",
    "Urine ACR",
    "Smoking",
    "Foot Risk",
    "Retinal screening",
    "9 KCP Complete",
    "3 Levels to Target",
    "MH Screen - DDS or PHQ",
    "Patient goals",
    "Care plan",
    "Education",
    "Care planning consultation",
]



columns_to_drop=[
            "Column1",
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

def calculate_due_status(
    data,
    date_col,
    value_col=None,
    threshold_value=None,
    timeframe_years=1.25,
    due_col="due_status",
):
    """
    Generic function to determine if a test is due based on the last test date and an optional threshold value.

    Parameters:
    data (pd.DataFrame): DataFrame containing the test dates and optional test values.
    date_col (str): Column name with the date of the last test.
    value_col (str, optional): Column name with the test values.
    threshold_value (float, optional): Threshold value to adjust the due frequency.
    timeframe_years (float): Default timeframe in years to consider due.
    due_col (str): New column name to store the due status.

    Returns:
    pd.DataFrame: DataFrame with an added due status column.
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
    Filter patients due for specific tests.

    Parameters:
    data (pd.DataFrame): DataFrame with due status columns.
    selected_tests (list): List of tests selected.
    test_mapping (dict): Mapping of test names to column names.

    Returns:
    pd.DataFrame: Filtered DataFrame for patients due for the selected tests.
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
    Calculate age in years from a given date of birth.

    Parameters:
    dob (str or datetime.date): Date of birth as a 'YYYY-MM-DD' string or a datetime.date object.

    Returns:
    int: Age in years.
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
    Calculate the length of diagnosis in months.

    Parameters:
    diagnosis_date (str or datetime.date): The date of first DM diagnosis.

    Returns:
    int: Length of diagnosis in months.
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
def load_and_preprocess_dashboard(file_path, col_list, test_info):
    """
    Load, preprocess, and calculate due columns for the dashboard.

    Parameters:
    file_path (str): Path to the CSV file.
    col_list (list): List of columns to convert to date format.
    test_info (dict): Contains columns and parameters for due calculations.

    Returns:
    pd.DataFrame: Preprocessed and enriched DataFrame with due status.
    """
    # Load the CSV file
    df = pd.read_csv(file_path)

# Check if columns are in DataFrame, and drop only those present
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])
    df.rename(columns= {'NHS Number': 'NHS number'}, inplace=True)
        # Handle NHS number - clean and convert
    df['NHS number'] = (
        df['NHS number']
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)  # Remove trailing .0 if present
        .str.replace(" ", "")  # Remove any spaces
    )

    # Convert valid numbers to integers, ignoring invalid entries
    df['NHS number'] = pd.to_numeric(df['NHS number'], errors='coerce').astype('Int64')
    # Convert specified columns to date only (no time part)
    for col in col_list:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    df['age'] = df['DOB'].apply(calculate_age)
    df['lenght_of_diagnosis_years'] = df['First DM Diagnosis'].apply(calculate_length_of_diagnosis)
    # Apply 'calculate_due_status' based on 'test_info' dictionary
    for test_name, params in test_info.items():
        df = calculate_due_status(df, **params)

    return df

plot_columns = [
    "age",
    "lenght_of_diagnosis_years",
    "HbA1c value",
    "DBP",
    "SBP",
    "Latest eGFR",
    "Total Chol",
    "Latest LDL",
    "Latest HDL",
    "Non-HDL Chol",
]

def plot_histograms(data, columns, color="#e3964a"):
    """
    Creates a 2x5 grid of histograms for each column specified in the `columns` list
    from the provided `data` DataFrame, and displays the plot in Streamlit.

    Parameters:
    - data (DataFrame): The dataset containing the columns to plot.
    - columns (list of str): List of column names to plot.
    - color (str): Color for the histograms. Default is '#f09235'.
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
    if notion_token != "" and notion_database != "":
        nh = NotionHelper(notion_token, notion_database)
        notion_df = nh.get_all_pages_as_dataframe()
        return notion_df

@st.cache_resource
def load_google_sheet_df(sheet_url, sheet_index):
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
    df['NHS number'] = df['NHS number'].astype(str).replace("", np.nan)
    df = df.dropna(subset=['NHS number'])
    df['NHS number'] = df['NHS number'].astype(int)
    return df


def extract_sms_df(intervention_df, sms_df, notion_df):
    intervention_df['NHS number'] = intervention_df['NHS number'].astype(int)
    sms_df["NHS number"] = sms_df["NHS number"].astype(int)
    output_sms_df = sms_df.merge(intervention_df[["NHS number"]], on="NHS number", how="inner")

    patients_to_contact = output_sms_df[~output_sms_df['NHS number'].isin(notion_df['NHS number'])]
    return patients_to_contact


def update_column_names(df):
    """
    Updates column names in a Pandas DataFrame by converting them to lower case and replacing spaces with underscores.

    Parameters:
        df (pd.DataFrame): Input DataFrame
    Returns:
        pd.DataFrame: The input DataFrame with updated column names
    """
    df.rename(columns=lambda x: x.lower().replace(' ', '_'), inplace=True)
    return df




def download_sms_csv(rewind_df, sms_df, notion_df, filename="dm_rewind_sms.csv"):
    """
    Extracts an SMS DataFrame, converts it to CSV, and provides a Streamlit download button.

    Parameters:
    - rewind_df (DataFrame): The DataFrame used as input for the SMS extraction.
    - sms_df (DataFrame): The SMS DataFrame to be extracted.
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
