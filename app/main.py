import pandas as pd
import streamlit as st
import os  # Added for file system operations
from combined_script import run_extraction
from input_form import input_form_data
from style import style_excel

# --- 1. Page, State, and File Configuration ---
SAVE_FILE = "insurance_extract.xlsx"  # Define the name of the file to save data
st.set_page_config(page_title="Insurance Policy PDF Extractor", layout="wide")
st.title("Insurance Policy PDF Extractor")

# Initialize all required session state keys
if 'file_identifier' not in st.session_state:
    st.session_state.file_identifier = None
if 'extracted_df' not in st.session_state:
    st.session_state.extracted_df = None
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False
if 'final_df' not in st.session_state:
    st.session_state.final_df = None
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

# --- 2. File Uploader and Extraction Logic ---
uploaded_file = st.file_uploader("Upload Insurance Policy PDF", type=["pdf"])

if uploaded_file is not None:
    # If a new file is uploaded, reset the entire state
    if st.session_state.file_identifier != uploaded_file.file_id:
        st.session_state.file_identifier = uploaded_file.file_id
        st.session_state.extracted_df = None
        st.session_state.form_submitted = False
        st.session_state.final_df = None
        st.session_state.form_data = {}
        # Clear the display and rerun to start fresh with the new file
        st.rerun()

    # Run extraction only if it hasn't been done for the current file
    if st.session_state.extracted_df is None:
        with st.spinner("Processing PDF and extracting data..."):
            st.session_state.extracted_df = run_extraction(uploaded_file)
            # Rerun once to ensure the form appears immediately after extraction
            st.rerun()

# --- 3. Duplicate Check, Form Display, and Submission Logic ---
if st.session_state.extracted_df is not None:

    # --- NEW: DUPLICATE CHECK LOGIC ---
    # This check runs after extraction but before the form is displayed or submitted.
    if not st.session_state.form_submitted:
        is_duplicate = False
        error_message = ""
        df_to_check = st.session_state.extracted_df

        if os.path.exists(SAVE_FILE):
            try:
                saved_df = pd.read_excel(SAVE_FILE)
                # Check for duplicate Policy Number
                if 'Policy Number' in saved_df.columns and 'Policy Number' in df_to_check.columns:
                    policy_no = df_to_check['Policy Number'].iloc[0]
                    if policy_no and str(policy_no) in saved_df['Policy Number'].astype(str).values:
                        is_duplicate = True
                        error_message = f"Duplicate found: Policy Number '{policy_no}' already exists in the saved data."

                # Check for duplicate Registration No. only if not already a duplicate
                if not is_duplicate and 'Registration No.' in saved_df.columns and 'Registration No.' in df_to_check.columns:
                    reg_no = df_to_check['Registration No.'].iloc[0]
                    if reg_no and str(reg_no) in saved_df['Registration No.'].astype(str).values:
                        is_duplicate = True
                        error_message = f"Duplicate found: Registration No. '{reg_no}' already exists in the saved data."

            except Exception as e:
                st.warning(f"Could not read the saved Excel file for duplicate check: {e}")

        # If a duplicate is found, show the error and stop the script execution
        if is_duplicate:
            st.error(error_message)
            st.stop()

    # --- EXISTING FORM LOGIC (runs only if no duplicate was found) ---
    st.success("Extraction complete!")
    extracted_df = st.session_state.extracted_df

    # Check if the required premium columns exist
    required_cols = ['Total OD Premium', 'Total Premium']
    if all(col in extracted_df.columns for col in required_cols):
        total_od_premium = extracted_df['Total OD Premium'].iloc[0]
        total_premium_payable = extracted_df['Total Premium'].iloc[0]

        # Call the form function. It will display the form (enabled or disabled)
        # and will return a DataFrame ONLY on the script run where the user clicks "Submit"
        input_form_df = input_form_data(total_od_premium, total_premium_payable)

        # If the form returned a DataFrame, it means it was just submitted
        if input_form_df is not None:
            # Create the final combined DataFrame
            final_df = pd.concat(
                [extracted_df.reset_index(drop=True), input_form_df.reset_index(drop=True)], axis=1
            )
            # Add the source filename for traceability
            final_df['Source File'] = uploaded_file.name
            st.session_state.final_df = final_df

            # --- NEW: AUTO-SAVING LOGIC ---
            try:
                # Load existing data if the file exists
                if os.path.exists(SAVE_FILE):
                    existing_df = pd.read_excel(SAVE_FILE)
                    # Append the new data to the existing data
                    full_df = pd.concat([existing_df, st.session_state.final_df], ignore_index=True)
                else:
                    # If the file doesn't exist, this is the first entry
                    full_df = st.session_state.final_df

                # Save the updated data back to the Excel file
                full_df.to_excel(SAVE_FILE, index=False)
                st.success(f"Data successfully saved to '{SAVE_FILE}'")
            except Exception as e:
                st.error(f"Failed to save data to Excel file: {e}")

    else:
        missing_cols = [col for col in required_cols if col not in extracted_df.columns]
        st.error(f"Extraction failed to produce required columns: {missing_cols}")
        st.dataframe(extracted_df)

# --- 4. Final Preview and Download ---
# This block is now independent and will render if 'final_df' exists in the state
if st.session_state.final_df is not None:
    st.subheader("Final Data Preview")
    st.dataframe(st.session_state.final_df)

    # Prepare and display the download button
    styled_excel_data = style_excel(st.session_state.final_df)
    st.download_button(
        label="Download Excel",
        data=styled_excel_data,
        file_name="insurance_extract.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

