import pandas as pd
import streamlit_shadcn_ui as ui
import pendulum
from datetime import datetime, date
import seaborn as sns
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

import numpy as np
import gspread


from main import (
    load_and_preprocess_dashboard,
    filter_due_patients,
    test_mapping,
    test_info,
    col_list,
    plot_columns,
    plot_histograms,
    download_sms_csv,
    online_mapping,
    load_notion_df,
    load_google_sheet_df
)
# from predict import *
from notionhelper import *


# Initialize session states if they haven't been set already
if "notion_token" not in st.session_state:
    st.session_state["notion_token"] = ""
if "notion_database" not in st.session_state:
    st.session_state["notion_database"] = ""
if "notion_connected" not in st.session_state:
    st.session_state["notion_connected"] = 'offline'
if "sheet_url" not in st.session_state:
    st.session_state["sheet_url"] = ""

# Define a callback function to set the token and database in session state
def set_notion_credentials(notion_token, notion_database):
    st.session_state["notion_token"] = notion_token
    st.session_state["notion_database"] = notion_database
    st.session_state["notion_connected"] = 'connected'
    st.session_state["sheet_url"] = ""

def disconnect_notion():
    st.session_state["notion_token"] = ""
    st.session_state["notion_database"] = ""
    st.session_state["notion_connected"] = 'offline'
    st.session_state["sheet_url"] = ""

def set_google_sheet_credentials(sheet_url):
    st.session_state["notion_token"] = ""
    st.session_state["notion_database"] = ""
    st.session_state["notion_connected"] = 'offline'
    st.session_state["sheet_url"] = sheet_url

def disconnect_google_sheet():
    st.session_state["notion_token"] = ""
    st.session_state["notion_database"] = ""
    st.session_state["notion_connected"] = 'offline'
    st.session_state["sheet_url"] = ""

# Set page configuration
st.set_page_config(layout="wide", page_title="A1Sense - Diabetes Dashboard")

# Display images
st.image("images/dashboard.png")


if st.session_state['notion_connected'] == 'connected' and st.session_state['sheet_url'] == "":
    st.sidebar.image("images/notion_connected.png")
elif st.session_state['notion_connected'] == 'offline' and st.session_state['sheet_url'] == "":
    st.sidebar.image("images/notion_offline.png")
elif st.session_state['sheet_url'] != '' and st.session_state['notion_connected'] == "offline":
    st.sidebar.image("images/google_online.png")
elif st.session_state['sheet_url'] == '' and st.session_state['notion_connected'] == "offline":
    st.sidebar.image("images/google_offline.png")
else:
    st.sidebar.image("notion_offline.png")



st.sidebar.subheader("Upload Data")
# File upload fields for CSVs
sms_file = st.sidebar.file_uploader("Upload **Diabetes Register Accurx SMS** csv", type="csv")
dashboard_file = st.sidebar.file_uploader("Upload **Diabetes Dashboard** as csv", type="csv")
st.sidebar.divider()
st.sidebar.subheader("Integrations")
# Radio button for selecting either Notion or Google Sheets
option = st.sidebar.radio("Select **Integration**:", ("Notion", "Google Sheets"), key="integration_option")


if option == "Notion":

    # Notion credentials form
    with st.sidebar.form("notion_form", border=False):
        notion_token = st.text_input("Notion Token", type="password", value=st.session_state["notion_token"])
        notion_database = st.text_input("Notion Database ID", value=st.session_state["notion_database"])

        # Form submit button


        # Check if form was submitted
        if st.session_state["notion_connected"] == 'offline':
            notion_submit = st.form_submit_button("Connect to Notion")
            if notion_submit:
                # Save to session state using the callback logic
                set_notion_credentials(notion_token, notion_database)
                st.rerun()
        elif st.session_state["notion_connected"] == 'connected':
            disconnect = st.form_submit_button("Disconnect Notion")
            if disconnect:
                disconnect_notion()
                st.rerun()


elif option == "Google Sheets":


    with st.sidebar.form("google_form", border=False):
        sheet_url = st.text_input("**Google Sheet URL**:", value=st.session_state["sheet_url"])

        # Check if form was submitted
        if st.session_state["sheet_url"] == "":
            google_submit = st.form_submit_button("Connect to Google Sheets")
            if google_submit:
                # Save to session state using the callback logic
                set_google_sheet_credentials(sheet_url)
                st.rerun()
        elif st.session_state["sheet_url"] != "":
            disconnect = st.form_submit_button("Disconnect Google Sheets")
            if disconnect:
                disconnect_google_sheet()
                st.rerun()



# Load dataframes if files are uploaded
if sms_file is not None:
    sms_df = pd.read_csv(sms_file)

if dashboard_file is not None:
    df = load_and_preprocess_dashboard(dashboard_file, col_list, test_info)
    nhs_df = df[["NHS number", "HbA1c value"]]
    # prediction = predict(df, nhs_df)

