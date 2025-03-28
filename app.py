import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pycountry
import json

# Page config
st.set_page_config(page_title="Product Origin Data Collection", page_icon="🌍", layout="wide")

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Session state init
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None
if "google_connected" not in st.session_state:
    st.session_state.google_connected = False

# Google Sheets connect
def get_google_sheets_connection():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        st.session_state.google_connected = True
        return client
    except Exception as e:
        st.session_state.google_connected = False
        st.error(f"Google Sheets connection error: {e}")
        return None

# Vendor dashboard
def vendor_dashboard(vendor_id):
    st.title(f"Welcome, Vendor #{vendor_id}")
    st.subheader("Product Country of Origin and HTS Code Data Collection")

    try:
        client = get_google_sheets_connection()
        if not client:
            return

        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        worksheet = spreadsheet.worksheet("Sheet1")
        data = worksheet.get_all_records()
        if not data:
            st.warning("Sheet1 is empty.")
            return

        df = pd.DataFrame(data)

        # Normalize and filter
        vendor_id = vendor_id.strip().upper()
        df["PrimaryVendorNumber"] = df["PrimaryVendorNumber"].astype(str).str.strip().str.upper()
        vendor_df = df[df["PrimaryVendorNumber"] == vendor_id].copy()

        if vendor_df.empty:
            st.warning(f"No products found for Vendor ID '{vendor_id}'")
            return

        st.success(f"✅ Found {len(vendor_df)} products for Vendor ID '{vendor_id}'")

        # Country list
        all_countries = sorted([f"{c.name}" for c in pycountry.countries])

        st.markdown("""
        #### Instructions
        - **HTS Code** must be a 10-digit number with no periods.
        - If you only have 6 or 8 digits, add zeros to the end.
        - Example for tulip bulbs: `0601101500`
        """)

        updated_rows = []

        for i, row in vendor_df.iterrows():
            with st.expander(f"🔍 {row['ProductName']} (SKU: {row['SKUID']})"):
                st.write("**Item Details:**")
                st.write({k: row[k] for k in row.index if k not in ['CountryofOrigin', 'HTSCode']})

                country = st.selectbox(
                    "Country of Origin",
                    all_countries,
                    key=f"country_{i}",
                    index=all_countries.index(row.get("CountryofOrigin", "")) if row.get("CountryofOrigin", "") in all_countries else 0,
                )

                hts_input = st.text_input(
                    "HTS Code (10 digits, no periods)",
                    value=str(row.get("HTSCode", "")).zfill(10),
                    max_chars=10,
                    key=f"hts_{i}",
                    help="Enter 10 digits. Add trailing 0s if needed (e.g. 0601101500)"
                )

                updated_rows.append({
                    **row,
                    "CountryofOrigin": country,
                    "HTSCode": hts_input,
                    "_original_index": i  # keep index to update correct row in sheet
                })

        if st.button("Submit"):
            worksheet_data = worksheet.get_all_values()
            headers = worksheet_data[0]
            for updated in updated_rows:
                row_index = updated["_original_index"] + 2  # +2 because gspread is 1-based and row 1 is header
                new_country = updated["CountryofOrigin"]
                new_hts = updated["HTSCode"]

                if not new_hts.isdigit() or len(new_hts) != 10:
                    st.warning(f"⚠️ Invalid HTS Code for SKU {updated['SKUID']}: Must be 10 digits")
                    continue

                # Find correct column indices
                country_col = headers.index("CountryofOrigin") + 1
                hts_col = headers.index("HTSCode") + 1

                worksheet.update_cell(row_index, country_col, new_country)
                worksheet.update_cell(row_index, hts_col, new_hts)

            st.success("✅ Your updates have been saved to Google Sheets.")
            summary = pd.DataFrame(updated_rows)[["SKUID", "ProductName", "CountryofOrigin", "HTSCode"]]
            st.dataframe(summary)

    except Exception as e:
        st.error(f"Error during dashboard execution: {e}")

# Main login logic
def login_page():
    st.title("🌍 Product Origin Data Collection")

    params = st.query_params
    if "vendor" in params:
        vendor_id = params["vendor"]
        st.session_state.logged_in = True
        st.session_state.current_vendor = vendor_id
        st.rerun()

    vendor_id = st.text_input("Vendor ID")
    if st.button("Login as Vendor"):
        if vendor_id:
            st.session_state.logged_in = True
            st.session_state.current_vendor = vendor_id
            st.rerun()
        else:
            st.error("Please enter a Vendor ID")

# Main app
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        vendor_dashboard(st.session_state.current_vendor)

if __name__ == "__main__":
    main()
