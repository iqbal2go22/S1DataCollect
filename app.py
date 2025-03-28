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

# --- Custom CSS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
        }
        div[data-testid="column"] {
            padding-top: 0.5rem !important;
        }
        div[data-testid="column"] > div {
            align-items: flex-start !important;
        }
        .stTextInput input {
            text-align: center;
        }
        .dropdown-align .stSelectbox {
            margin-top: 0 !important;
        }
        .hts-inline {
            display: flex;
            align-items: center;
            gap: 6px;
        }
    </style>
""", unsafe_allow_html=True)

# --- Google API Scopes ---
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# --- Session State ---
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

# --- Connect to Google Sheets ---
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

# --- Vendor Form ---
def vendor_dashboard(vendor_id):
    vendor_id = vendor_id.strip().upper()

    if st.session_state.vendor_df is None:
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

        vendor_df = vendor_df.sort_values("Taxonomy").reset_index(drop=True)

        # Show progress bar
        with st.container():
            msg_container = st.empty()
            progress_bar = st.progress(0, text="Loading items...")
            for i in range(len(vendor_df)):
                time.sleep(0.01)
                progress_bar.progress((i + 1) / len(vendor_df), text="Loading items...")
            time.sleep(0.2)
            progress_bar.empty()
            msg_container.success(f"✅ Loaded {len(vendor_df)} items successfully!")

        st.session_state.vendor_df = vendor_df
        st.session_state.worksheet = worksheet
        st.session_state.headers = worksheet.row_values(1)
        st.session_state.vendor_name = vendor_df.iloc[0].get("PrimaryVendorName", f"Vendor {vendor_id}")

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

    # --- Table Headers ---
    cols = st.columns([0.8, 1.8, 0.9, 1, 2.5, 2.5, 3])
    with cols[0]: st.markdown("**Image**")
    with cols[1]: st.markdown("**Taxonomy**")
    with cols[2]: st.markdown("**SKU**")
    with cols[3]: st.markdown("**Item #**")
    with cols[4]: st.markdown("**Product Name**")
    with cols[5]: st.markdown("**Country of Origin**")
    with cols[6]: st.markdown("**HTS Code + Submit**")

    updated_df = st.session_state.vendor_df.copy()
    rows_to_keep = []

    for i, row in updated_df.iterrows():
        cols = st.columns([0.8, 1.8, 0.9, 1, 2.5, 2.5, 3])

        with cols[0]:
            img_url = row.get("ImageURL", "").strip()
            if img_url:
                try:
                    response = requests.get(img_url, timeout=3)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        st.image(img, width=45)
                    else:
                        st.markdown("No Image")
                except:
                    st.markdown("No Image")
            else:
                st.markdown("No Image")

        with cols[1]: st.markdown(row.get("Taxonomy", ""))
        with cols[2]: st.markdown(str(row.get("SKUID", "")))
        with cols[3]: st.markdown(str(row.get("SiteOneItemNumber", "")))
        with cols[4]: st.markdown(str(row.get("ProductName", "")))

        with cols[5]:
            with st.container():
                st.markdown('<div class="dropdown-align">', unsafe_allow_html=True)
                country = st.selectbox(
                    label="",
                    options=dropdown_options,
                    index=0,
                    key=f"country_{i}"
                )
                st.markdown('</div>', unsafe_allow_html=True)

        with cols[6]:
            c1, c2 = st.columns([2.2, 1])
            with c1:
                hts_code = st.text_input("", value="", key=f"hts_{i}", max_chars=10, label_visibility="collapsed")
            with c2:
                submitted = st.button("Submit", key=f"submit_{i}")

        if submitted:
            if country == "Select...":
                st.warning(f"⚠️ Country not selected for SKU {row['SKUID']}")
                rows_to_keep.append(row)
                continue
            if not hts_code.isdigit() or len(hts_code) != 10:
                st.warning(f"⚠️ Invalid HTS Code for SKU {row['SKUID']}")
                rows_to_keep.append(row)
                continue

            try:
                row_index = i + 2
                country_col = st.session_state.headers.index("CountryofOrigin") + 1
                hts_col = st.session_state.headers.index("HTSCode") + 1
                st.session_state.worksheet.update_cell(row_index, country_col, country)
                st.session_state.worksheet.update_cell(row_index, hts_col, hts_code)
                st.success(f"✅ Submitted SKU {row['SKUID']}")
            except Exception as e:
                st.error(f"Error saving SKU {row['SKUID']}: {e}")
                rows_to_keep.append(row)
        else:
            rows_to_keep.append(row)

    st.session_state.vendor_df = pd.DataFrame(rows_to_keep).reset_index(drop=True)

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

# --- Login Page ---
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

# --- Main ---
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        vendor_dashboard(st.session_state.current_vendor)

if __name__ == "__main__":
    main()