if st.session_state["notion_connected"] == 'connected':
    actioned_df = load_notion_df(st.session_state["notion_token"], st.session_state["notion_database"])
elif st.session_state["notion_connected"] == 'offline' and st.session_state["sheet_url"] != "":
    actioned_df = load_google_sheet_df(st.session_state["sheet_url"], 0)
else:
    actioned_df = pd.DataFrame({
                            "NHS number": [np.nan],
                            "Name": ["Empty"]
                            })

tab_selector = ui.tabs(
    options=[
        "Quick Start",
        "Online Pre-assessment",
        "HCA Self-book",
        "Rewind",
        "Filter Dataframe",
        "Predicted Hba1c - Regression",
        "Guidelines",
        "Integrations",
    ],
    default_value="Quick Start",
    key="tab3",
)

if tab_selector == "Online Pre-assessment":

    if "sms_df" not in globals() or "df" not in globals():
        st.warning("Please upload both CSV files to proceed.")

    c1, c2 = st.columns(2)
    with c1:
        selected_tests = st.multiselect(
            "Select **Pre-assessment Criteria** to include:",
            options=["Annual Review Done", "Care plan", "MH Screen - DDS or PHQ", "Patient goals", "Education", "BP"],
            default=["Annual Review Done"],
        )
    with c2:
        st.write()
    # Call the filter_due_patients function with the DataFrame and selected tests
    try:
        due_patients = filter_due_patients(df, selected_tests, online_mapping)

    except NameError as e:
        st.warning(f"Upload csv data to use this tool. Error: {e}")

    try:
        if not due_patients.empty:
            ui.badges(badge_list=[("Patient Count: ", "outline"), (due_patients.shape[0], "default")], class_name="flex gap-2", key="badges1")
            plot_histograms(due_patients, plot_columns)
            import streamlit_shadcn_ui as ui

            ui.badges(badge_list=[("Patient Count: ", "outline"), (due_patients.shape[0], "default")], class_name="flex gap-2", key="badges1")

            st.dataframe(due_patients, height=300)
            download_sms_csv(due_patients, sms_df, actioned_df, filename="online_preassessment_sms.csv")

        else:
            st.warning(
                "Please upload the necessary CSV file to display the dataframe. Select at least one criterion to filter by."
            )
    except NameError as e:
        st.warning(f"Upload csv data to use this tool. Error: {e}")







elif tab_selector == "HCA Self-book":

    if "sms_df" not in globals() or "df" not in globals():
        st.warning("Please upload both CSV files to proceed.")

    c1, c2 = st.columns(2)
    with c1:
        selected_tests = st.multiselect(
            "Select **Tests** to include:",
            options=["HbA1c", "Lipids", "eGFR", "Urine ACR", "Foot Check"],
            default=["HbA1c"],
        )
    with c2:
        st.write()
    # Call the filter_due_patients function with the DataFrame and selected tests
    try:
        due_patients = filter_due_patients(df, selected_tests, test_mapping)
    except NameError as e:
        st.warning(f"Upload csv data to use this tool. Error: {e}")

    try:
        if not due_patients.empty:
            ui.badges(badge_list=[("Patient Count: ", "outline"), (due_patients.shape[0], "default")], class_name="flex gap-2", key="badges2")
            plot_histograms(due_patients, plot_columns)


            st.dataframe(due_patients, height=300)
            download_sms_csv(due_patients, sms_df, actioned_df, filename="hca_selfbook_sms.csv")


        else:
            st.warning(
                "Please upload the necessary CSV file to display the dataframe. Select at least one criterion to filter by."
            )
    except NameError as e:
        st.warning(f"Upload csv data to use this tool. Error: {e}")

