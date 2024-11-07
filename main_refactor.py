import pandas as pd
import pendulum
from datetime import datetime, date

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
}

test_mapping = {
    "HbA1c": "hba1c_due",
    "Lipids": "lipids_due",
    "eGFR": "egfr_due",
    "Urine ACR": "urine_acr_due",
    "Foot": "foot_due",
}


def calculate_due_status(
    data,
    date_col,
    value_col=None,
    threshold_value=None,
    timeframe_years=1,
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


def load_and_preprocess_dashboard(file_path, col_list, test_info):
    """
    Load, preprocess, and calculate due columns for the dashboard.

    Parameters:
    file_path (str): Path to the CSV file.
    col_list (list): List of columns to convert to datetime.
    test_info (dict): Contains columns and parameters for due calculations.

    Returns:
    pd.DataFrame: Preprocessed and enriched DataFrame with due status.
    """
    df = pd.read_csv(file_path)
    for col in col_list:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    for test_name, params in test_info.items():
        df = calculate_due_status(df, **params)

    return df
