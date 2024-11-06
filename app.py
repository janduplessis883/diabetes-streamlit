import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import pendulum
from datetime import datetime, date
import seaborn as sns
import matplotlib.pyplot as plt


st.set_page_config(layout="wide")
st.image('dashboard.png')

st.logo("data_upload.png", size='large')


# File upload fields for CSVs
sms_file = st.sidebar.file_uploader("Upload Patient SMS List CSV", type="csv")
dashboard_file = st.sidebar.file_uploader("Upload Diabetes Dashboard CSV", type="csv")

# Load dataframes if files are uploaded
if sms_file is not None:
    sms_df = pd.read_csv(sms_file)

col_list = ['DOB', 'First DM Diagnosis', 'Annual Review Done', 'HbA1c', 'BP', 'Cholesterol', 'BMI', 'eGFR', 'Urine ACR', 'Smoking',
       'Foot Risk', 'Retinal screening', '9 KCP Complete',
       '3 Levels to Target', 'MH Screen - DDS or PHQ', 'Patient goals',
       'Care plan', 'Education', 'Care planning consultation']

def datetime_conversion(df, col_list):
    for col in col_list:
        # Check if the column exists in the dataframe to avoid KeyError
        if col in df.columns:
            # Ensure that the column is of string type to avoid issues
            df[col] = df[col].astype(str)

            # Replace invalid dates
            df[col] = df[col].replace(["00/01/1900", "01/01/1900"], "")

            # Convert to datetime format with specific date format and strip time
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce').dt.date
    return df

def calculate_age(dob):
    # Parse DOB if it's provided as a string
    if isinstance(dob, str):
        dob = datetime.strptime(dob, '%Y-%m-%d').date()

    # Get today's date
    today = datetime.today().date()

    # Calculate age
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age

def length_of_diagnosis_in_months(date_of_diagnosis):
    # Parse date_of_diagnosis if it's provided as a string
    if isinstance(date_of_diagnosis, str):
        date_of_diagnosis = datetime.strptime(date_of_diagnosis, '%Y-%m-%d').date()

    # Get today's date
    today = datetime.today().date()

    # Calculate difference in years and months
    years_difference = today.year - date_of_diagnosis.year
    months_difference = today.month - date_of_diagnosis.month

    # Total months difference
    total_months = years_difference * 12 + months_difference

    # Adjust if the current day of the month is before the diagnosis day
    if today.day < date_of_diagnosis.day:
        total_months -= 1

    return total_months

def calculate_hba1c_due(data, hba1c_value_col, hba1c_date_col, due_col='hba1c_due'):
    """
    Calculate if an HbA1c test is due based on the last HbA1c result.

    Parameters:
    data (pd.DataFrame): The DataFrame containing HbA1c values and dates.
    hba1c_value_col (str): The column name in the DataFrame containing HbA1c values.
    hba1c_date_col (str): The column name in the DataFrame containing the date of the last HbA1c test.
    due_col (str): The name of the new column where the due status will be stored.

    Returns:
    pd.DataFrame: The DataFrame with the new due status column.
    """
    # Current date
    now = pendulum.now()

    # Define the function to determine if HbA1c is due based on value and date
    def is_hba1c_due(row):
        hba1c_value = row[hba1c_value_col]
        last_hba1c_date = row[hba1c_date_col]

        if pd.isnull(last_hba1c_date) or pd.isnull(hba1c_value):
            return False  # If there's no date or value, we cannot determine due status

        # Determine the timeframe based on HbA1c value
        if hba1c_value < 53:
            timeframe = 1  # 1 year if < 53 mmol/mol
        elif 53 <= hba1c_value <= 75:
            timeframe = 0.5  # 6 months if 53–75 mmol/mol
        else:
            timeframe = 0.25  # 3 months if > 75 mmol/mol

        # Convert last HbA1c date to pendulum instance
        if isinstance(last_hba1c_date, (pd.Timestamp, datetime)):
            last_hba1c_date = last_hba1c_date.to_pydatetime()

        if isinstance(last_hba1c_date, (pd.Timestamp, date)):
            last_hba1c_date = last_hba1c_date.isoformat()

        last_hba1c_date = pendulum.parse(last_hba1c_date)

        # Check if the difference in years is greater than or equal to the timeframe
        return (now - last_hba1c_date).in_years() >= timeframe

    # Apply the function to each row in the DataFrame
    data[due_col] = data.apply(is_hba1c_due, axis=1)

    return data


