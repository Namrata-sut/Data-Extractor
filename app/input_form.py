import pandas as pd
import streamlit as st
from datetime import datetime


# Streamlit app configuration
st.set_page_config(page_title="Insurance Policy Extractor", layout="wide")

# Sample dropdown options (replace with actual data as needed)
partner_names = ["Partner A", "Partner B", "Partner C"]
agent_names = ["Agent X", "Agent Y", "Agent Z"]
submitted_by_options = ["User 1", "User 2", "User 3"]


def input_form_data(od_premium, net_premium):
    # Initialize session state for form submission
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
        st.session_state.form_data = {}

    # Check if form has already been submitted
    if st.session_state.form_submitted:
        st.info("Form has already been submitted.")
    else:
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
                "Submitted By", "Partner Name", "Mode of Payment",
                "Bank Name", "Cheque No.", "Cheque/Receive Date", "Amount Received", "Base For Commission",
                "Commissiable Premium", "Agent Name", "Agent %", "Agent Comm. Amt", "Short fall",
                "Net Payable", "Remarks", "Our Com %", "Our Com Amt",
                "% Received", "Com Received", "Com Month", "Ad. Com %", "AD.Com Amt",
                "Recovery Amt", "Gross Profit", "Notes",
            ]
            # Reorder columns
            new_df = new_df[columns]

            # final_df is just new_df (no merging with existing_df)
            final_df = new_df.copy()

            print(final_df)
            return final_df


# input_form_data()
