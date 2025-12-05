import pandas as pd
import streamlit as st
from datetime import datetime

# Streamlit app configuration
st.set_page_config(page_title="Insurance Policy Extractor", layout="wide")

EXPORT_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1rm66-CcEAJ_1Z28qXbBi5GJuyp0R-eSo/"
    "export?format=xlsx"
)

df = pd.read_excel(EXPORT_URL, engine="openpyxl")
partner_names = df["Partner name"].dropna().unique().tolist()
agent_names = df["Agent name"].dropna().unique().tolist()
submitted_by_options = df["Submitted by"].dropna().unique().tolist()


def input_form_data(od_premium, net_premium):
    st.subheader("Enter Additional Details")

    # Initialize session state
    if "form_submitted" not in st.session_state:
        st.session_state.form_submitted = False
        st.session_state.form_data = {}

    is_submitted = st.session_state.form_submitted
    form_values = st.session_state.form_data

    # Move Mode of Payment OUTSIDE the form
    mode_of_payment = st.selectbox(
        "Mode of Payment *", ["Online", "Cash", "Cheque"],
        index=["Online", "Cash", "Cheque"].index(form_values.get("Mode of Payment", "Online")),
        disabled=is_submitted
    )

    # The rest of the inputs inside the form
    with st.form(key="additional_details_form"):

        if mode_of_payment == "Cheque":
            bank_name = st.text_input("Bank Name *", value=form_values.get("Bank Name", ""), disabled=is_submitted)
            cheque_no = st.text_input("Cheque No. *", value=form_values.get("Cheque No.", ""), disabled=is_submitted)
            cheque_date = st.date_input("Cheque/Receive Date *", disabled=is_submitted)
        else:
            bank_name = form_values.get("Bank Name", "N/A")
            cheque_no = form_values.get("Cheque No.", "N/A")
            cheque_date = None

        amount_received = st.number_input("Amount Received", min_value=0, value=0)

        remarks = st.text_area("Remarks *", value=form_values.get("Remarks", ""), disabled=is_submitted)
        partner_name = st.selectbox("Partner Name *", partner_names,
                                    index=partner_names.index(form_values.get("Partner Name", partner_names[0])),
                                    disabled=is_submitted)
        agent_name = st.selectbox("Agent Name *", agent_names,
                                  index=agent_names.index(form_values.get("Agent Name", agent_names[0])),
                                  disabled=is_submitted)
        submitted_by = st.selectbox("Submitted By *", submitted_by_options,
                                    index=submitted_by_options.index(form_values.get("Submitted By", submitted_by_options[0])),
                                    disabled=is_submitted)
        base_for_commission = st.selectbox("Base For Commission *", ["OD", "NET"],
                                           index=["OD", "NET"].index(form_values.get("Base For Commission", "OD")),
                                           disabled=is_submitted)
        agent_percentage = st.number_input("Agent % *", min_value=0, value=0)

        # Submit button
        submit_button = st.form_submit_button("Submit Details", disabled=is_submitted)

        if submit_button and not is_submitted:
            # Validation for mandatory fields
            if (mode_of_payment and
                    (mode_of_payment != "Cheque" or (bank_name and cheque_no)) and
                    cheque_date and amount_received and remarks and partner_name and agent_name and
                    submitted_by and base_for_commission and agent_percentage is not None):

                # Save in session state
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
                    "Agent %": f"{agent_percentage:.2f}%",
                }
                st.session_state.form_submitted = True
                st.success("Form submitted successfully!")

                # --- Calculation Logic ---
                results = []
                row = {}
                now = datetime.now()
                row["Entry Date"] = now.strftime("%d-%b-%Y")
                row["Entry Time"] = now.strftime("%H:%M:%S")
                row["Amount Received"] = amount_received
                row["OD PREMIUM"] = od_premium
                row["Net PREMIUM"] = net_premium

                # Add form data
                row.update(st.session_state.form_data)

                # Short fall
                try:
                    net_val = float(row["Net PREMIUM"]) if row["Net PREMIUM"] else 0.0
                    amt_recv = float(row["Amount Received"]) if row["Amount Received"] else 0.0
                    row["Short fall"] = f"{net_val - amt_recv:.2f}"
                except ValueError:
                    row["Short fall"] = "N/A"

                # Commissiable Premium
                row["Commissiable Premium"] = row["OD PREMIUM"] if row["Base For Commission"] == "OD" else row["Net PREMIUM"]

                # Agent Comm. Amt
                try:
                    comm_prem = float(row["Commissiable Premium"]) if row["Commissiable Premium"] else 0.0
                    agent_pct = float(row["Agent %"].strip("%")) / 100 if row["Agent %"] else 0.0
                    row["Agent Comm. Amt"] = f"{comm_prem * agent_pct:.2f}"
                except ValueError:
                    row["Agent Comm. Amt"] = "N/A"

                # Net Payable
                try:
                    agent_comm_amt = float(row["Agent Comm. Amt"]) if row["Agent Comm. Amt"] != "N/A" else 0.0
                    short_fall = float(row["Short fall"]) if row["Short fall"] != "N/A" else 0.0
                    row["Net Payable"] = f"{agent_comm_amt - short_fall:.2f}"
                except ValueError:
                    row["Net Payable"] = "N/A"

                # Add additional columns
                row.update({
                    "Our Com %": "0", "Our Com Amt": "0", "% Received": "0",
                    "Com Received": "0", "Com Month": "N/A", "Ad. Com %": "0",
                    "AD.Com Amt": "0", "Recovery Amt": "0", "Gross Profit": "0", "Notes": "N/A"
                })

                results.append(row)
                new_df = pd.DataFrame(results)

                # Reorder columns
                columns = [
                    "Submitted By", "Partner Name", "Mode of Payment", "Bank Name", "Cheque No.", "Cheque/Receive Date",
                    "Amount Received", "Base For Commission", "Commissiable Premium", "Agent Name", "Agent %",
                    "Agent Comm. Amt", "Short fall", "Net Payable", "Remarks", "Our Com %", "Our Com Amt",
                    "% Received", "Com Received", "Com Month", "Ad. Com %", "AD.Com Amt", "Recovery Amt",
                    "Gross Profit", "Notes"
                ]

                final_df = new_df[columns]
                print(final_df)
                return final_df
            else:
                st.error("Please fill all mandatory fields.")

    # Display success message if already submitted
    if is_submitted:
        st.info("Form already submitted. Fields are disabled.")

    return None