def calculate_lipids_due(data, cholesterol_date_col, due_col='lipids_due'):
    """
    Determine if a lipid test is due based on the last cholesterol test date.

    Parameters:
    data (pd.DataFrame): The DataFrame containing the date of the last cholesterol test.
    cholesterol_date_col (str): The column name in the DataFrame containing the cholesterol test dates.
    due_col (str): The name of the new column where the due status will be stored.

    Returns:
    pd.DataFrame: The DataFrame with the new due status column.
    """
    # Current date
    now = pendulum.now()

    # Define the function to determine if lipid test is due
    def is_lipids_due(row):
        last_cholesterol_date = row[cholesterol_date_col]

        # Check if the date is missing
        if pd.isnull(last_cholesterol_date):
            return False  # No date means we can't determine if it's due

        # Convert last cholesterol test date to pendulum instance if it’s not already
        if isinstance(last_cholesterol_date, (pd.Timestamp, datetime, pendulum.DateTime)):
            last_cholesterol_date = pendulum.instance(last_cholesterol_date)
        elif isinstance(last_cholesterol_date, str):
            last_cholesterol_date = pendulum.parse(last_cholesterol_date)
        elif isinstance(last_cholesterol_date, date):  # Check for `datetime.date` specifically
            last_cholesterol_date = pendulum.instance(pd.Timestamp(last_cholesterol_date))

        # Check if the difference is greater than or equal to 1 year
        return (now - last_cholesterol_date).in_years() >= 1

    # Apply the function to each row in the DataFrame
    data[due_col] = data.apply(is_lipids_due, axis=1)

    return data

def calculate_foot_due(data, foot_date_col, due_col='foot_due'):
    """
    Determine if a foot check is due based on the last foot check date.

    Parameters:
    data (pd.DataFrame): The DataFrame containing the date of the last foot check.
    foot_date_col (str): The column name in the DataFrame containing the foot check dates.
    due_col (str): The name of the new column where the due status will be stored.

    Returns:
    pd.DataFrame: The DataFrame with the new due status column.
    """
    # Current date
    now = pendulum.now()

    # Define the function to determine if foot check is due
    def is_foot_due(row):
        last_foot_check_date = row[foot_date_col]

        # Check if the date is missing
        if pd.isnull(last_foot_check_date):
            return False  # No date means we can't determine if it's due

        # Convert last foot check date to pendulum instance if it’s not already
        if isinstance(last_foot_check_date, (pd.Timestamp, datetime, pendulum.DateTime)):
            last_foot_check_date = pendulum.instance(last_foot_check_date)
        elif isinstance(last_foot_check_date, str):
            last_foot_check_date = pendulum.parse(last_foot_check_date)
        elif isinstance(last_foot_check_date, date):  # Check for `datetime.date` specifically
            last_foot_check_date = pendulum.instance(pd.Timestamp(last_foot_check_date))

        # Check if the difference is greater than or equal to 1 year
        return (now - last_foot_check_date).in_years() >= 1

    # Apply the function to each row in the DataFrame
    data[due_col] = data.apply(is_foot_due, axis=1)

    return data


