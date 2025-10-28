import pandas as pd
import streamlit as st
from combined_script import run_extraction
from input_form import input_form_data
from style import style_excel

# --- 1. Page and State Initialization ---
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

# --- 3. Form Display and Submission Logic ---
# This section runs if the PDF has been successfully extracted
if st.session_state.extracted_df is not None:
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
            # Create the final combined DataFrame and store it in the session state
            st.session_state.final_df = pd.concat(
                [extracted_df.reset_index(drop=True), input_form_df.reset_index(drop=True)], axis=1
            )
            # No rerun needed here. The script will continue and render the final DF below.
    else:
        # If extraction missed the required columns, show an error
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

