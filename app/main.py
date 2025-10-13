import pandas as pd
import streamlit as st
import combined_script
# from style import style_excel
from input_form import input_form_data


def main():
    st.title("Insurance Policy PDF Extractor")
    try:
        extracted_df = combined_script.main()
        if extracted_df is not None and not extracted_df.empty:
            total_od_premium = extracted_df["Total OD Premium"]
            print(total_od_premium)
            total_premium_payable = extracted_df["Total Premium"]
            print(total_premium_payable)
            input_form_df = input_form_data(total_od_premium, total_premium_payable)
            final_df = pd.concat([extracted_df.reset_index(drop=True), input_form_df.reset_index(drop=True)], axis=1)
            excel_file = "insurance_extract.xlsx"
            final_df.to_excel(excel_file, index=False)
            # excel_data = style_excel(final_df)
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="Download Excel",
                    data=f,
                    file_name="insurance_extract.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            print("DataFrame is empty or None")
    except Exception as e:
        st.error(f"Failed: {e}")
        st.stop()


if __name__ == "__main__":
    main()