def calculate_egfr_due(data, egfr_value_col, egfr_date_col, due_col='egfr_due'):
    """
    Determine if an eGFR test is due based on the last eGFR value and test date.

    Parameters:
    data (pd.DataFrame): The DataFrame containing eGFR values and dates.
    egfr_value_col (str): The column name in the DataFrame containing eGFR values.
    egfr_date_col (str): The column name in the DataFrame containing the date of the last eGFR test.
    due_col (str): The name of the new column where the due status will be stored.

    Returns:
    pd.DataFrame: The DataFrame with the new due status column.
    """
    # Current date
    now = pendulum.now()

    # Define the function to determine if eGFR test is due based on value and date
    def is_egfr_due(row):
        egfr_value = row[egfr_value_col]
        last_egfr_date = row[egfr_date_col]

        # Check if the date or value is missing
        if pd.isnull(last_egfr_date) or pd.isnull(egfr_value):
            return False  # If there's no date or value, we cannot determine due status

        # Determine the timeframe based on eGFR value
        if egfr_value <= 30:
            timeframe = 0.5  # 6 months if eGFR <= 30
        else:
            timeframe = 1  # 1 year if eGFR > 30

        # Convert last eGFR date to pendulum instance
        if isinstance(last_egfr_date, (pd.Timestamp, datetime)):
            last_egfr_date = last_egfr_date.to_pydatetime()

        if isinstance(last_egfr_date, (pd.Timestamp, date)):
            last_egfr_date = last_egfr_date.isoformat()

        last_egfr_date = pendulum.parse(last_egfr_date)

        # Check if the difference in years is greater than or equal to the timeframe
        return (now - last_egfr_date).in_years() >= timeframe

    # Apply the function to each row in the DataFrame
    data[due_col] = data.apply(is_egfr_due, axis=1)

    return data

def calculate_urine_acr_due(data, acr_date_col, due_col='urine_acr_due'):
    """
    Determine if a urine ACR test is due based on the last test date.

    Parameters:
    data (pd.DataFrame): The DataFrame containing the date of the last urine ACR test.
    acr_date_col (str): The column name in the DataFrame containing the urine ACR test dates.
    due_col (str): The name of the new column where the due status will be stored.

    Returns:
    pd.DataFrame: The DataFrame with the new due status column.
    """
    # Current date as a pendulum DateTime object
    now = pendulum.now()

    # Define the function to determine if urine ACR is due
    def is_urine_acr_due(row):
        last_acr_date = row[acr_date_col]

        # Check if the date is missing
        if pd.isnull(last_acr_date):
            return False  # No date means we can't determine if it's due

        # Ensure last_acr_date is a pendulum DateTime instance
        if isinstance(last_acr_date, pd.Timestamp):
            last_acr_date = pendulum.instance(last_acr_date.to_pydatetime())
        elif isinstance(last_acr_date, date):  # for datetime.date
            last_acr_date = pendulum.instance(pd.Timestamp(last_acr_date))
        elif isinstance(last_acr_date, str):
            last_acr_date = pendulum.parse(last_acr_date)

        # Check if the last ACR test was more than 1 year ago
        return (now - last_acr_date).in_years() >= 1

    # Apply the is_urine_acr_due function to each row in the DataFrame
    data[due_col] = data.apply(is_urine_acr_due, axis=1)

    # Return the modified DataFrame
    return data

# Function to highlight a list of columns
def highlight_columns(columns, color='#fdf7f2'):
    def style_columns(val):
        return f'background-color: {color}'
    return df.style.applymap(style_columns, subset=columns)



