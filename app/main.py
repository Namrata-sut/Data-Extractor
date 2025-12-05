import pandas as pd
import streamlit as st
import os
from combined_script import run_extraction
from input_form import input_form_data
from style import style_excel

# --- 1. Page, State, and File Configuration ---
SAVE_FILE = (
    "https://docs.google.com/spreadsheets/d/1GoTHOZINGQ4Lb3f0joO_i9AskAWfq51jxnqktHlpX_0/export?format=xlsx"
)

st.dataframe(pd.read_excel(SAVE_FILE, engine="openpyxl"))
st.set_page_config(page_title="Insurance Policy PDF Extractor", layout="wide")
st.title("Insurance Policy PDF Extractor")

# Initialize session state
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

# --- 2. File Uploader and Early Duplicate File Check ---
uploaded_file = st.file_uploader("Upload Insurance Policy PDF", type=["pdf"])

if uploaded_file is not None:
    file_name = uploaded_file.name
    file_already_exists = False

    # ✅ Step 1: Check if file name already exists before extraction
    if os.path.exists(SAVE_FILE):
        try:
            saved_df = pd.read_excel(SAVE_FILE, engine="openpyxl")
            if "Source File" in saved_df.columns and file_name in saved_df["Source File"].values:
                st.error(f"The file '{file_name}' has already been uploaded.")
                file_already_exists = True

                # --- Always show the entire saved data even if duplicate ---
                st.subheader("Existing Saved Data")
                try:
                    styled_excel_data = style_excel(saved_df)
                    st.dataframe(saved_df, use_container_width=True)

                    st.download_button(
                        label="Download Styled Excel",
                        data=styled_excel_data,
                        file_name="insurance_extract_styled.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Error displaying saved Excel data: {e}")
                # Stop further processing for this file
                st.stop()
        except Exception as e:
            st.warning(f"Could not read the saved Excel file: {e}")

    # ✅ Step 2: Only run extraction if file is new
    if not file_already_exists:
        # Reset the session when a new file is uploaded
        if st.session_state.file_identifier != uploaded_file.file_id:
            st.session_state.file_identifier = uploaded_file.file_id
            st.session_state.extracted_df = None
            st.session_state.form_submitted = False
            st.session_state.final_df = None
            st.session_state.form_data = {}
            st.rerun()

        # Run extraction only if not already done
        if st.session_state.extracted_df is None:
            with st.spinner("Processing PDF and extracting data..."):
                st.session_state.extracted_df = run_extraction(uploaded_file)
                st.rerun()

        # --- 3. Policy Number & Registration No. Duplicate Check ---
        if st.session_state.extracted_df is not None and not st.session_state.form_submitted:
            df_to_check = st.session_state.extracted_df
            is_duplicate = False
            error_message = ""

            if os.path.exists(SAVE_FILE):
                try:
                    saved_df = pd.read_excel(SAVE_FILE, engine="openpyxl")

                    # Check for duplicate Policy Number
                    if 'Policy Number' in saved_df.columns and 'Policy Number' in df_to_check.columns:
                        policy_no = df_to_check['Policy Number'].iloc[0]
                        if policy_no and str(policy_no) in saved_df['Policy Number'].astype(str).values:
                            is_duplicate = True
                            error_message = f"Duplicate found: Policy Number '{policy_no}' already exists."

                    # Check for duplicate Registration No. (only if Policy Number not duplicate)
                    if not is_duplicate and 'Registration No.' in saved_df.columns and 'Registration No.' in df_to_check.columns:
                        reg_no = df_to_check['Registration No.'].iloc[0]
                        if reg_no and str(reg_no) in saved_df['Registration No.'].astype(str).values:
                            is_duplicate = True
                            error_message = f"Duplicate found: Registration No. '{reg_no}' already exists."

                except Exception as e:
                    st.warning(f"Could not read the saved Excel file for duplicate check: {e}")

            # Stop execution if a duplicate is found
            if is_duplicate:
                st.error(error_message)
                st.stop()

        # --- 4. Continue if no duplicates ---
        st.success("Extraction complete!")
        extracted_df = st.session_state.extracted_df

        required_cols = ['OD PREMIUM', 'Final Premium']
        if all(col in extracted_df.columns for col in required_cols):
            total_od_premium = extracted_df['OD PREMIUM'].iloc[0]
            total_premium_payable = extracted_df['Final Premium'].iloc[0]

            input_form_df = input_form_data(total_od_premium, total_premium_payable)

            if input_form_df is not None:
                final_df = pd.concat(
                    [extracted_df.reset_index(drop=True), input_form_df.reset_index(drop=True)], axis=1
                )
                final_df['Source File'] = file_name
                st.session_state.final_df = final_df

                try:
                    if os.path.exists(SAVE_FILE):
                        existing_df = pd.read_excel(SAVE_FILE, engine="openpyxl")
                        full_df = pd.concat([existing_df, st.session_state.final_df], ignore_index=True)
                    else:
                        full_df = st.session_state.final_df

                    st.dataframe(full_df, use_container_width=True)
                    import gspread
                    import pandas as pd
                    from oauth2client.service_account import ServiceAccountCredentials

                    # Scopes
                    scope = [
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive"
                    ]

                    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
                    client = gspread.authorize(creds)

                    # Your Google Sheet URL
                    sheet_url = "https://docs.google.com/spreadsheets/d/1GoTHOZINGQ4Lb3f0joO_i9AskAWfq51jxnqktHlpX_0/edit?usp=drive_link"

                    sheet = client.open_by_url(sheet_url).sheet1

                    # Convert df to string to avoid Arrow errors
                    df_to_append = full_df.astype(str)

                    # Convert df to list of lists
                    rows = df_to_append.values.tolist()

                    # Append each row without clearing existing data
                    for row in rows:
                        sheet.append_row(row, value_input_option='USER_ENTERED')

                    st.success(f"Data successfully saved to '{SAVE_FILE}'")
                except Exception as e:
                    st.error(f"Failed to save data: {e}")
        else:
            missing_cols = [col for col in required_cols if col not in extracted_df.columns]
            st.error(f"Extraction failed to produce required columns: {missing_cols}")
            st.dataframe(extracted_df)

