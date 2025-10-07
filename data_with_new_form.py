# working with all column and excel design
# 3-10-25 (2:AM)

import re
import os
import pdfplumber
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
import uuid
from style import style_excel

# ---------------- Config ---------------- #
SAVE_FILE = "insurance_extract.xlsx"


# ---------------- Helpers ---------------- #
def clean_field(val: str) -> str:
    """Trim value and cut if 2+ spaces found."""
    if not val:
        return val
    return re.split(r"\s{2,}", val.strip())[0]


def get_text(pdf_file):
    """Extract full text from all pages"""
    with pdfplumber.open(pdf_file) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text


def get_page_text(pdf_file, page_num):
    """Extract text from a specific page"""
    with pdfplumber.open(pdf_file) as pdf:
        if page_num < len(pdf.pages):
            return pdf.pages[page_num].extract_text() or ""
    return ""


def first(patterns, text):
    """Return first regex group1 match from patterns"""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def parse_pdf(pdf_file):
    text = get_text(pdf_file)

    # ---- normalize odd whitespaces (NBSP, zero-width, etc.) just once ---- #
    def norm(s: str) -> str:
        if not s:
            return ""
        s = re.sub(r"[\u00A0\u2000-\u200B\u202F\u205F\u3000]", " ", s)  # non-breaking & thin spaces
        s = re.sub(r"[ \t]{2,}", " ", s)  # collapse multiple spaces
        return s

    text = norm(text)

    # ---------------- Policy number ---------------- #
    policy_number = first([r"Policy Number\s*[:\-]?\s*([0-9]{10,})"], text)

    # ---------------- Insured Name ---------------- #
    insured_name_raw = first([r"Insured Name\s*:\s*([^\n]+)"], text)
    insured_name = ""
    if insured_name_raw:
        matches = re.findall(r"(?:[A-Z0-9/&.,]+(?:\s|$))+", insured_name_raw)
        if matches:
            insured_name = matches[0].strip()
    if insured_name:
        insured_name = re.match(r"^[A-Z0-9/ &.,]+", insured_name).group(0).strip()

    # ---------------- Period of Insurance ---------------- #
    period_start, period_expiry = "", ""
    m = re.search(
        r"Period of Insurance\s*:\s*From\s.*?on\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4}).*?(?:to|upto).*?([0-9]{2}-[A-Za-z]{3}-[0-9]{4})",
        text, re.IGNORECASE
    )
    if m:
        period_start = m.group(1).strip()
        period_expiry = m.group(2).strip()
    else:
        m = re.search(
            r"Period of Insurance\s*:\s*From\s.*?on\s*([0-9]{2}-[A-Za-z]{3}-[0-9]{4})",
            text, re.IGNORECASE
        )
        if m:
            period_start = m.group(1).strip()
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if "Period of Insurance" in line:
                    if i + 1 < len(lines):
                        n = re.search(r"([0-9]{2}-[A-Za-z]{3}-[0-9]{4})", lines[i + 1])
                        if n:
                            period_expiry = n.group(1).strip()
                    break

    # ---------------- Registration No. (page 2 only) ---------------- #
    page2_text = norm(get_page_text(pdf_file, 1))
    registration_no = first([r"Registration No\.?\s*([A-Z0-9\-]+)"], page2_text)

    # ---------------- Make/Model & Variant ---------------- #
    make_model_variant_full = first([r"Make\s*/\s*Model\s*&?\s*Variant\s*([^\n]+)"], text)
    make_model_variant_full = norm(make_model_variant_full)
    make_model_variant = make_model_variant_full or ""
    if make_model_variant:
        make_model_variant = make_model_variant.strip()
        split_pat = r"(?:CC/HP|C\.?\s*C\.?|CC\b|BHP\b|HP\b|Date\s+of\s+Registration|Date\s+of\s+Reg(?:istration)?)"
        parts = re.split(split_pat, make_model_variant, flags=re.IGNORECASE)
        if parts:
            make_model_variant = parts[0].strip()

    # ---------------- Vehicle usage subtype ---------------- #
    vehicle_usage_subtype = first([r"Vehicle Usage Sub Type\s*([A-Za-z ]+)"], text)

    # ---------------- Engine + Chassis ---------------- #
    engine_chassis_raw = first([r"Engine No\.?.*?Chassis No\.?.*?([^\n]+)"], text)
    engine_no, chassis_no = "", ""
    if engine_chassis_raw:
        engine_chassis = re.split(r"\s{2,}|LCC", engine_chassis_raw)[0].strip()
        em = re.search(r"Engine\s*No\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)", engine_chassis, re.I)
        cm = re.search(r"Chassis\s*No\.?\s*[:\-]?\s*([A-Z0-9\-\/]*\d)\b", engine_chassis, re.I)
        if em:
            engine_no = em.group(1).strip()
        if cm:
            chassis_no = cm.group(1).strip()
        if (not engine_no or not chassis_no) and "/" in engine_chassis:
            parts = [p.strip() for p in engine_chassis.split("/") if p.strip()]
            if parts and not engine_no:
                engine_no = parts[0]
            if len(parts) > 1 and not chassis_no:
                m = re.search(r"([A-Z0-9\-\/]*\d)\b", parts[1])
                if m:
                    chassis_no = m.group(1).strip()
    if not chassis_no:
        chassis_no = first([r"Chassis No\.?\s*[:\-]?\s*([A-Z0-9\-\/]*\d)\b"], text)
    engine_chassis_combined = f"{engine_no} / {chassis_no}".strip(" /")

    # ---------------- Mfg month & year ---------------- #
    mfg_month_year = first([r"Mfg\.?\s*Month\s*&\s*Year\s*([A-Z]{3,9}-\d{4})"], text)

    # ---------------- Seating Capacity ---------------- #
    lcc_including_driver = first([
        r"LCC Including Driver\s*([0-9]+)",
        r"Seating Capacity Including Driver\s*([0-9]+)"
    ], text)

    # ---------------- CC / HP ---------------- #
    def extract_cc_hp(s: str) -> str:
        s = norm(s)
        label_cc = r"(?:C\.?\s*C\.?|CC|CUBIC\s*CAPACITY|ENGINE\s*CAPACITY)"
        label_hp = r"(?:H\.?\s*P\.?|HP|BHP|PS|K\.?\s*W\.?|KW)"
        patterns = [
            rf"\b(\d{{2,4}})\s*{label_cc}\b",
            rf"{label_cc}\s*[:\-]?\s*(\d{{2,4}})\b",
            rf"\b(\d{{1,3}})\s*{label_hp}\b",
            rf"{label_hp}\s*[:\-]?\s*(\d{{1,3}})\b",
            rf"\b(\d{{2,4}})[^\dA-Za-z]{{0,3}}{label_cc}",
            rf"{label_cc}[^\dA-Za-z]{{0,3}}(\d{{2,4}})",
            rf"\b(\d{{1,3}})[^\dA-Za-z]{{0,3}}{label_hp}",
            rf"{label_hp}[^\dA-Za-z]{{0,3}}(\d{{1,3}})",
        ]
        for pat in patterns:
            m = re.search(pat, s, flags=re.I)
            if m:
                return re.sub(r"\D", "", m.group(1))
        m = re.search(rf"{label_cc}[^\d]{{0,10}}(\d{{2,4}})", s, flags=re.I)
        if not m:
            m = re.search(rf"(\d{{2,4}})[^\d]{{0,10}}{label_cc}", s, flags=re.I)
        if m:
            return re.sub(r"\D", "", m.group(1))
        return ""

    cc_hp = extract_cc_hp(make_model_variant_full)
    if not cc_hp:
        cc_hp = extract_cc_hp(text)

    # ---------------- Total IDV ---------------- #
    total_idv = first([r"Total IDV\s*`?\s*([0-9,]+(?:\.\d{2})?)"], text).replace(",", "")

    # ---------------- NCB ---------------- #
    ncb = first([
        r"Deduct\s*([0-9]{1,2}\s*%)\s*for NCB",
        r"% of NCB.*?\b([0-9]{1,2}%)"
    ], text)
    if not ncb:
        ncb = "0%"

    # ---------------- GVW ---------------- #
    gvw = first([r"gvw\s*`?\s*([0-9,]+(?:\.\d{2})?)"], text).replace(",", "")
    if not vehicle_usage_subtype and not gvw:
        if re.search(r"\bPrivate\s*Car\b", page2_text, flags=re.IGNORECASE):
            vehicle_usage_subtype = "Private Car"
    if not gvw:
        gvw = "N/A"
    if not vehicle_usage_subtype and gvw:
        try:
            gvw_num = float(re.sub(r"[^\d.]", "", gvw))
            if gvw_num < 3500:
                vehicle_usage_subtype = "LCV"
            elif gvw_num >= 3500:
                vehicle_usage_subtype = "GCV"
        except ValueError:
            pass

    # ---------------- Total own damage premium ---------------- #
    total_own_damage_premium = first(
        [r"TOTAL OWN DAMAGE PREMIUM\s*([0-9,]+(?:\.\d{2})?)"], text
    ).replace(",", "")

    # ---------------- Total package premium ---------------- #
    total_package_premium = first(
        [r"TOTAL PACKAGE PREMIUM.*?\s*([0-9,]+(?:\.\d{2})?)"], text
    ).replace(",", "")

    # ---------------- Total premium ---------------- #
    total_premium = first([
        r"TOTAL PREMIUM PAYABLE.*?\s*([0-9,]+(?:\.\d{2})?)",
        r"Total Premium\s*`?\s*([0-9,]+)"
    ], text).replace(",", "")

    # ---------------- Company Name ---------------- #
    company_match = re.search(r"Reliance General Insurance Company Limited\.", text, re.IGNORECASE)
    company_name = company_match.group(0).strip() if company_match else ""

    # ---------------- Policy Type (page 2 search) ---------------- #
    policy_type = "N/A"
    if page2_text:
        if re.search(r"Package Policy", page2_text, re.IGNORECASE):
            policy_type = "Package"
        elif re.search(r"Liability Insurance", page2_text, re.IGNORECASE):
            policy_type = "Liability"
        elif re.search(r"Stand-alone Own Damage", page2_text, re.IGNORECASE):
            policy_type = "SAOD"

    # ---------------- Entry Date/Time ---------------- #
    now = datetime.now()
    entry_date = now.strftime("%d-%b-%Y")
    entry_time = now.strftime("%H:%M:%S")

    # ---------------- Build dict ---------------- #
    row = {
        "Entry Date": entry_date,
        "Entry Time": entry_time,
        "Company Name": company_name,
        "Policy Number": policy_number,
        "Insured Name": insured_name,
        "Start Date": period_start,
        "Expiry Date": period_expiry,
        "Registration No.": registration_no,
        "Make & Model": make_model_variant,
        "Product Type": vehicle_usage_subtype,
        "Policy Type": policy_type,
        "Seating Capacity": lcc_including_driver,
        "GVW": gvw,
        "CC": cc_hp,
        "Engine No.": engine_no,
        "Chassis No.": chassis_no,
        "Mfg.Year": mfg_month_year,
        "Total IDV": total_idv,
        "NCB": ncb,
        "OD PREMIUM": total_own_damage_premium,
        "Net PREMIUM": total_package_premium,
        "Final Premium": total_premium,
    }

    # Final cleaning for all fields
    return {k: clean_field(v) for k, v in row.items()}