def load_dashboard(file):
    # Load and preprocess the dashboard DataFrame
    df = pd.read_csv(file)
    # Filter DataFrame for specific conditions
    df.drop(columns=['Column1', 'Column2', 'Column3', 'Column4',
       'Column5', 'Column6', 'Column7', 'Column8', 'Column9','Group consultations', 'Hypo Mon Denom', 'Month of Birth',
       'EFi Score', 'Frailty', 'QoF Invites Done', 'QoF DM006D',
       'QoF DM006 Achieved', 'QoF DM012D', 'QoF DM012 Achieved', 'QoF DM014D',
       'QoF DM014 Achieved', 'QoF BP Done', 'QoF DM019D', 'QoF DM019 Achieved',
       'QoF HbA1c Done', 'QoF DM020D', 'QoF DM020 Achieved', 'QoF DM021D',
       'QoF DM021 Achieved', 'QoF DM022D', 'QoF DM022 Achieved', 'QoF DM023D',
       'QoF DM023 Achieved', 'HbA1c Trend', 'Diag L6y HbA1c <=53', 'Type 1', 'Type 2', 'Both Types Recorded', 'No Type Recorded',
       'Outstanding ES Count', 'Outstanding QoF Count', 'Total Outstanding',
       'Next Appt Date', 'Next Appt with', 'Number Future Appts', 'COVID-19 High Risk', 'GLP-1 or Insulin', 'Unnamed: 110',
       'Unnamed: 111', 'Unnamed: 112', 'Unnamed: 113', 'Unnamed: 114',
       'Unnamed: 115', 'Unnamed: 116', 'Unnamed: 117'], inplace=True)
    df.rename(columns= {'NHS Number': 'NHS number'}, inplace=True)
    df['NHS number'] = df['NHS number'].str.replace(" ", "").astype(int)
    df = datetime_conversion(df, col_list)
    df = calculate_hba1c_due(df, hba1c_value_col='HbA1c value', hba1c_date_col='HbA1c', due_col='hba1c_due')
    df['hba1c_due'] = df['hba1c_due'].astype(bool)
    df = calculate_lipids_due(df, "Cholesterol", "lipids_due")
    df['lipids_due'] = df['lipids_due'].astype(bool)
    df = calculate_foot_due(df, foot_date_col='Foot Risk', due_col='foot_due')
    df['foot_due'] = df['foot_due'].astype(bool)
    df = calculate_egfr_due(df, egfr_value_col='Latest eGFR', egfr_date_col='eGFR', due_col='egfr_due')
    df['egfr_due'] = df['egfr_due'].astype(bool)
    df = calculate_urine_acr_due(df, acr_date_col='Urine ACR', due_col='urine_acr_due')
    df['urine_acr_due'] = df['urine_acr_due'].astype(bool)
    df['age'] = df['DOB'].apply(calculate_age)
    df['length_of_diagnosis_months'] = df['First DM Diagnosis'].apply(length_of_diagnosis_in_months)
    return df

if dashboard_file is not None:
    df = load_dashboard(dashboard_file)


def extract_sms_df(intervention_df, sms_df):
    sms_df['NHS number'] = sms_df['NHS number'].astype(int)
    output_sms_df = sms_df.merge(intervention_df[['NHS number']], on='NHS number', how='inner')
    print(f"Patient count: {output_sms_df.shape[0]}")
    return output_sms_df


def filter_due_patients(data, selected_tests):
    """
    Filter patients due for specific tests based on selected tests.

    Parameters:
    data (pd.DataFrame): The DataFrame containing the due status columns for various tests.
    selected_tests (list): The list of tests selected in the multi-select field.

    Returns:
    pd.DataFrame: A DataFrame filtered to include only patients due for the selected tests.
    """
    # Mapping of test names to DataFrame columns
    test_columns = {
        "HbA1c": "hba1c_due",
        "Lipids": "lipids_due",
        "eGFR": "egfr_due",
        "Urine ACR": "urine_acr_due",
        "Foot": "foot_due"
    }

    # Ensure all columns are boolean
    for col in test_columns.values():
        if col in data.columns:
            data[col] = data[col].astype(bool)

    # Create filter conditions based on selected tests
    filter_conditions = [data[test_columns[test]] for test in selected_tests if test in test_columns]

    # If no valid tests are selected, return an empty DataFrame
    if not filter_conditions:
        return data.iloc[0:0]

    # Combine all conditions with logical OR
    combined_filter = filter_conditions[0]
    for condition in filter_conditions[1:]:
        combined_filter |= condition

    # Debugging print statements
    st.write("Selected Tests:", selected_tests)
    st.write("Filter Conditions Applied:", combined_filter.sum(), "rows match the filter.")

    # Return the filtered data
    return data[combined_filter]



