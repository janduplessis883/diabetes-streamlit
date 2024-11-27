import pickle
from joblib import load
import pandas as pd
from data_preprocessing.eda import update_column_names
from main import *
import streamlit as st


final = pd.DataFrame({"nhs_number": [], "latest_hba1c_value": [], "predicted_hba1c": [], "subtraction_result":[]})

def update_statin_strength(df):
    # Define the mapping dictionary
    statin_map = {
        'Pravastatin 10mg tablets': 1,
        'Pravastatin 20mg tablets': 2,
        'Pravastatin 40mg tablets': 3,
        'Simvastatin 20mg tablets': 4,
        'Simvastatin 40mg tablets': 5,
        'Simvastatin 80mg tablets': 6,
        'Atorvastatin 10mg tablets': 7,
        'Atorvastatin 20mg tablets': 8,
        'Atorvastatin 40mg tablets': 9,
        'Atorvastatin 80mg tablets': 10,
        'Rosuvastatin 5mg tablets': 11,
        'Rosuvastatin 10mg tablets': 12,
        'Rosuvastatin 20mg tablets': 13,
        'Rosuvastatin 40mg tablets': 14
    }

    # Update the 'statin' column using the map
    df['statin_strenght'] = df['statin'].map(statin_map)
    return df

def update_bame_column(df):
    # Define the mapping dictionary
    bame_map = {
        'No': 0,
        'Yes': 1,
        'NK': 0
    }

    # Update the 'bame' column using the map
    df['bame'] = df['bame'].map(bame_map)
    return df

def diabetes_diagnosis_map(df):
    dm_map = {
        "Type 1": 1,
        "Type 2": 2,
        "Both Types - Latest Type 1": 1,
        "Both Types - Latest Type 2": 2,
        "No Type Recorded": 0,
        "Both Types - Check": 2
        }
    df['diabetes_diagnosis'] = df['diabetes_diagnosis'].map(dm_map)
    return df