elif tab_selector == "Filter Dataframe":

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
        st.sidebar.divider()
        # Create sliders for each metric and store the selected range
        for key, (label, min_val, max_val) in metrics.items():
            filter_values[key] = st.sidebar.slider(
                f"Select **{label}** range",
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
        ui.badges(badge_list=[("Patient Count: ", "outline"), (filtered_df.shape[0], "default")], class_name="flex gap-2", key="badges3")
        # Display the filtered DataFram
        plot_histograms(filtered_df, plot_columns)

        st.dataframe(filtered_df, height=300)  # Only shows rows within the slider-selected range
        download_sms_csv(filtered_df, sms_df, actioned_df, filename="filtered_data_sms.csv")






elif tab_selector == "Rewind":

    st.write("Patients eligible for referral to **Rewind**.")
    if "sms_df" not in globals() or "df" not in globals():
        st.warning("Please upload both CSV files to proceed.")
    else:
        rewind_df = df[
            (df["Eligible for REWIND"] == "Yes") & (df["REWIND - Started"] == 0)
        ]
        ui.badges(badge_list=[("Patient Count: ", "outline"), (rewind_df.shape[0], "default")], class_name="flex gap-2", key="badges4")
        st.dataframe(rewind_df)
        download_sms_csv(rewind_df, sms_df, actioned_df, filename="dm_rewind_sms.csv")






elif tab_selector == "Guidelines":

    st.write("""In the management of diabetes, the frequency of monitoring various metrics can change based on the patient’s condition and previous results. According to NICE (National Institute for Health and Care Excellence) guidelines, here are recommended timeframes for common diabetic metrics, with adjustments based on results:

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

    st.image("images/table.png")


elif tab_selector == "Quick Start":


    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""### Diabetes Recall
On the right the proposed workflow for Diabetes Recalls, to use with this tool.

Online Pre-assessment Questionnaire can by collected via a Tally forms which has advanced logic speeding up online completion. Note the Tally URL is blocked by NHS, so set the form up on your home or phone internet connection.

A wide range of integration with Tally is possible, Google Sheets and Notion are good options to collect and manage returns.
Use the Pre-assessment on this tool to target the appropriate cohort of patients for invitation to use the online pre-assessment. Once data entry has been completed Patients can be referrecd for Phlebotomy and foot checks with you HCA, follow-up with a clinical phamacist or clinician once results are avaialable.
### Using the Recall Tool:
1. Prepare your **Diabetes Register SMS csv**, as you would do for **Accurx** invites. Columns: `NHS number, Preferred Telephone number, Date of birth, First name, Email`
2. Save your latest **Diabtes Dashboard** from Paul, as a CSV file.
3. Upload both to this tool.
4. Use the navigation at the top to optimize your groups for recall.
5. Once you are happy with your patient cohort, download a custom CSV using the **Download Button** on each page. This will have the exact list of patient you have selected using the tool.""")
        st.write("**Tally form preview:**")
        with st.container(height=450, border=True):
            st.image('images/tallyform.png')
        ui.link_button(text="Download Pre-assessment Form Template", url="https://tally.so/templates/diabetes-pre-assessment-questionnaire/mYQ4zm", key="link_btn")
    with c2:
        st.container(height=45, border=False)
        st.image('images/flowchart.png')

    st.write("If you find this tool useful, please follow the link to GitHub and :material/star: this project.")
    st.write("For assistance with using this tool or setting up a Tally integration please contact me via a GitHub issue.")
    st.write("**Thank you**!")
    st.html("<a href='https://github.com/janduplessis883/diabetes-streamlit'><img alt='Static Badge' src='https://img.shields.io/badge/GitHub-jandupplessis883-%23f09235?logo=github'></a>")


elif tab_selector == "Predicted Hba1c - Regression":


    st.write("**Prediction DF** here")
    st.dataframe(prediction)

    st.write("This app will soon include a feature to predict patients’ next **HbA1c levels** based on their medical history. A regression model is being trained on data from the **Brompton Health PCN** to support this functionality.")
    st.markdown("""
                Predicting HbA1c levels using machine learning has been the focus of several studies. Here are some notable papers:
1. “**Machine Learning to Identify Predictors of Glycemic Control in Type 2 Diabetes: An Analysis of Target HbA1c Reduction Using Empagliflozin/Linagliptin Data**”
This study employs machine learning to analyze clinical trial data, identifying patient characteristics associated with achieving and maintaining target HbA1c levels. (Springer Link)
2. “**Improving Current Glycated Hemoglobin Prediction in Adults: Use of Machine Learning Models**”
This research demonstrates that machine learning models can effectively predict current HbA1c levels (≥5.7% or less) by utilizing patients’ longitudinal data, enhancing the performance and importance of various predictors. (JMIR Medical Informatics)
3. “**Machine Learning and Deep Learning Predictive Models for Type 2 Diabetes: A Systematic Review**”
This systematic review compares various machine learning and deep learning models for predicting type 2 diabetes, highlighting the effectiveness of tree-based algorithms and the challenges in model interpretability. (DMS Journal)
4. “**Machine Learning Approaches to Predict Risks of Diabetic Complications and Poor Glycemic Control in Nonadherent Type 2 Diabetes**”
This paper explores machine learning techniques to predict the risks of diabetic complications and poor glycemic control, emphasizing the role of HbA1c as a critical predictor. (Frontiers)
5. “**Predictive Modelling of Glycated Hemoglobin Levels Using Machine Learning Regressors**”
This study develops a methodology for predicting HbA1c levels using various machine learning regression algorithms, demonstrating the potential for improved diabetes management. (Iieta)
""")
    st.image('images/r2.png')
    st.image('images/regression2.png')

    st.subheader("Systematic Review: HbA1c Prediction")
    with st.container(height=650, border=True):
        pdf_viewer("hba1c-paper.pdf")





elif tab_selector == "Integrations":
    st.image("images/integrations.png")
    st.write(st.session_state)

    st.subheader("Actioned DF Loaded:")
    st.dataframe(actioned_df)
