import streamlit as st
from company_extractor import digit_data_extraction
from company_extractor import reliance_data_extraction
from company_extractor import tata_data_extraction
from policy_extraction_config import PolicyExtractorConfig


def extract_company_name_llm(text, llm):
    """
    Uses Gemini LLM to extract just the company name from an input text.
    Returns the best company name string or an empty string if not found.
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

    response = llm.invoke(prompt)
    # Postprocess: Take first non-empty line as answer
    company_name = response.content.strip().splitlines()[0]
    return company_name


def main():
    uploaded_file = st.file_uploader("Upload Insurance Policy PDF.", type=["pdf"])
    extractor = PolicyExtractorConfig(uploaded_file)
    if uploaded_file:
        with st.spinner("Processing PDF and extracting data..."):
            text = extractor.extract_text_from_pdf()
            llm = extractor.initialize_llm()
            company = extract_company_name_llm(text, llm)

        if not company:
            st.error("Could not detect company (Reliance, Tata, Digit) in the PDF text.")
            st.stop()
        try:
            if 'reliance' in company.lower():
                reliance_data_extraction.main(uploaded_file)
            if 'digit' in company.lower():
                digit_data_extraction.main(uploaded_file)
            if 'tata' in company.lower():
                tata_data_extraction.main(uploaded_file)
        except Exception as e:
            st.error(f"Failed to import extraction for company {company}: {e}")
            st.stop()


if __name__ == "__main__":
    main()
