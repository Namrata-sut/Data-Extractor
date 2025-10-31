import pandas as pd
from datetime import datetime
import streamlit as st
from policy_extraction_config import PolicyExtractorConfig

# Columns for final Excel
COLUMNS = [
    "Company Name",
    "Policy Number", "Insured Name", "Start Date", "Expiry Date", "Registration No.",
    "Make & Model", "Product Type", "Policy type", "Seating Capacity", "GVW", "CC",
    "Engine No.", "Chassis No.", "Mfg.Year", "Total IDV", "NCB Claimed", "Total OD Premium",
    "Total Package Premium", "Total Premium", "Source File"
]


def extract_with_ai(llm, text, source_file):
    """Send PDF text to Gemini LLM and extract structured info."""
    extractor = PolicyExtractorConfig(source_file)
    # text = extractor.extract_text_from_pdf()
    prompt = f"""
    You are an insurance document data extraction assistant.
    Extract the following fields from this insurance policy text and return ONLY valid JSON:
    {COLUMNS}

    ### Extraction & Formatting Rules
    - "Company Name": Extract the insurance company name (e.g., "Reliance").
    - "Policy Number": Extract the complete policy number exactly as listed. If multiple numbers appear separated by '/', include the entire string (e.g., "D195110126/01/0001").
    - "Insured Name": Extract the name of the insured person or company.
    - "Start Date" and "Expiry Date" must be formatted strictly as MM/DD/YYYY.
    - "Registration No.": Extract the full vehicle registration number (e.g., "MH12AB1234").
    - "Make & Model": Extract both make and model, e.g., "Tata Motors Tiago".
    - "Product Type", extract the full descriptive name of the insured product, policy, or coverage type. Look for sections containing words like "Product", "Product Type", or any phrase ending with "Package Policy" or describing commercial vehicles. If the label is not present, use the most descriptive vehicle/product line matching commercial insurance context (such as "Commercial Vehicles (Passengers Carrying 4W>6 & 3W>17)" or "Reliance Commercial Vehicles (Passengers Carrying 4W>6 & 3W>17) Package Policy"). If multiple candidates are found, prefer the longest and most descriptive one containing category (Reliance, Commercial), vehicle type, and package/policy type. If no clear product type can be found, return an empty string.
    - "Policy Type", find the label "Type of Cover" or "**** Policy" (case-insensitive) and extract the value that immediately follows it. This value may be on the same line or on the line directly below. For example, if the text says "Type of Cover: Package", the value should be "Package".
    - "Seating Capacity": Extract the total seating capacity number (e.g., "7").
    - "GVW": Extract Gross Vehicle Weight (e.g., "7500 KG").
    - "CC": Extract engine cubic capacity (e.g., "1197 CC").
    - "Engine No.": Extract the engine number exactly as shown.
    - "Chassis No.": Extract the full chassis number exactly as shown.
    - "Mfg.Year": Extract the manufacturing year (e.g., "2021").
    - "Total IDV": Extract the Insured Declared Value in numeric form (e.g., "₹ 5,00,000" or "500000").
    - "NCB Claimed", first attempt to extract the numeric value that is followed by a '%' symbol. For example, if the text says "NCB: 25 %", the value should be "25%".
    - "Total OD Premium": Extract the total Own Damage premium value (e.g., "₹ 2,000").
    - "Total Package Premium": Extract the combined premium before tax (e.g., "₹ 3,500").
    - "Total Premium Payable": Extract the total payable premium including taxes (e.g., "₹ 4,130").
    - "Source File": Return the file name provided as input.

    If any field is missing, return its value as an empty string.
    
    Ensure:
        - Do not include any additional keys, text, or explanation.
        - The response must be **strictly valid JSON** (no comments, markdown, or text outside the JSON).
        - Be consistent with key names and casing exactly as shown above.
    Policy text:
    {text}
    """

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


def main(text, uploaded_file):
    extractor = PolicyExtractorConfig(uploaded_file)
    llm = extractor.initialize_llm()
    if uploaded_file:
        all_records = []
        with st.spinner("Extracting data reliance..."):
            record = extract_with_ai(llm, text, uploaded_file)
            all_records.append(record)

        df = pd.DataFrame(all_records)

        # Rename and rearrange columns as per final structure
        rename_map = {
            "Policy type": "Policy Type",
            "NCB Claimed": "NCB",
            "Total OD Premium": "OD PREMIUM",
            "Total Package Premium": "Net PREMIUM",
            "Total Premium": "Final Premium",
        }

        df.rename(columns=rename_map, inplace=True)

        final_columns = [
            "Entry Date", "Entry Time", "Company Name", "Policy Number", "Insured Name",
            "Start Date", "Expiry Date", "Registration No.", "Make & Model", "Product Type",
            "Policy Type", "Seating Capacity", "GVW", "CC", "Engine No.", "Chassis No.",
            "Mfg.Year", "Total IDV", "NCB", "OD PREMIUM", "Net PREMIUM", "Final Premium"
        ]

        df = df[final_columns]

        st.success("Extraction complete!")
        return df

# if __name__ == "__main__":
#     input_file = st.file_uploader("Upload pdf file to extract insurance data...", type=["pdf"])
#     main(input_file)

