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

# Global styling
st.markdown("""
    <style>
        div[data-testid="column"] > div {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .block-container {
            padding-top: 1rem;
        }
        .stSelectbox label, .stTextInput label {
            display: none;
        }
        .stSelectbox div[data-baseweb="select"],
        .stTextInput input {
            margin: 0 auto;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None
if "google_connected" not in st.session_state:
    st.session_state.google_connected = False
if "vendor_df" not in st.session_state:
    st.session_state.vendor_df = None
if "vendor_name" not in st.session_state:
    st.session_state.vendor_name = ""

# Google Sheets connection
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
    vendor_id = vendor_id.strip().upper()

    # Only load data if it's not already loaded
    if st.session_state.vendor_df is None:
        with st.spinner("Loading products..."):
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
            df["PrimaryVendorNumber"] = df["PrimaryVendorNumber"].astype(str).str.strip().str.upper()
            vendor_df = df[df["PrimaryVendorNumber"] == vendor_id].copy()

            if vendor_df.empty:
                st.warning(f"No products found for Vendor ID '{vendor_id}'")
                return

            st.session_state.vendor_df = vendor_df.reset_index(drop=True)
            st.session_state.worksheet = worksheet
            st.session_state.headers = worksheet.row_values(1)
            st.session_state.vendor_name = vendor_df.iloc[0].get("PrimaryVendorName", f"Vendor {vendor_id}")
            time.sleep(1)

        st.success(f"✅ Loaded {len(st.session_state.vendor_df)} items successfully!")

    st.title(f"{st.session_state.vendor_name} ({vendor_id})")
    st.markdown("Please complete the form and email the saved CSV file back to **tmunshi@siteone.com**.")
    st.markdown("---")

    st.markdown("""
    **Instructions:**
    - Select a **Country of Origin** using the dropdown.
    - Enter the **HTS Code** as a 10-digit number (no periods).
    - If you only have 6 or 8 digits, add trailing 0s (e.g. `0601101500`).
    """)

    st.markdown("---")

    all_countries = sorted([f"{c.alpha_2} - {c.name}" for c in pycountry.countries])
    dropdown_options = ["Select..."] + all_countries

    # Header
    cols = st.columns([0.5, 1, 1, 2.5, 2.5, 2, 1])
    with cols[0]: st.markdown("**✓**")
    with cols[1]: st.markdown("**SKU**")
    with cols[2]: st.markdown("**Item #**")
    with cols[3]: st.markdown("**Product Name**")
    with cols[4]: st.markdown("**Country of Origin**")
    with cols[5]: st.markdown("**HTS Code**")
    with cols[6]: st.markdown("**Image**")

    # Render items
    updated_df = st.session_state.vendor_df.copy()
    rows_to_keep = []

    for i, row in updated_df.iterrows():
        cols = st.columns([0.5, 1, 1, 2.5, 2.5, 2, 1])

        with cols[0]:
            submit_box = st.checkbox("", key=f"submit_{i}")

        with cols[1]: st.markdown(str(row.get("SKUID", "")))
        with cols[2]: st.markdown(str(row.get("SiteOneItemNumber", "")))
        with cols[3]: st.markdown(str(row.get("ProductName", "")))

        with cols[4]:
            country = st.selectbox(
                label="",
                options=dropdown_options,
                index=0,
                key=f"country_{i}"
            )

        with cols[5]:
            hts = st.text_input(
                label="",
                value="",
                max_chars=10,
                key=f"hts_{i}",
                help="Enter 10-digit HTS Code"
            )

        with cols[6]:
            img_url = row.get("ImageURL", "").strip()
            if img_url:
                try:
                    response = requests.get(img_url, timeout=3)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        st.image(img, width=50)
                    else:
                        st.markdown("No Image")
                except:
                    st.markdown("No Image")
            else:
                st.markdown("No Image")

        if submit_box:
            if country == "Select...":
                st.warning(f"Please select country for SKU {row['SKUID']}")
                rows_to_keep.append(row)
                continue
            if not hts.isdigit() or len(hts) != 10:
                st.warning(f"HTS Code for SKU {row['SKUID']} must be exactly 10 digits")
                rows_to_keep.append(row)
                continue

            try:
                row_index = i + 2
                country_col = st.session_state.headers.index("CountryofOrigin") + 1
                hts_col = st.session_state.headers.index("HTSCode") + 1
                st.session_state.worksheet.update_cell(row_index, country_col, country)
                st.session_state.worksheet.update_cell(row_index, hts_col, hts)
                st.success(f"✅ Submitted SKU {row['SKUID']}")
            except Exception as e:
                st.error(f"Error saving SKU {row['SKUID']}: {e}")
                rows_to_keep.append(row)
        else:
            rows_to_keep.append(row)

    # Update session state with remaining rows
    st.session_state.vendor_df = pd.DataFrame(rows_to_keep).reset_index(drop=True)

# Login
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
