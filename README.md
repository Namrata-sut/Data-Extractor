# Insurance Policy Extractor (with Company-specific Modules)
This is a modular Streamlit application for extracting structured data from insurance policy PDF files.  
It auto-detects the company (Digit, Reliance, or TATA) using LLM (Gemini),
and applies the proper extraction logic for each insurer.  
Supports export of results to Excel and clean JSON display.

## Features
- Extracts policy data using *Google Gemini (Generative AI)*  
- Dynamically detects and runs company-specific logic  
- Exports results to Excel  
- Simple *Streamlit web UI* for upload & download  
- Modular architecture — add new company extractors easily  


## Project Structure
```
Data-Extractor/
│
├── app/
│   ├── main.py                      # App entry point
│   ├── combined_script.py           # Main unified extraction script
│   ├── policy_extraction_config.py  # Shared configs/classes
│   ├── __init__.py
│   └── company_extractor/
│       ├── __init__.py
│       ├── digit_data_extraction.py
│       ├── reliance_data_extraction.py
│       └── tata_data_extraction.py
├── TESTING/                         # Place your input PDF files for checking here
│   └── sample_files                 # Example folder for extra test PDFs
├── .env                             # Gemini API key configuration
├── README.md                        # This file
├── requirements.txt                 # Install dependencies
├── style.py                         # Apply formatting to the output excel file
├── data_with_new_form.py            # Takes the input data from user
├── .gitignore                       # Files ignored by git
└── venv/                            # Python virtual environment (recommended)
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/insurance-policy-extractor.git
cd insurance-policy-extractor
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Create a requirements.txt file with the following content:
```bash
pip install -r requirements.txt
```

### 4. Create a .env file in the project root and add your Google API key:
```ini
GOOGLE_API_KEY="your_google_api_key_here"
```

### 5. After setup, run the Streamlit app using:
```bash
cd app
streamlit run main.py
```

