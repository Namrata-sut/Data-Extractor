import json
import os

import pdfplumber
import streamlit as st

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


class PolicyExtractorConfig:
    def __init__(self, pdf_file):
        load_dotenv()
        # if os.path.exists(".env"):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        # else:
        #     self.api_key = st.secrets["api_keys"]["GOOGLE_API_KEY"]
        self.pdf_file = pdf_file

    def initialize_llm(self):
        """Initializes Gemini LLM."""
        if not self.api_key:
            st.error("Google API key not set. Please set GOOGLE_API_KEY.")
            st.stop()
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0, top_p=1.0, google_api_key=self.api_key
        )

    def extract_text_from_pdf(self):
        """Extracts raw text from uploaded PDF bytes."""
        text = ""
        with pdfplumber.open(self.pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def clean_json_output(self, raw_output: str):
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
