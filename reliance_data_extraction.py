import pandas as pd
import pdfplumber
import os
import json
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Columns for final Excel
COLUMNS_NEW = [
    "Submitted By", "Entry Date", "Entry Time", "Partner Name", "Company Name",
    "Policy Number", "Insured Name", "Start Date", "Expiry Date", "Registration No.",
    "Make & Model", "Product Type", "Policy Type", "Seating Capacity", "GVW", "CC",
    "Engine No.", "Chassis No.", "Mfg.Year", "Total IDV", "NCB", "OD PREMIUM",
    "Net PREMIUM", "Final Premium", "Mode of Payment", "Bank Name", "Cheque No.",
    "Cheque/Receive Date", "Amount Received", "Base For Commission", "Commissiable Premium",
    "Agent Name", "Agent %", "Agent Comm. Amt", "Short fall", "Net Payable", "Remarks",
    "Our Com %", "Our Com Amt", "% Received", "Com Received", "Com Month", "Ad. Com %",
    "AD.Com Amt", "Recovery Amt", "Gross Profit", "Notes", "Source File"
]

# Columns for final Excel
COLUMNS = [
    "Company Name",
    "Policy Number", "Insured Name", "Start Date", "Expiry Date", "Registration No.",
    "Make & Model", "Product Type", "Policy type", "Seating Capacity", "GVW", "CC",
    "Engine No.", "Chassis No.", "Mfg.Year", "Total IDV", "NCB Claimed", "Total OD Premium",
    "Total Net Premium", "Total Final Premium", "Source File"
]

def initialize_llm():
    """Initializes Gemini LLM."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        st.error("Google API key not set. Please set GOOGLE_API_KEY.")
        st.stop()
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", temperature=0,top_p=1.0, google_api_key=api_key
    )

def extract_text_from_pdf(pdf_file):
    """Extracts text from PDF bytes."""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def clean_json_output(raw_output: str):
    """Cleans Gemini's raw output and converts it to JSON dict."""
    try:
        # Remove markdown fences if present
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`")
            raw_output = raw_output.split("json\n")[-1]
            raw_output = raw_output.split("```")[0]
        return json.loads(raw_output)
    except Exception as e:
        st.error(f" JSON parsing failed: {e}")
        return {}

def extract_with_ai(text, source_file):
    """Send PDF text to Gemini LLM and extract structured info."""
    llm = initialize_llm()
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

    response = llm.invoke(prompt)
    raw_output = response.content.strip()
    parsed = clean_json_output(raw_output)

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
    data["Source File"] = source_file

    return data


def main():
    st.title("Insurance Policy Extractor")
    uploaded_files = st.file_uploader(
        "Upload Insurance Policy PDF(s)", type=["pdf"], accept_multiple_files=True
    )

    if uploaded_files:
        all_records = []
        with st.spinner("Extracting data..."):
            for uploaded_file in uploaded_files:
                text = extract_text_from_pdf(uploaded_file)
                record = extract_with_ai(text, uploaded_file.name)
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

if __name__ == "__main__":
    main()