# --- 5. Final Data Preview & Download ---
if st.session_state.final_df is not None:
    # --- 6. Show Entire Saved Data with Styling ---
    if os.path.exists(SAVE_FILE):
        st.subheader("Final Data Preview")
        try:
            # Read the saved Excel file
            saved_data = pd.read_excel(SAVE_FILE, engine="openpyxl")
            # Specify desired column order (copy-pasted from your template)
            columns = [
                "Submitted By", "Entry Date", "Entry Time", "Partner Name", "Company Name",
                "Policy Number", "Insured Name", "Start Date", "Expiry Date", "Registration No.",
                "Make & Model", "Product Type", "Policy Type", "Seating Capacity", "GVW",
                "CC", "Engine No.", "Chassis No.", "Mfg.Year", "Total IDV",
                "NCB", "OD PREMIUM", "Net PREMIUM", "Final Premium", "Mode of Payment",
                "Bank Name", "Cheque No.", "Cheque/Receive Date", "Amount Received", "Base For Commission",
                "Commissiable Premium", "Agent Name", "Agent %", "Agent Comm. Amt", "Short fall",
                "Net Payable", "Remarks", "Our Com %", "Our Com Amt",
                "% Received", "Com Received", "Com Month", "Ad. Com %", "AD.Com Amt",
                "Recovery Amt", "Gross Profit", "Notes", "Source File"
            ]

            # Fill any missing columns with empty string
            for col in columns:
                if col not in saved_data.columns:
                    saved_data[col] = ""

            # Reorder
            saved_df = saved_data[columns]

            # Apply your custom Excel styling
            styled_excel_data = style_excel(saved_df)
            # Display the styled data preview
            st.dataframe(saved_df, use_container_width=True)
            # Download button for styled Excel
            st.download_button(
                label="Download Styled Excel",
                data=styled_excel_data,
                file_name="insurance_extract_styled.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error loading or styling saved Excel file: {e}")
    else:
        st.info("No saved data found yet.")