tab_selector = ui.tabs(
    options=[
        "Quick Start",
        "Online Pre-assessment",
        "HCA Self-book",
        "Rewind",
        "Patient Search",
        "Filter Dataframe",
        "Guidelines"
    ],
            default_value="Quick Start",
            key="tab3",
        )

if tab_selector == "Online Pre-assessment":
    st.image("online.png")
    st.write("Send **Tally Form** Pre-asessment")
    if 'sms_df' not in globals() or 'df' not in globals():
        st.warning('Please upload both CSV files to proceed.')


elif tab_selector == "HCA Self-book":
    st.image("hca.png")
    if 'sms_df' not in globals() or 'df' not in globals():
        st.warning('Please upload both CSV files to proceed.')
    selected_tests = st.multiselect(
        "Select tests to include:",
        options=["HbA1c", "Lipids", "eGFR", "Urine ACR", "Foot"],
        default=["HbA1c"]
    )
    # Call the filter_due_patients function with the DataFrame and selected tests
    due_patients = filter_due_patients(df, selected_tests)
    sns.histplot(data=due_patients, x='HbA1c value')
    # Display the filtered DataFrame if there are results

    if not due_patients.empty:
        st.dataframe(due_patients[['Patient ID', 'NHS number', 'First Name', 'Surname', 'DOB', 'Usual GP',
       'E-Mail Address', 'E-Mail Address Recorded', 'IMD Decile', 'Ethnicity',
       'BAME', 'First DM Diagnosis', 'Diabetes diagnosis', 'HbA1c value',
       'SBP', 'DBP', 'Total Chol', 'Non-HDL Chol', 'Latest HDL', 'Latest LDL',
       'Latest eGFR', 'Latest BMI', 'hba1c_due', 'lipids_due',
       'foot_due', 'egfr_due', 'urine_acr_due', 'age',
       'length_of_diagnosis_months', 'Latest Qrisk2', 'Annual Review Done',
       'HbA1c', 'BP', 'Cholesterol', 'BMI', 'eGFR', 'Urine ACR', 'Smoking',
       'Foot Risk', 'Retinal screening', '9 KCP Complete',
       '3 Levels to Target', 'MH Screen - DDS or PHQ', 'Patient goals',
       'Care plan', 'Education', 'Care planning consultation',
       'Struc educ in L5Y', 'Struc educ in 12M Diag', 'Risk Factor',
       'Eligible for REWIND', 'REWIND - Started', 'Hypo monitoring',
       'Statin date', 'Statin', 'Metformin', 'Sulphonylurea', 'DPP4', 'SGLT2',
       'Pioglitazone', 'GLP-1', 'Basal / mix insulin', 'Rapid acting insulin',
       'ACEI/ARB', 'Calcium Channel Blocker', 'Diuretic', 'Beta Blocker',
       'Spironolactone', 'Doxazosin', 'Review Due',]])


        # Create a single row with 5 subplots
        # Create a single row with 5 subplots

        fig, axes = plt.subplots(2, 5, figsize=(20, 6), sharey=True)

        # Column names to plot (make sure you have up to 10 columns to fill each subplot)
        columns = ['age', 'length_of_diagnosis_months','HbA1c value',  'DBP', 'SBP', 'Latest eGFR',
                                'Total Chol', 'Latest LDL', 'Latest HDL', 'Non-HDL Chol']

        # Loop over each column and create a histogram
        for i, col in enumerate(columns):
            row, col_index = divmod(i, 5)  # Determine row and column index in 2x5 grid
            sns.histplot(data=due_patients, x=col, ax=axes[row, col_index], color='#f09235', bins=15)
            #axes[row, col_index]

            # Remove top and right borders
            axes[row, col_index].spines['top'].set_visible(False)
            axes[row, col_index].spines['right'].set_visible(False)
            axes[row, col_index].spines['left'].set_visible(False)

            # Add horizontal grid lines with specific thickness
            axes[row, col_index].yaxis.grid(True, linewidth=0.5)
            axes[row, col_index].grid(axis='x', visible=False)  # Optional: hides vertical grid lines if not desired

        # Hide any unused subplots if columns are less than 10
        for j in range(len(columns), 10):
            fig.delaxes(axes.flatten()[j])

        # Display the plot in Streamlit
        st.pyplot(fig)

    else:
        st.warning('Please upload the necessary CSV file to display the dataframe. Select as least one criteria to filter by.')

