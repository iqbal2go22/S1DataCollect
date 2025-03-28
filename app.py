import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pycountry
from PIL import Image
import requests
from io import BytesIO
import time

st.set_page_config(page_title="Product Origin Data Collection", page_icon="🌍", layout="wide")

# --- CSS Styling Fixes ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
        }
        div[data-testid="column"] > div {
            align-items: flex-start !important;
        }
        .stTextInput input {
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None
if "vendor_df" not in st.session_state:
    st.session_state.vendor_df = None
if "worksheet" not in st.session_state:
    st.session_state.worksheet = None
if "headers" not in st.session_state:
    st.session_state.headers = []
if "vendor_name" not in st.session_state:
    st.session_state.vendor_name = ""

def get_google_sheets_connection():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(credentials)

def vendor_dashboard(vendor_id):
    vendor_id = vendor_id.strip().upper()

    if st.session_state.vendor_df is None:
        client = get_google_sheets_connection()
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        worksheet = spreadsheet.worksheet("Sheet1")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        df["PrimaryVendorNumber"] = df["PrimaryVendorNumber"].astype(str).str.strip().str.upper()

        df = df[(df["PrimaryVendorNumber"] == vendor_id) & (
            (df["CountryofOrigin"].isna()) | (df["CountryofOrigin"] == '') |
            (df["HTSCode"].isna()) | (df["HTSCode"] == '')
        )].copy()

        if df.empty:
            st.success("✅ All items for this vendor have already been submitted.")
            return

        df = df.sort_values("Taxonomy").reset_index(drop=True)
        st.session_state.vendor_df = df
        st.session_state.worksheet = worksheet
        st.session_state.headers = worksheet.row_values(1)
        st.session_state.vendor_name = df.iloc[0].get("PrimaryVendorName", f"Vendor {vendor_id}")

    st.title(f"{st.session_state.vendor_name} ({vendor_id})")

    st.markdown("""
    **Instructions:**
    - Select a **Country of Origin** using the dropdown.
    - Enter the **HTS Code** as a 10-digit number (no periods).
    - If you only have 6 or 8 digits, add trailing 0s (e.g. `0601101500`).
    """)
    st.markdown("---")

    all_countries = sorted([f"{c.alpha_2} - {c.name}" for c in pycountry.countries])
    dropdown_options = ["Select..."] + all_countries

    # Table header
    cols = st.columns([0.8, 1.8, 0.9, 1, 2.5, 2.5, 3])
    for i, label in enumerate(["Image", "Taxonomy", "SKU", "Item #", "Product Name", "Country of Origin", "HTS Code + Submit"]):
        with cols[i]:
            st.markdown(f"**{label}**")

    updated_df = st.session_state.vendor_df.copy()

    for i, row in updated_df.iterrows():
        cols = st.columns([0.8, 1.8, 0.9, 1, 2.5, 2.5, 3])

        with cols[0]:
            img_url = row.get("ImageURL", "").strip()
            if img_url:
                try:
                    response = requests.get(img_url, timeout=3)
                    img = Image.open(BytesIO(response.content))
                    st.image(img, width=45)
                except:
                    st.markdown("No Image")
            else:
                st.markdown("No Image")

        with cols[1]: st.markdown(row.get("Taxonomy", ""))
        with cols[2]: st.markdown(str(row.get("SKUID", "")))
        with cols[3]: st.markdown(str(row.get("SiteOneItemNumber", "")))
        with cols[4]: st.markdown(str(row.get("ProductName", "")))

        with cols[5]:
            country = st.selectbox("", options=dropdown_options, index=0, key=f"country_{i}")

        with cols[6]:
            c1, c2 = st.columns([2.2, 1])
            with c1:
                hts_code = st.text_input("", value="", key=f"hts_{i}", max_chars=10, label_visibility="collapsed")
            with c2:
                submitted = st.button("Submit", key=f"submit_{i}")

        if submitted:
            if country == "Select..." or not hts_code.isdigit() or len(hts_code) != 10:
                st.warning(f"⚠️ Invalid input for SKU {row['SKUID']}")
                st.stop()

            try:
                row_index = i + 2
                country_col = st.session_state.headers.index("CountryofOrigin") + 1
                hts_col = st.session_state.headers.index("HTSCode") + 1
                st.session_state.worksheet.update_cell(row_index, country_col, country)
                st.session_state.worksheet.update_cell(row_index, hts_col, hts_code)
                st.success(f"✅ Submitted SKU {row['SKUID']}")
                st.session_state.vendor_df.drop(i, inplace=True)
                st.session_state.vendor_df.reset_index(drop=True, inplace=True)
                st.rerun()
            except Exception as e:
                st.error(f"Error updating Google Sheet: {e}")

    if len(st.session_state.vendor_df) > 0:
        if st.button("Submit All Remaining Items"):
            for i, row in st.session_state.vendor_df.iterrows():
                country = st.session_state.get(f"country_{i}", "Select...")
                hts = st.session_state.get(f"hts_{i}", "")
                if country == "Select..." or not hts.isdigit() or len(hts) != 10:
                    continue
                try:
                    row_index = i + 2
                    country_col = st.session_state.headers.index("CountryofOrigin") + 1
                    hts_col = st.session_state.headers.index("HTSCode") + 1
                    st.session_state.worksheet.update_cell(row_index, country_col, country)
                    st.session_state.worksheet.update_cell(row_index, hts_col, hts)
                except Exception as e:
                    st.error(f"Error saving SKU {row['SKUID']}: {e}")
            st.success("✅ All remaining items submitted successfully.")
            st.session_state.vendor_df = None
            st.rerun()

def login_page():
    st.title("🌍 Product Origin Data Collection")
    params = st.query_params
    if "vendor" in params:
        st.session_state.logged_in = True
        st.session_state.current_vendor = params["vendor"]
        st.rerun()
    vendor_id = st.text_input("Vendor ID")
    if st.button("Login as Vendor"):
        if vendor_id:
            st.session_state.logged_in = True
            st.session_state.current_vendor = vendor_id
            st.rerun()
        else:
            st.error("Please enter a Vendor ID")

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        vendor_dashboard(st.session_state.current_vendor)

if __name__ == "__main__":
    main()
