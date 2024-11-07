import streamlit as st
import pandas as pd
import streamlit_shadcn_ui as ui
import pendulum
from datetime import datetime, date
import seaborn as sns
import matplotlib.pyplot as plt

from main2 import (
    load_and_preprocess_dashboard,
    filter_due_patients,
    test_mapping,
    test_info,
    col_list,
    plot_columns,
    plot_histograms,
    download_sms_csv,
    extract_sms_df
)

st.set_page_config(layout="wide", page_title="Diabetes Dashboard")
st.image("dashboard.png")

st.logo("data_upload.png", size="large")

# File upload fields for CSVs
sms_file = st.sidebar.file_uploader("Upload Patient SMS List CSV", type="csv")
dashboard_file = st.sidebar.file_uploader("Upload Diabetes Dashboard CSV", type="csv")

# Load dataframes if files are uploaded
if sms_file is not None:
    sms_df = pd.read_csv(sms_file)

if dashboard_file is not None:
    df = load_and_preprocess_dashboard(dashboard_file, col_list, test_info)


tab_selector = ui.tabs(
    options=[
        "Quick Start",
        "Online Pre-assessment",
        "HCA Self-book",
        "Rewind",
        "Patient Search",
        "Filter Dataframe",
        "Guidelines",
    ],
    default_value="Quick Start",
    key="tab3",
)

if tab_selector == "Online Pre-assessment":
    st.image("online.png")
    st.image("mermaid.png")
    if "sms_df" not in globals() or "df" not in globals():
        st.warning("Please upload both CSV files to proceed.")


elif tab_selector == "HCA Self-book":
    st.image("hca.png")
    if "sms_df" not in globals() or "df" not in globals():
        st.warning("Please upload both CSV files to proceed.")

    c1, c2 = st.columns(2)
    with c1:
        selected_tests = st.multiselect(
            "Select **Tests** to include:",
            options=["HbA1c", "Lipids", "eGFR", "Urine ACR", "Foot"],
            default=["HbA1c"],
        )
    with c2:
        st.write()
    # Call the filter_due_patients function with the DataFrame and selected tests
    due_patients = filter_due_patients(df, selected_tests, test_mapping)

    if not due_patients.empty:
        plot_histograms(due_patients, plot_columns)
        st.dataframe(due_patients, height=300)
        download_sms_csv(due_patients, sms_df, filename="hca_selfbook_sms.csv")


    else:
        st.warning(
            "Please upload the necessary CSV file to display the dataframe. Select at least one criterion to filter by."
        )


elif tab_selector == "Filter Dataframe":
    st.image("filter.png")
    if "df" not in globals():
        st.warning("Please upload the Diabetes Dashboard CSV file to proceed.")
    else:
        # Get the min and max values for each column to use in sliders
        metrics = {
            "HbA1c value": (
                "HbA1c value",
                df["HbA1c value"].min(),
                df["HbA1c value"].max(),
            ),
            "SBP": ("SBP", df["SBP"].min(), df["SBP"].max()),
            "DBP": ("DBP", df["DBP"].min(), df["DBP"].max()),
            "Latest LDL": (
                "Latest LDL",
                df["Latest LDL"].min(),
                df["Latest LDL"].max(),
            ),
            "Latest eGFR": (
                "Latest eGFR",
                df["Latest eGFR"].min(),
                df["Latest eGFR"].max(),
            ),
            "Latest BMI": (
                "Latest BMI",
                df["Latest BMI"].min(),
                df["Latest BMI"].max(),
            ),
        }

        # Dictionary to store slider values for each metric
        filter_values = {}

        # Create sliders for each metric and store the selected range
        for key, (label, min_val, max_val) in metrics.items():
            filter_values[key] = st.sidebar.slider(
                f"Select {label} range",
                min_value=float(min_val),
                max_value=float(max_val),
                value=(float(min_val), float(max_val)),
            )

        # Filter the DataFrame based on the selected ranges for all metrics
        filtered_df = df.copy()
        for key, (label, _, _) in metrics.items():
            min_val, max_val = filter_values[key]
            filtered_df = filtered_df[
                (filtered_df[key] >= min_val) & (filtered_df[key] <= max_val)
            ]

        # Display the filtered DataFrame
        st.write("Filtered DataFrame based on selected ranges:")
        st.markdown("Patient count: " + str(filtered_df.shape[0]))
        plot_histograms(filtered_df, plot_columns)
        st.dataframe(filtered_df, height=300)  # Only shows rows within the slider-selected ranges

        download_sms_csv(filtered_df, sms_df, filename="filtered_data_sms.csv")