elif tab_selector == "Filter Dataframe":
    st.image("filter.png")
    if 'df' not in globals():
        st.warning('Please upload the Diabetes Dashboard CSV file to proceed.')
        # Get the min and max values for each column to use in sliders
    metrics = {
        "HbA1c value": ("HbA1c value", df["HbA1c value"].min(), df["HbA1c value"].max()),
        "SBP": ("SBP", df["SBP"].min(), df["SBP"].max()),
        "DBP": ("DBP", df["DBP"].min(), df["DBP"].max()),
        "Latest LDL": ("Latest LDL", df["Latest LDL"].min(), df["Latest LDL"].max()),
        "Latest eGFR": ("Latest eGFR", df["Latest eGFR"].min(), df["Latest eGFR"].max()),
        "Latest BMI": ("Latest BMI", df["Latest BMI"].min(), df["Latest BMI"].max()),
    }

    # Dictionary to store slider values for each metric
    filter_values = {}

    # Create sliders for each metric and store the selected range
    for key, (label, min_val, max_val) in metrics.items():
        filter_values[key] = st.sidebar.slider(
            f"Select {label} range",
            min_value=float(min_val),
            max_value=float(max_val),
            value=(float(min_val), float(max_val))
        )

    # Filter the DataFrame based on the selected ranges for all metrics
    filtered_df = df.copy()
    for key, (label, _, _) in metrics.items():
        min_val, max_val = filter_values[key]
        filtered_df = filtered_df[(filtered_df[key] >= min_val) & (filtered_df[key] <= max_val)]

    # Display the filtered DataFrame
    st.write("Filtered DataFrame based on selected ranges:")
    st.markdown("Patient count: " + str(filtered_df.shape[0]))
    st.dataframe(filtered_df)  # Only shows rows within the slider-selected ranges

    # Display the count of patients in the filtered DataFrame


elif tab_selector == "Rewind":
    st.image("rewind.png")
    if 'sms_df' not in globals() or 'df' not in globals():
        st.warning('Please upload both CSV files to proceed.')
    rewind_df = df[(df['Eligible for REWIND'] == 'Yes') & (df['REWIND - Started'] == 0)]
    st.markdown("Patient count: " + str(rewind_df.shape[0]))
    st.dataframe(rewind_df)
    output_sms_df = extract_sms_df(rewind_df, sms_df)
    csv = output_sms_df.to_csv(index=False)
    st.download_button(
        label="Download Rewind SMS List as CSV",
        data=csv,
        file_name='dm_rewind_sms.csv',
        mime='text/csv'
    )



elif tab_selector == "Patient Search":
    st.image("search.png")


