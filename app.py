import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pycountry
from PIL import Image
import requests
from io import BytesIO

# Streamlit page setup
st.set_page_config(page_title="Product Origin Data Collection", page_icon="🌍", layout="wide")

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None
if "google_connected" not in st.session_state:
    st.session_state.google_connected = False

# Connect to Google Sheets
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

# Vendor Dashboard (tabular layout)
def vendor_dashboard(vendor_id):
    st.title(f"Mar-Co Clay Products, Inc. ({vendor_id})")
    st.markdown("Please complete the form and email the saved CSV file back to **tmunshi@siteone.com**.")
    st.markdown("---")

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

        vendor_id = vendor_id.strip().upper()
        df["PrimaryVendorNumber"] = df["PrimaryVendorNumber"].astype(str).str.strip().str.upper()
        vendor_df = df[df["PrimaryVendorNumber"] == vendor_id].copy()

        if vendor_df.empty:
            st.warning(f"No products found for Vendor ID '{vendor_id}'")
            return

        all_countries = sorted([f"{c.alpha_2} - {c.name}" for c in pycountry.countries])

        st.markdown("""
        **Instructions:**
        - Select a **Country of Origin** using the dropdown.
        - Enter the **HTS Code** as a 10-digit number (no periods).
        - If you only have 6 or 8 digits, add trailing 0s (e.g. `0601101500`).
        """)

        st.markdown("---")
        updated_rows = []

        # Header row
        cols = st.columns([1.2, 1.2, 1.5, 3, 2.5, 2])
        with cols[0]: st.markdown("**Image**")
        with cols[1]: st.markdown("**SKU**")
        with cols[2]: st.markdown("**Item #**")
        with cols[3]: st.markdown("**Product Name**")
        with cols[4]: st.markdown("**Country of Origin**")
        with cols[5]: st.markdown("**HTS Code**")

        for i, row in vendor_df.iterrows():
            cols = st.columns([1.2, 1.2, 1.5, 3, 2.5, 2])

            with cols[0]:
                image_url = row.get("ImageURL", "").strip()
                if image_url:
                    try:
                        response = requests.get(image_url, timeout=3)
                        if response.status_code == 200:
                            img = Image.open(BytesIO(response.content))
                            st.image(img, width=70)
                        else:
                            st.text("No Image")
                    except:
                        st.text("No Image")
                else:
                    st.text("No Image")

            with cols[1]: st.text(str(row.get("SKUID", "")))
            with cols[2]: st.text(str(row.get("SiteOneItemNumber", "")))
            with cols[3]: st.text(str(row.get("ProductName", "")))

            with cols[4]:
                default_country = str(row.get("CountryofOrigin", ""))
                country_selected = st.selectbox(
                    label="",
                    options=all_countries,
                    index=all_countries.index(default_country) if default_country in all_countries else 0,
                    key=f"country_{i}"
                )

            with cols[5]:
                default_hts = str(row.get("HTSCode", "")).zfill(10)
                hts_code = st.text_input(
                    label="",
                    value=default_hts if default_hts.isdigit() else "",
                    key=f"hts_{i}",
                    max_chars=10,
                    help="Enter 10-digit HTS Code with no periods. Use 0s if fewer digits."
                )

            updated_rows.append({
                **row,
                "CountryofOrigin": country_selected,
                "HTSCode": hts_code,
                "_row_index": i
            })

        if st.button("Submit"):
            worksheet_data = worksheet.get_all_values()
            headers = worksheet_data[0]

            for updated in updated_rows:
                row_index = updated["_row_index"] + 2  # gspread is 1-based, +1 for header
                new_country = updated["CountryofOrigin"]
                new_hts = updated["HTSCode"]

                if not new_hts.isdigit() or len(new_hts) != 10:
                    st.warning(f"⚠️ Invalid HTS Code for SKU {updated['SKUID']}: Must be 10 digits")
                    continue

                try:
                    country_col = headers.index("CountryofOrigin") + 1
                    hts_col = headers.index("HTSCode") + 1

                    worksheet.update_cell(row_index, country_col, new_country)
                    worksheet.update_cell(row_index, hts_col, new_hts)
                except Exception as e:
                    st.error(f"Error updating row for SKU {updated['SKUID']}: {e}")

            st.success("✅ All updates have been saved to the spreadsheet.")
            result_df = pd.DataFrame(updated_rows)[["SKUID", "ProductName", "CountryofOrigin", "HTSCode"]]
            st.dataframe(result_df)

    except Exception as e:
        st.error(f"Error during dashboard execution: {e}")

# Login Page
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

# App entry
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        vendor_dashboard(st.session_state.current_vendor)

if __name__ == "__main__":
    main()