elif tab_selector == "Rewind":
    st.image("rewind.png")
    if "sms_df" not in globals() or "df" not in globals():
        st.warning("Please upload both CSV files to proceed.")
    else:
        rewind_df = df[
            (df["Eligible for REWIND"] == "Yes") & (df["REWIND - Started"] == 0)
        ]
        st.markdown("Patient count: " + str(rewind_df.shape[0]))
        st.dataframe(rewind_df)
        output_sms_df = extract_sms_df(rewind_df, sms_df)
        csv = output_sms_df.to_csv(index=False)
        st.download_button(
            label="Download Rewind SMS List as CSV",
            data=csv,
            file_name="dm_rewind_sms.csv",
            mime="text/csv",
        )


elif tab_selector == "Patient Search":
    st.image("search.png")


elif tab_selector == "Guidelines":
    st.image("guidelines.png")

    st.write(
        """In the management of diabetes, the frequency of monitoring various metrics can change based on the patient’s condition and previous results. According to NICE (National Institute for Health and Care Excellence) guidelines, here are recommended timeframes for common diabetic metrics, with adjustments based on results:

1. **HbA1c (Glycated Hemoglobin)**

	- If < 53 mmol/mol (7%): Check annually. This indicates good control for most patients.
	- If 53–75 mmol/mol (7%–9%): Check every 3-6 months. For higher levels, more frequent monitoring is suggested to assess whether treatment adjustments are improving control.
	- If > 75 mmol/mol (9%): Check every 3 months. Regular monitoring is needed to bring levels down, as high HbA1c indicates increased risk of complications.

2. **Blood Pressure**

	- Target Range: Usually < 140/80 mmHg, but < 130/80 mmHg for those with kidney, eye, or cerebrovascular disease.
	- Frequency:
	  - Stable and well-controlled: Check annually.
	  - Above target range: Check every 1–3 months until target is achieved, adjusting medications as necessary.

3. **Lipid Profile (Cholesterol)**

	- Stable and on statin therapy: Check annually.
	- If initiating or changing lipid-lowering treatment: Check at 3 months to assess the impact and adjust doses if necessary.

4. **Renal Function (eGFR and ACR)**

	- Normal renal function and stable: Check annually.
	- Reduced kidney function or albuminuria: Check every 6 months or more frequently if there is progressive decline.

5. **Eye Screening**

	- No signs of retinopathy: Check annually with digital retinal photography.
	- If signs of retinopathy or high-risk: May require more frequent checks, such as every 6 months, based on ophthalmology advice.

6. **Foot Examination**

	- Low risk (no risk factors): Check annually.
	- Moderate risk (one risk factor, e.g., neuropathy): Check every 3–6 months by a foot protection team.
	- High risk (ulcers, previous amputation, deformity): Check every 1–3 months or as frequently as required, with regular input from specialists.

7. **Body Mass Index (BMI) and Weight**

	- General Monitoring: Check annually or every 6 months if BMI > 30 or weight management is a goal.
	- If on weight loss medications or interventions: Check every 3 months."""
    )

    st.image("table.png")


elif tab_selector == "Quick Start":
    st.image("start.png")
    st.write(
        """### Step 1: Upload Data Files

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
"""
    )
