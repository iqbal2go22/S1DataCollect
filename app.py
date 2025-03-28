import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pycountry
from PIL import Image
import requests
from io import BytesIO
import time
import uuid

st.set_page_config(page_title="Product Origin Data Collection", page_icon="🌍", layout="wide")

# --- Custom CSS ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
        }
        div[data-testid="column"] > div {
            align-items: center !important;
        }
        .stTextInput input {
            text-align: center;
        }
        .stSelectbox > div {
            margin-top: 0 !important;
        }
        /* Progress counter styling */
        .progress-counter {
            font-size: 24px;
            text-align: center;
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            font-weight: bold;
        }
        .progress-counter-large {
            font-size: 42px;
            color: #0068c9;
            margin: 0;
            padding: 0;
        }
        /* For submitted items */
        .submitted-row {
            background-color: #d4edda;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
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
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "submitted_skus" not in st.session_state:
    st.session_state.submitted_skus = set()

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
    
    # Hard reset if needed
    if 'reset_all' in st.session_state and st.session_state.reset_all:
        for key in list(st.session_state.keys()):
            if key not in ['logged_in', 'current_vendor']:
                if key in st.session_state:
                    del st.session_state[key]
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.submitted_skus = set()
    
    # Load data if not already loaded
    if "vendor_df" not in st.session_state or st.session_state.vendor_df is None:
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
        
        # Get all items for this vendor
        all_vendor_items = df[df["PrimaryVendorNumber"] == vendor_id].copy()
        total_items = len(all_vendor_items)
        
        # Filter to incomplete items only
        vendor_df = all_vendor_items[
            (all_vendor_items["CountryofOrigin"].isna()) | 
            (all_vendor_items["CountryofOrigin"] == "") |
            (all_vendor_items["HTSCode"].isna()) | 
            (all_vendor_items["HTSCode"] == "")
        ].copy()
        
        if vendor_df.empty:
            st.success("✅ All items for this vendor have already been submitted.")
            return

        vendor_df = vendor_df.sort_values("Taxonomy").reset_index(drop=True)
        
        # Store the data
        st.session_state.vendor_df = vendor_df
        st.session_state.all_vendor_items = all_vendor_items
        st.session_state.total_items = total_items
        st.session_state.worksheet = worksheet
        st.session_state.headers = worksheet.row_values(1)
        st.session_state.vendor_name = vendor_df.iloc[0].get("PrimaryVendorName", f"Vendor {vendor_id}")

    st.title(f"{st.session_state.vendor_name} ({vendor_id})")
    
    # Calculate current stats
    if "submitted_skus" in st.session_state:
        submitted_count = len(st.session_state.submitted_skus)
    else:
        submitted_count = 0
    
    # Get total items and remaining items
    remaining_count = len(st.session_state.vendor_df) - submitted_count
    if remaining_count < 0:
        remaining_count = 0
    
    # Big progress counter at the top
    st.markdown(f"""
    <div class="progress-counter">
        <p>Items Remaining</p>
        <p class="progress-counter-large">{remaining_count} / {st.session_state.total_items}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    **Instructions:**
    - Select a **Country of Origin** using the dropdown.
    - Enter the **HTS Code** as a 10-digit number (no periods).
    - If you only have 6 or 8 digits, add trailing 0s (e.g. `0601101500`).
    - Each row will disappear after successful submission.
    """)
    st.markdown("---")

    all_countries = sorted([f"{c.alpha_2} - {c.name}" for c in pycountry.countries])
    dropdown_options = ["Select..."] + all_countries

    # --- Table Header ---
    cols = st.columns([0.8, 1.8, 0.9, 1, 2.5, 2.5, 3])
    with cols[0]: st.markdown("**Image**")
    with cols[1]: st.markdown("**Taxonomy**")
    with cols[2]: st.markdown("**SKU**")
    with cols[3]: st.markdown("**Item #**")
    with cols[4]: st.markdown("**Product Name**")
    with cols[5]: st.markdown("**Country of Origin**")
    with cols[6]: st.markdown("**HTS Code + Submit**")
    
    if "vendor_df" not in st.session_state or st.session_state.vendor_df is None or len(st.session_state.vendor_df) == 0:
        st.success("🎉 All items have been successfully completed! Thank you!")
        return

    # Display recently submitted items
    for sku in list(st.session_state.submitted_skus):
        # Find the item in the dataframe
        item_row = st.session_state.vendor_df[st.session_state.vendor_df['SKUID'].astype(str) == str(sku)]
        if not item_row.empty:
            st.markdown(f"""
            <div class="submitted-row">
                ✅ Submitted: {item_row.iloc[0]['ProductName']} (SKU: {sku})
            </div>
            """, unsafe_allow_html=True)
    
    # Skip over rows that have already been submitted in this session
    skus_to_display = []
    for i, row in st.session_state.vendor_df.iterrows():
        sku = str(row['SKUID'])
        if sku not in st.session_state.submitted_skus:
            skus_to_display.append(sku)

    # If all rows have been submitted, show completion message
    if not skus_to_display:
        st.balloons()
        st.success("🎉 All items have been successfully completed! Thank you!")
        st.session_state.vendor_df = None
        return
    
    # Display only rows that haven't been submitted in this session
    for i, row in st.session_state.vendor_df.iterrows():
        sku = str(row['SKUID'])
        if sku in st.session_state.submitted_skus:
            continue

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
            country = st.selectbox(
                label="",
                options=dropdown_options,
                index=0,
                key=f"country_{sku}",
                label_visibility="collapsed"
            )

        with cols[6]:
            c1, c2 = st.columns([2.2, 1])
            with c1:
                hts_code = st.text_input("", value="", key=f"hts_{sku}", max_chars=10, label_visibility="collapsed")
            with c2:
                submitted = st.button("Submit", key=f"submit_{sku}")

        if submitted:
            if country == "Select...":
                st.warning(f"⚠️ Country not selected for SKU {sku}")
                continue
            if not hts_code.isdigit() or len(hts_code) != 10:
                st.warning(f"⚠️ Invalid HTS Code for SKU {sku}")
                continue

            try:
                # Find the actual row in the spreadsheet
                all_skus = st.session_state.worksheet.col_values(st.session_state.headers.index("SKUID") + 1)
                try:
                    row_index = all_skus.index(str(sku)) + 1
                except ValueError:
                    # If SKU not found by string, try finding by number
                    try:
                        row_index = all_skus.index(str(int(sku))) + 1
                    except:
                        st.error(f"Could not find SKU {sku} in the spreadsheet")
                        continue
                
                country_col = st.session_state.headers.index("CountryofOrigin") + 1
                hts_col = st.session_state.headers.index("HTSCode") + 1
                
                st.session_state.worksheet.update_cell(row_index, country_col, country)
                st.session_state.worksheet.update_cell(row_index, hts_col, hts_code)
                
                # Mark this SKU as submitted
                st.session_state.submitted_skus.add(sku)
                
                # Force a rerun to update the UI
                st.rerun()
                
            except Exception as e:
                st.error(f"Error saving SKU {sku}: {e}")

    # Button for submitting all remaining items
    if len(skus_to_display) > 0:
        if st.button("Submit All Remaining Items"):
            items_processed = 0
            for sku in skus_to_display:
                country = st.session_state.get(f"country_{sku}", "Select...")
                hts = st.session_state.get(f"hts_{sku}", "")
                if country == "Select..." or not hts.isdigit() or len(hts) != 10:
                    continue
                
                try:
                    # Find the row in the dataframe
                    row = st.session_state.vendor_df[st.session_state.vendor_df['SKUID'].astype(str) == str(sku)].iloc[0]
                    
                    # Find the actual row in the spreadsheet
                    all_skus = st.session_state.worksheet.col_values(st.session_state.headers.index("SKUID") + 1)
                    try:
                        row_index = all_skus.index(str(sku)) + 1
                    except ValueError:
                        # If SKU not found by string, try finding by number
                        try:
                            row_index = all_skus.index(str(int(sku))) + 1
                        except:
                            st.error(f"Could not find SKU {sku} in the spreadsheet")
                            continue
                    
                    country_col = st.session_state.headers.index("CountryofOrigin") + 1
                    hts_col = st.session_state.headers.index("HTSCode") + 1
                    
                    st.session_state.worksheet.update_cell(row_index, country_col, country)
                    st.session_state.worksheet.update_cell(row_index, hts_col, hts_code)
                    
                    # Mark this SKU as submitted
                    st.session_state.submitted_skus.add(sku)
                    
                    items_processed += 1
                except Exception as e:
                    st.error(f"Error saving SKU {sku}: {e}")
            
            if items_processed > 0:
                st.success(f"✅ {items_processed} items submitted successfully.")
                st.rerun()
            else:
                st.warning("No items were submitted. Please fill in required fields.")

    # Debug button (hidden in production)
    if st.sidebar.button("Reset Session (Debug)"):
        st.session_state.reset_all = True
        st.rerun()

# --- Login ---
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