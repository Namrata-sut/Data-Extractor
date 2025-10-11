import streamlit as st
import combined_script


def main():
    st.title("Insurance Policy Extractor")
    try:
        combined_script.main()
    except Exception as e:
        st.error(f"Failed: {e}")
        st.stop()


if __name__ == "__main__":
    main()
