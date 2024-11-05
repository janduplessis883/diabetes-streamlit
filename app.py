import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import pendulum
from datetime import datetime, date

st.set_page_config(layout="wide")
st.image('dashboard.png')



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
        # Remove invalid dates
        df[col] = df[col].str.replace("00/01/1900", "").replace("01/01/1900", "")

        # Convert to datetime format with specific date format and strip time
        df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce').dt.date
    return df


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
    return df

if dashboard_file is not None:
    df = load_dashboard(dashboard_file)


def extract_sms_df(intervention_df, sms_df):
    sms_df['NHS number'] = sms_df['NHS number'].astype(int)
    output_sms_df = sms_df.merge(intervention_df[['NHS number']], on='NHS number', how='inner')
    print(f"Patient count: {output_sms_df.shape[0]}")
    return output_sms_df






tab_selector = ui.tabs(
            options=[
                "Online Pre-assessment",
                "HCA Self-book",
                "Rewind",
                "Filter Dataframe",
                "Patient Search",
                "Guidelines"
            ],
            default_value="Online Pre-assessment",
            key="tab3",
        )

if tab_selector == "Online Pre-assessment":
    st.image("online.png")
    st.write("Send **Tally Form** Pre-asessment")
    st.dataframe(df)

elif tab_selector == "HCA Self-book":
    st.image("hca.png")
    selected_tests = st.multiselect(
        "Select tests to include:",
        options=["HBa1c", "Lipids", "eGFR", "Urine ACR", "Foot"],
        default=[]
    )
    if selected_tests == ['HBa1c']:
        hba1c_due = df[(df['hba1c_due'] == True)]
        st.dataframe(hba1c_due)

elif tab_selector == "Filter Dataframe":
    st.image("filter.png")
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
