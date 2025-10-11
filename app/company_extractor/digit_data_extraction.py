from datetime import datetime
import pandas as pd
import streamlit as st
from policy_extraction_config import PolicyExtractorConfig

# Columns for final Excel
COLUMNS = [
    "Company Name",
    "Policy Number", "Insured Name", "Start Date", "Expiry Date", "Registration No.",
    "Make & Model", "Product Type", "Policy type", "Seating Capacity", "GVW", "CC",
    "Engine No.", "Chassis No.", "Mfg.Year", "Total IDV", "NCB % (Current Policy)",
    "Total OD Premium", "Net Premium", "Total Premium", "Source File"
]


def extract_with_ai(llm, source_file):
    """Send PDF text to Gemini LLM and extract structured info."""

    extractor = PolicyExtractorConfig(source_file)
    text = extractor.extract_text_from_pdf()
    print("Text", text)

    prompt = f"""
    Extract the following fields from this insurance policy text and return ONLY valid JSON:
    {COLUMNS}
    Formatting and extraction rules:
    - "Company Name": Extract the exact name of the insurance company or issuing institution from anywhere in the document.
    - "Policy Number", extract the complete policy number(s) exactly as listed in the text. If multiple policy numbers appear together separated by '/', include the entire string with all numbers and separator(s). Do not split or remove any part. If multiple lines or variants are found, prefer the longest or most complete entry.
        Input: Policy Number D195110126 /01072025 Issue Date 01-Jul-2025
        → Output: D195110126 /01072025
        Input: Policy No.: 12345/67890/2025
        → Output: 12345/67890/2025
    - "Insured Name": Extract the full name of the insured entity or individual.
    - "Start Date" & "Expiry Date": Extract both dates and format strictly as MM/DD/YYYY. If listed in DD/MM/YYYY or another form, convert to MM/DD/YYYY.
    - "Registration No.": Extract the full vehicle registration number(s) as shown in the document. If the registration is indicated as "NEW," "TEMP," "NA," or a similar label (case-insensitive), return that exact value. Always extract the literal string provided, even if it isn't a standard number plate.
    - "Make & Model": 
        Extract and concatenate only the fields found under "Make," "Model," and "Variant"/"Sub-Type". 
        Strictly do not take values from "Policy Type", "Fuel Type", "Body Type", or unrelated columns.
        Join these using a single space, in left-to-right table order, removing field labels and extra spaces.
        When present, always join the value from the "Make" field with the entire value from the "Model/Vehicle Variant (Sub-Type)" or "Variant/Sub-Type" field, even if it includes descriptors like seating, "Bs-IV", or "CNG".
        Never include cells from "Policy Type", "Fuel Type" or "Body Type", even if they're on the same row.
        If the "Make" cell is empty, but the "Model" or "Variant" contains the full vehicle description (including brand), use that text as-is.
        If fields span multiple lines (e.g., "36 Seater / Bs-IV / Diesel"), join as a single string preserving slashes/parentheses.
        Example: If Make: SML ISUZU, Model/Vehicle Variant: S7 School Bus / 52 Seater/CNG → output "SML ISUZU S7 School Bus / 52 Seater/CNG".
    - "Product Type", extract the full descriptive name of the insured product, policy, or coverage type. Look for sections containing words like "Product", "Product Type", or any phrase ending with "Package Policy" or describing commercial vehicles. If the label is not present, use the most descriptive vehicle/product line matching commercial insurance context (such as "Commercial Vehicles (Passengers Carrying 4W>6 & 3W>17)" or "Reliance Commercial Vehicles (Passengers Carrying 4W>6 & 3W>17) Package Policy"). If multiple candidates are found, prefer the longest and most descriptive one containing category (Reliance, Commercial), vehicle type, and package/policy type. If no clear product type can be found, return an empty string.
    - "Policy Type":
        Find the label "Type of Cover" or "**** Policy" (case-insensitive) and extract the value that immediately follows it. This value may be on the same line or on the line directly below.
        If no such labeled field is present, then extract the most prominent document/product header or title containing the key word "Policy" (case-insensitive) found at or near the start or repeated throughout the document, as the policy type.
        For "Policy Number", extract the complete policy number(s) exactly as listed in the text. If multiple policy numbers appear together separated by '/', include the entire string with all numbers and separator(s). Do not split or remove any part. If multiple lines or variants are found, prefer the longest or most complete entry.
        For "Product Type", extract the full descriptive name of the insured product, policy, or coverage type. Look for sections containing words like "Product", "Product Type", or any phrase ending with "Package Policy" or describing commercial vehicles. If the label is not present, use the most descriptive vehicle/product line matching commercial insurance context (such as "Commercial Vehicles (Passengers Carrying 4W>6 & 3W>17)" or "Reliance Commercial Vehicles (Passengers Carrying 4W>6 & 3W>17) Package Policy"). If multiple candidates are found, prefer the longest and most descriptive one containing category (Reliance, Commercial), vehicle type, and package/policy type. If no clear product type can be found, return an empty string.
        "Seating Capacity": Find the number appearing directly underneath or directly to the right of "Seating Capacity" or "Licensed Capacity", whether separated by new lines, table rows, spaces, or columns. Use ONLY the value in the same column or location under that header. Do NOT pick up values from other fields or rows. Example:
            - Example2:
                Seating Capacity
                2
                should extract "2".
            or
            - Example2:
                Licensed Capacity
                2
                should return "2"
    - "GVW", extract the numeric part of the vehicle's Gross Vehicle Weight, removing any units such as "KG", "Kg", or similar. For example, if the text says "6250KG" or "1550 Kg", return "6250" or "1550" only.
    - "CC", extract the numeric value associated with "Cubic Capacity", "CC", or similar term for non-electric vehicles. If the vehicle is electric (look for "Electric", "Battery", or electric-specific models), extract the numeric value next to "Power", "Motor Power", or similar label. For all cases, return only the number, without units.
    - "Engine No.", look for fields or columns labeled "Engine", "Engine No.", or similar. When multiple numbers are combined under "Registration, Engine, Chassis No.", split these by spaces, slashes, line breaks, or table cells. Remove the registration number (which will usually match the "Registration No." field) and chassis number (often labeled or longer format), and extract the unique alphanumeric value remaining as the "Engine No.". If not found, return an empty string.
    - "Chassis No.": As above, find the value labeled "Chassis No." or, when grouped, extract the most likely chassis number (usually the third in a grouped field). Match typical chassis number patterns (often alphanumeric, longer string).
    - "Mfg.Year": Extract the four-digit manufacturing year, even when given as part of "Year" or "Manufacturing Year and Month".
    - "Total IDV": Extract the "Insured Declared Value" numeric value, removing any currency symbols. If multiple IDV values, use the one marked "Total IDV" or listed with the policy.
    - "NCB Claimed", first attempt to extract the numeric value that is followed by a '%' symbol. For example, if the text says "NCB: 25 %", the value should be "25%".
    - "Total OD Premium": Extract the number labeled "Own Damage Premium", "OD Premium", or similar description. Remove currency symbols.
    - "Net Premium": Extract the value labeled "Net Premium" (the premium payable after discounts, before tax). Remove currency symbols.
    - "Total Premium": Extract the total premium due payable (after tax and all charges), labeled as "Total Premium", "Total Premium Payable" or similar. Remove currency symbols.
    - "Source File": Set as the filename or reference provided, or leave empty if not present.

    General Rules:
    - If any field is missing or not found, return its value as an empty string.
    - Output must be valid JSON containing only the specified keys above.
    - Do not include any extra data, headers, or notes—output the JSON only.

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


def main(uploaded_file):
    st.subheader("Digit Insurance Policy Extraction")
    extractor = PolicyExtractorConfig(uploaded_file)
    llm = extractor.initialize_llm()
    if uploaded_file:
        all_records = []
        with st.spinner("Extracting data..."):
            record = extract_with_ai(llm, uploaded_file)
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