def predict(df, nhs_df):
    data = update_column_names(df)
    # data = load_df(data, col_list, columns_to_drop)
    print("🦖 Prep Dataframe")
    data = update_bame_column(data)
    print("😀 Bame Mapped")
    data = data.drop(columns=["dob", "ethnicity", "first_dm_diagnosis", "9_kcp_complete", "3_levels_to_target", "mh_screen_-_dds_or_phq", "patient_goals", "care_plan"])
    print("💧 Drop Columns")

    data = add_length_columns(data, cols_toget_length, calculate_length_of_diagnosis)
    print("🧮 Length of diagnosis columns")
    data = data.drop(columns=['annual_review_done',
    'hba1c', 'bp', 'cholesterol', 'bmi', 'egfr', 'urine_acr', 'smoking',
    'foot_risk', 'retinal_screening', 'education',
    'care_planning_consultation', 'struc_educ_in_l5y',
    'struc_educ_in_12m_diag', 'statin_date'])
    print("💧 Drop Columns")

    data = update_statin_strength(data)
    print("🗺️  Mapped Statiin Strength")
    data = diabetes_diagnosis_map(data)
    print("🗺️  Mapped Diabetes Diagnosis")

    data['latest_qrisk2'] = data['latest_qrisk2'].str.replace("%", "").astype(float)
    data = impute_values(data, missing_values=0, copy=False, strategy='mean', columns=impute_cols)
    data = data.fillna(0)  # STRATEGY FILL ALL NAA WITH ZERO
    data.drop(columns=["statin"], inplace=True)

    nhs_number = data[["nhs_number", "hba1c_value"]]

    data.drop(columns=["nhs_number", "column9"], inplace=True)

    new_col_list = ['imd_decile', 'bame', 'diabetes_diagnosis', 'column1',
        'sbp', 'dbp', 'total_chol', 'non-hdl_chol', 'latest_hdl', 'latest_ldl',
        'latest_egfr', 'latest_bmi', 'latest_qrisk2', 'column2', 'column3',
        'column4', 'column5', 'column6', 'column7', 'column8', 'column9',
        'metformin', 'sulphonylurea', 'dpp4', 'sglt2',
        'pioglitazone', 'glp-1', 'basal_/_mix_insulin', 'rapid_acting_insulin',
        'acei/arb', 'calcium_channel_blocker', 'diuretic', 'beta_blocker',
        'spironolactone', 'doxazosin', 'age', 'lenght_of_diagnosis_months',
        'lenght_of_diagnosis_years', 'annual_review_done_length',
        'hba1c_length', 'cholesterol_length', 'bmi_length', 'egfr_length',
        'urine_acr_length', 'smoking_length', 'foot_risk_length',
        'retinal_screening_length', 'education_length', 'statin_date_length',
        'statin_strenght']


    arranged_col_list = ['imd_decile', 'bame', 'diabetes_diagnosis', 'sbp', 'dbp', 'total_chol',
        'non-hdl_chol', 'latest_hdl', 'latest_ldl', 'latest_egfr', 'latest_bmi',
        'latest_qrisk2', 'column1', 'column2', 'column3', 'column4', 'column5',
        'column6', 'column7', 'column8', 'column9', 'metformin',
        'sulphonylurea', 'dpp4', 'sglt2', 'pioglitazone', 'glp-1',
        'basal_/_mix_insulin', 'rapid_acting_insulin', 'acei/arb',
        'calcium_channel_blocker', 'diuretic', 'beta_blocker', 'spironolactone',
        'doxazosin', 'age', 'lenght_of_diagnosis_months',
        'lenght_of_diagnosis_years', 'annual_review_done_length',
        'hba1c_length', 'cholesterol_length', 'bmi_length', 'egfr_length',
        'urine_acr_length', 'smoking_length', 'foot_risk_length',
        'retinal_screening_length', 'education_length', 'statin_date_length',
        'statin_strenght']

    data.columns = new_col_list

    data = data[arranged_col_list]

    drop_these = ['diabetes_diagnosis',
        'sulphonylurea', 'dpp4', 'sglt2', 'pioglitazone', 'glp-1',
        'basal_/_mix_insulin', 'rapid_acting_insulin', 'acei/arb',
        'calcium_channel_blocker', 'diuretic', 'beta_blocker', 'spironolactone',
        'doxazosin',  'lenght_of_diagnosis_months',
        'annual_review_done_length',
        'hba1c_length', 'cholesterol_length', 'bmi_length', 'egfr_length',
        'urine_acr_length', 'smoking_length', 'foot_risk_length',
        'retinal_screening_length', 'education_length', ]

    data.drop(columns=drop_these, inplace=True)
    with open('scaler_StandardScaler_2024-11-13_17-59-35.pkl', 'rb') as f:
        scaler = pickle.load(f)

    scaled_new_data = scaler.transform(data)

    # Load the model from the file
    gbr_loaded = load('gradient_boosting_model_13nov24.joblib')

    # Now you can use it to make predictions
    predictions = gbr_loaded.predict(scaled_new_data)

    nhs_list = nhs['nhs_number'].to_list()
    nhb_list = nhs['hba1c_value'].to_list()

    data = {
    "nhs_number": nhs_list,
    "latest_hba1c_value": hb_list,
    "predicted_hba1c": predictions,
    }
    final = pd.DataFrame(data)

    final['subtraction_result'] = final['latest_hba1c_value']  - final['predicted_hba1c']

    st.dataframe(final)

    return final









def highlight_subtraction_result(df):
    # Define the style function with multiple conditions
    def highlight(cell):
        # Apply different colors based on the cell's value
        if cell < -10:
            color = '#fb923c'  # Highlight in red if the value is greater than 10
        elif cell < -5:
            color = '#fcd34d'  # Highlight in yellow if the value is greater than 5
        else:
            color = ''
        return f'background-color: {color}'

    # Apply the style function to the 'subtraction_result' column
    styled_df = df.style.applymap(highlight, subset=['subtraction_result'])
    return styled_df

styled = highlight_subtraction_result(final)
st.dataframe(styled)
