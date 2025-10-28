import streamlit as st
from company_extractor import digit_data_extraction, reliance_data_extraction, tata_data_extraction
from policy_extraction_config import PolicyExtractorConfig


def extract_company_name_llm(text, llm):
    """
    Uses a Language Model to extract the insurance company name from text.
    Args:
        text (str): The text extracted from the PDF.
        llm: An initialized LLM client.

    Returns:
        str: The extracted company name, or an empty string if not found.
    """
    prompt = f"""
    Extract ONLY the exact name of the insurance company from the following text and
    return just the company name string. 
    Do NOT return any other words, JSON, headers, or explanations. If not found, return an empty string.

    Examples:
    Text: "Issued by Go Digit General Insurance Ltd."
    Output: Go Digit General Insurance Ltd.

    Text: "Company Name: Reliance General Insurance Company Limited"
    Output: Reliance General Insurance Company Limited

    Text: "This is a policy issued by TATA AIG General Insurance Company Limited"
    Output: TATA AIG General Insurance Company Limited

    Text: {text}
    Output:
    """.strip()

    try:
        response = llm.invoke(prompt)
        if response.content:
            company_name = response.content.strip().splitlines()[0]
            return company_name
        return ""
    except Exception as e:
        st.error(f"Error during LLM call: {e}")
        return ""


def run_extraction(uploaded_file):
    """
    Orchestrates the PDF data extraction process.

    This function is called by the main Streamlit app and is responsible for:
    1. Initializing configurations.
    2. Extracting text from the PDF.
    3. Identifying the insurance company using an LLM.
    4. Delegating to the correct company-specific extraction module.

    Args:
        uploaded_file: The file-like object from st.file_uploader.

    Returns:
        pd.DataFrame: A DataFrame containing the extracted data, or None if extraction fails.
    """
    if not uploaded_file:
        st.error("No file was provided for extraction.")
        return None

    # Initialize configurations and extract text
    extractor_config = PolicyExtractorConfig(uploaded_file)
    text = extractor_config.extract_text_from_pdf()
    llm = extractor_config.initialize_llm()

    # Identify the company from the extracted text
    company_name = extract_company_name_llm(text, llm)
    if not company_name:
        st.error("Could not determine the insurance company from the PDF.")
        return None

    st.info(f"Detected company: {company_name}")

    # Route to the appropriate company-specific extractor
    try:
        if 'reliance' in company_name.lower():
            df = reliance_data_extraction.main(text, uploaded_file)
        elif 'digit' in company_name.lower():
            df = digit_data_extraction.main(text, uploaded_file)
        elif 'tata' in company_name.lower():
            df = tata_data_extraction.main(text, uploaded_file)
        else:
            st.error(f"No specific extraction module found for '{company_name}'.")
            return None

        return df

    except Exception as e:
        st.error(f"An error occurred while extracting data for {company_name}: {e}")
        return None