elif tab_selector == "Guidelines":
    st.image("guidelines.png")

    st.write("""In the management of diabetes, the frequency of monitoring various metrics can change based on the patient’s condition and previous results. According to NICE (National Institute for Health and Care Excellence) guidelines, here are recommended timeframes for common diabetic metrics, with adjustments based on results:

1. **HbA1c (Glycated Hemoglobin)**

	-	If < 53 mmol/mol (7%): Check annually. This indicates good control for most patients.
	-	If 53–75 mmol/mol (7%–9%): Check every 3-6 months. For higher levels, more frequent monitoring is suggested to assess whether treatment adjustments are improving control.
	-	If > 75 mmol/mol (9%): Check every 3 months. Regular monitoring is needed to bring levels down, as high HbA1c indicates increased risk of complications.

2. **Blood Pressure**

	-	Target Range: Usually < 140/80 mmHg, but < 130/80 mmHg for those with kidney, eye, or cerebrovascular disease.
	-	Frequency:
	-	Stable and well-controlled: Check annually.
	-	Above target range: Check every 1–3 months until target is achieved, adjusting medications as necessary.

3. **Lipid Profile (Cholesterol)**

	-	Stable and on statin therapy: Check annually.
	-	If initiating or changing lipid-lowering treatment: Check at 3 months to assess the impact and adjust doses if necessary.

4. **Renal Function (eGFR and ACR)**

	-	Normal renal function and stable: Check annually.
	-	Reduced kidney function or albuminuria: Check every 6 months or more frequently if there is progressive decline.

5. **Eye Screening**

	-	No signs of retinopathy: Check annually with digital retinal photography.
	-	If signs of retinopathy or high-risk: May require more frequent checks, such as every 6 months, based on ophthalmology advice.

6. **Foot Examination**

	-	Low risk (no risk factors): Check annually.
	-	Moderate risk (one risk factor, e.g., neuropathy): Check every 3–6 months by a foot protection team.
	-	High risk (ulcers, previous amputation, deformity): Check every 1–3 months or as frequently as required, with regular input from specialists.

7. **Body Mass Index (BMI) and Weight**

	-	General Monitoring: Check annually or every 6 months if BMI > 30 or weight management is a goal.
	-	If on weight loss medications or interventions: Check every 3 months.""")

    st.image('table.png')






elif tab_selector == "Quick Start":
    st.image("start.png")
    st.write("""### Step 1: Upload Data Files

**Access the Sidebar**: On the left side of the app, you'll find the sidebar containing file upload options.

**Upload CSV Files**:

**Patient SMS List CSV**: Click on "Upload Patient SMS List CSV" and select your patient SMS list file.

**Diabetes Dashboard CSV**: Click on "Upload Diabetes Dashboard CSV" and select your diabetes dashboard data file.

Ensure Correct Formatting: Make sure your CSV files are properly formatted and include all necessary columns as expected by the app.

### Step 2: Navigate Through the App Tabs

The app is organized into several tabs, each designed to assist with different aspects of patient management:

**Quick Start**: Provides an overview and initial guidance on using the app.
Online Pre-assessment:
Purpose: Send Tally Form pre-assessments to patients.
Action Required: Ensure both the Patient SMS List CSV and Diabetes Dashboard CSV files are uploaded to utilize this feature.
HCA Self-book:
Identify Due Patients: Use this tab to filter and identify patients who are due for specific tests.
Select Tests: Choose from HbA1c, Lipids, eGFR, Urine ACR, and Foot examinations using the multi-select option.
View Results: The app displays a list of patients due for the selected tests along with interactive histograms of key metrics.
Download SMS List: Extract a CSV file of patients to facilitate SMS outreach for appointment bookings.
Rewind:
Focus on REWIND Program: This tab highlights patients eligible for the REWIND program who have not yet started it.
View and Download: Access the list of eligible patients and download their contact information for outreach.
Patient Search:
Individual Lookup: Search for individual patients using specific criteria.
Note: This feature requires the Diabetes Dashboard CSV to be uploaded.
Filter Dataframe:
Advanced Filtering: Use sidebar sliders to filter patients based on various metrics such as HbA1c value, SBP, DBP, LDL, eGFR, and BMI.
Analyze Data: View the filtered patient list and analyze the data to make informed clinical decisions.
Guidelines:
Reference Material: Access summarized NICE guidelines for diabetes management directly within the app.
Stay Informed: Use this information to ensure your practice aligns with the recommended monitoring frequencies and target values.
""")