# Streamlit app configuration
st.set_page_config(page_title="Insurance Policy Extractor", layout="wide")
st.title("📄 Insurance Policy PDF Extractor")

# Sample dropdown options (replace with actual data as needed)
partner_names = ["Partner A", "Partner B", "Partner C"]
agent_names = ["Agent X", "Agent Y", "Agent Z"]
submitted_by_options = ["User 1", "User 2", "User 3"]

# File uploader (restrict to one PDF)
uploaded_file = st.file_uploader(
    "Upload one Insurance PDF",
    type=["pdf"],
    accept_multiple_files=False
)

if uploaded_file:
    # Check for duplicate Policy Number, Registration No., or Source File before showing form
    duplicate_found = False
    if os.path.exists(SAVE_FILE):
        existing_df = pd.read_excel(SAVE_FILE)
        row = parse_pdf(uploaded_file)  # Parse PDF to get Policy Number and Registration No.
        row["Source File"] = uploaded_file.name
        if "Source File" in existing_df.columns and uploaded_file.name in existing_df["Source File"].values:
            st.error("This data has already been updated.")
            duplicate_found = True
        elif "Policy Number" in existing_df.columns and row["Policy Number"] in existing_df["Policy Number"].values:
            st.error("Policy Number already exists.")
            duplicate_found = True
        elif "Registration No." in existing_df.columns and row["Registration No."] and row["Registration No."] in \
                existing_df["Registration No."].values:
            st.error("Registration No. already exists.")
            duplicate_found = True

    # Show form only if no duplicates
    if not duplicate_found:
        # Initialize session state for form submission
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False
            st.session_state.form_data = {}

        # Form for additional fields
        st.subheader("Enter Additional Details")
        mode_of_payment = st.selectbox("Mode of Payment *", ["Online", "Cash", "Cheque"])

        with st.form(key="additional_details_form"):
            # Conditional fields for Cheque
            bank_name = "N/A"
            cheque_no = "N/A"
            if mode_of_payment == "Cheque":
                bank_name = st.text_input("Bank Name *")
                cheque_no = st.text_input("Cheque No. *")

            cheque_date = st.date_input("Cheque/Receive Date *")
            amount_received = st.number_input("Amount Received *", min_value=0.0, format="%.2f")
            remarks = st.text_area("Remarks *")
            partner_name = st.selectbox("Partner Name *", partner_names)
            agent_name = st.selectbox("Agent Name *", agent_names)
            submitted_by = st.selectbox("Submitted By *", submitted_by_options)
            base_for_commission = st.selectbox("Base For Commission *", ["OD", "NET"])
            agent_percentage = st.number_input("Agent % *", min_value=0.0, format="%.2f")

            submit_button = st.form_submit_button("Submit Details")

            if submit_button:
                # Check if all mandatory fields are filled
                if (mode_of_payment and
                        (mode_of_payment != "Cheque" or (
                                bank_name and bank_name != "N/A" and cheque_no and cheque_no != "N/A")) and
                        cheque_date and
                        amount_received is not None and
                        remarks and
                        partner_name and
                        agent_name and
                        submitted_by and
                        base_for_commission and
                        agent_percentage is not None):
                    st.session_state.form_data = {
                        "Mode of Payment": mode_of_payment,
                        "Bank Name": bank_name,
                        "Cheque No.": cheque_no,
                        "Cheque/Receive Date": cheque_date.strftime("%d-%b-%Y") if cheque_date else "",
                        "Amount Received": f"{amount_received:.2f}",
                        "Remarks": remarks,
                        "Partner Name": partner_name,
                        "Agent Name": agent_name,
                        "Submitted By": submitted_by,
                        "Base For Commission": base_for_commission,
                        "Agent %": f"{agent_percentage:.2f}%"
                    }
                    st.session_state.form_submitted = True
                    st.success("Form submitted successfully!")
                else:
                    st.error("Please fill all mandatory fields.")

        if st.session_state.form_submitted:
            # Load existing Excel if exists
            if os.path.exists(SAVE_FILE):
                existing_df = pd.read_excel(SAVE_FILE, engine="openpyxl")
            else:
                existing_df = pd.DataFrame()

            results = []
            row = parse_pdf(uploaded_file)
            row["Source File"] = uploaded_file.name
            # Add form data
            row.update(st.session_state.form_data)
            # Calculate Short fall
            try:
                net_premium = float(row["Net PREMIUM"]) if row["Net PREMIUM"] else 0.0
                amount_received = float(row["Amount Received"]) if row["Amount Received"] else 0.0
                row["Short fall"] = f"{net_premium - amount_received:.2f}"
            except ValueError:
                row["Short fall"] = "N/A"
            # Calculate Commissiable Premium
            row["Commissiable Premium"] = row["OD PREMIUM"] if row["Base For Commission"] == "OD" else row[
                "Net PREMIUM"]
            # Calculate Agent Comm. Amt
            try:
                commisiable_premium = float(row["Commissiable Premium"]) if row["Commissiable Premium"] else 0.0
                agent_percentage = float(row["Agent %"].strip("%")) / 100 if row["Agent %"] else 0.0
                row["Agent Comm. Amt"] = f"{commisiable_premium * agent_percentage:.2f}"
            except ValueError:
                row["Agent Comm. Amt"] = "N/A"
            # Calculate Net Payable
            try:
                agent_comm_amt = float(row["Agent Comm. Amt"]) if row["Agent Comm. Amt"] != "N/A" else 0.0
                short_fall = float(row["Short fall"]) if row["Short fall"] != "N/A" else 0.0
                row["Net Payable"] = f"{agent_comm_amt - short_fall:.2f}"
            except ValueError:
                row["Net Payable"] = "N/A"
            # Add new columns with default values
            row["Our Com %"] = "0"
            row["Our Com Amt"] = "0"
            row["% Received"] = "0"
            row["Com Received"] = "0"
            row["Com Month"] = "N/A"
            row["Ad. Com %"] = "0"
            row["AD.Com Amt"] = "0"
            row["Recovery Amt"] = "0"
            row["Gross Profit"] = "0"
            row["Notes"] = "N/A"

            results.append(row)
            new_df = pd.DataFrame(results)
            # Reorder columns to match the specified sequence
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
            new_df = new_df[columns]
            final_df = pd.concat(
                [existing_df[columns] if not existing_df.empty else pd.DataFrame(columns=columns), new_df],
                ignore_index=True)

            # Keep Policy Number as text
            if "Policy Number" in final_df.columns:
                final_df["Policy Number"] = final_df["Policy Number"].astype(str)

            # Save to Excel with styling
            style_excel(final_df, SAVE_FILE)

            # Display
            st.subheader("Extracted Data")
            st.dataframe(final_df)

            # Download option with styling
            excel_data = style_excel(final_df)

            st.download_button(
                label="📥 Download Extracted Data as Excel",
                data=excel_data,
                file_name="insurance_extract.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.success(f"✅ Data also auto-saved in working directory as {SAVE_FILE}")

            # Reset form after submission
            st.session_state.form_submitted = False
            st.session_state.form_data = {}

