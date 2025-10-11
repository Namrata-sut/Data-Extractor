from datetime import datetime
import pandas as pd
import streamlit as st
from app.policy_extraction_config import PolicyExtractorConfig

# Columns for final Excel
COLUMNS = [
    "Company Name",
    "Policy Number", "Insured Name", "Start Date", "Expiry Date", "Registration No.",
    "Make & Model", "Product Type", "Policy type", "Seating Capacity", "GVW", "CC",
    "Engine No.", "Chassis No.", "Mfg.Year", "Total IDV", "NCB Claimed", "Total OD PREMIUM",
    "Total Net PREMIUM", "Total Final Premium", "Source File"
]


def extract_with_ai(text, llm, source_file):
    """Send PDF text to Gemini LLM and extract structured info."""
    prompt = f"""
    Extract the following fields from this insurance policy text and return ONLY valid JSON:
    {COLUMNS}

    Formatting and extraction rules:
    - "Start Date" and "Expiry Date" must be formatted strictly as MM/DD/YYYY.
    - For "Policy Type", find the label "Type of Cover" or "**** Policy" (case-insensitive) and extract the value that immediately follows it. This value may be on the same line or on the line directly below. For example, if the text says "Type of Cover: Package", the value should be "Package".
    - For "NCB Claimed", first attempt to extract the numeric value that is followed by a '%' symbol. For example, if the text says "NCB: 25 %", the value should be "25%".
    - If any field is missing, return its value as an empty string.
    - Do not include any additional keys or explanations — return pure JSON.

    Policy text:
    {text}
    """
    extractor = PolicyExtractorConfig(source_file)
    response = llm.invoke(prompt)
    raw_output = response.content.strip()
    parsed = extractor.clean_json_output(raw_output)

    # Fill default structure
    data = {col: "" for col in COLUMNS}
    for col in COLUMNS:
        if col in parsed and parsed[col] is not None:
            data[col] = parsed[col]

    # Add system-generated values
    now = datetime.now()
    entry_date = now.strftime("%d-%b-%Y")
    entry_time = now.strftime("%H:%M:%S")
    data["Entry Date"] = entry_date
    data["Entry Time"] = entry_time
    data["Source File"] = source_file.name

    return data


def main(uploaded_file):
    st.title("Tata Insurance Policy Extractor")
    if uploaded_file:
        extractor = PolicyExtractorConfig(uploaded_file)
        llm = extractor.initialize_llm()
        all_records = []
        with st.spinner("Extracting data..."):
            text = extractor.extract_text_from_pdf()
            record = extract_with_ai(text, llm, uploaded_file)
            all_records.append(record)

        df = pd.DataFrame(all_records)
        st.success("Extraction complete!")
        st.dataframe(df)

        # Download Excel
        excel_file = "insurance_extract.xlsx"
        df.to_excel(excel_file, index=False)
        with open(excel_file, "rb") as f:
            st.download_button(
                label="Download Excel",
                data=f,
                file_name="insurance_extract.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


# if __name__ == "__main__":
#     input_file = st.file_uploader("Upload Insurance Policy PDF.", type=["pdf"])
#     main(input_file)
