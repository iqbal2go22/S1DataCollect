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
        div[data-testid="column"] > div {
            align-items: center !important;  /* Fixed alignment issue */
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
        /* Success message styling */
        .success-message {
            background-color: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            text-align: center;
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
if "total_items" not in st.session_state:
    st.session_state.total_items = 0
if "total_remaining" not in st.session_state:
    st.session_state.total_remaining = 0
if "submitted_items" not in st.session_state:
    st.session_state.submitted_items = []

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

    # Load data if not already loaded or if we need to refresh
    if st.session_state.vendor_df is None or "refresh_data" in st.session_state and st.session_state.refresh_data:
        if "refresh_data" in st.session_state:
            del st.session_state.refresh_data
            
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

        # Filter by vendor and exclude already completed rows
        vendor_df = df[
            (df["PrimaryVendorNumber"] == vendor_id) &
            ((df["CountryofOrigin"].isna()) | (df["CountryofOrigin"] == "") |
             (df["HTSCode"].isna()) | (df["HTSCode"] == ""))
        ].copy()
        
        # Also exclude any items that were submitted in this session
        if "submitted_items" in st.session_state and len(st.session_state.submitted_items) > 0:
            vendor_df = vendor_df[~vendor_df["SKUID"].astype(str).isin(st.session_state.submitted_items)].copy()

        if vendor_df.empty:
            st.success("✅ All items for this vendor have already been submitted.")
            return

        vendor_df = vendor_df.sort_values("Taxonomy").reset_index(drop=True)
        
        # Store total count for progress tracking
        st.session_state.total_items = len(df[df["PrimaryVendorNumber"] == vendor_id])
        st.session_state.total_remaining = len(vendor_df)

        # Progress bar
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
    
    # Count completed and total
    completed_count = st.session_state.total_items - st.session_state.total_remaining
    
    # Big progress counter at the top
    st.markdown(f"""
    <div class="progress-counter">
        <p>Items Remaining</p>
        <p class="progress-counter-large">{st.session_state.total_remaining} / {st.session_state.total_items}</p>
        <p>({completed_count} completed)</p>
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

    # Display any recently submitted items
    if "recent_submissions" in st.session_state and st.session_state.recent_submissions:
        for sku in st.session_state.recent_submissions:
            st.markdown(f"""
            <div class="success-message">
                ✅ Submitted SKU {sku}
            </div>
            """, unsafe_allow_html=True)
        # Clear recent submissions after displaying them
        st.session_state.recent_submissions = []

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

    if st.session_state.vendor_df is None or len(st.session_state.vendor_df) == 0:
        st.success("🎉 All items have been successfully completed! Thank you!")
        return

    updated_df = st.session_state.vendor_df.copy()
    rows_to_keep = []
    recent_submissions = []

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
            country = st.selectbox(
                label="",
                options=dropdown_options,
                index=0,
                key=f"country_{i}",
                label_visibility="collapsed"  # Improve alignment
            )

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
                # Find the actual row in the spreadsheet
                all_skus = st.session_state.worksheet.col_values(st.session_state.headers.index("SKUID") + 1)
                try:
                    row_index = all_skus.index(str(row['SKUID'])) + 1
                except ValueError:
                    # If SKU not found by string, try finding by number
                    try:
                        row_index = all_skus.index(str(int(row['SKUID']))) + 1
                    except:
                        st.error(f"Could not find SKU {row['SKUID']} in the spreadsheet")
                        rows_to_keep.append(row)
                        continue
                
                country_col = st.session_state.headers.index("CountryofOrigin") + 1
                hts_col = st.session_state.headers.index("HTSCode") + 1
                
                st.session_state.worksheet.update_cell(row_index, country_col, country)
                st.session_state.worksheet.update_cell(row_index, hts_col, hts_code)
                
                # Track this submission
                if "submitted_items" not in st.session_state:
                    st.session_state.submitted_items = []
                st.session_state.submitted_items.append(str(row['SKUID']))
                
                # Add to recent submissions to show on next refresh
                recent_submissions.append(str(row['SKUID']))
                
                # Update counter
                st.session_state.total_remaining -= 1
                
                # Don't add this row to rows_to_keep (it will be removed)
            except Exception as e:
                st.error(f"Error saving SKU {row['SKUID']}: {e}")
                rows_to_keep.append(row)
        else:
            rows_to_keep.append(row)

    # If submissions happened, store them and trigger a refresh
    if recent_submissions:
        st.session_state.recent_submissions = recent_submissions
        st.session_state.refresh_data = True
        st.rerun()

    # Rebuild remaining view
    st.session_state.vendor_df = pd.DataFrame(rows_to_keep).reset_index(drop=True)

    # Check if we're done
    if st.session_state.total_remaining == 0 or len(st.session_state.vendor_df) == 0:
        st.balloons()
        st.success("🎉 All items have been successfully completed! Thank you!")
        st.session_state.vendor_df = None
    elif len(st.session_state.vendor_df) > 0:
        if st.button("Submit All Remaining Items"):
            items_processed = 0
            newly_submitted = []
            for i, row in st.session_state.vendor_df.iterrows():
                country = st.session_state.get(f"country_{i}", "Select...")
                hts = st.session_state.get(f"hts_{i}", "")
                if country == "Select..." or not hts.isdigit() or len(hts) != 10:
                    continue
                
                try:
                    # Find the actual row in the spreadsheet
                    all_skus = st.session_state.worksheet.col_values(st.session_state.headers.index("SKUID") + 1)
                    try:
                        row_index = all_skus.index(str(row['SKUID'])) + 1
                    except ValueError:
                        # If SKU not found by string, try finding by number
                        try:
                            row_index = all_skus.index(str(int(row['SKUID']))) + 1
                        except:
                            st.error(f"Could not find SKU {row['SKUID']} in the spreadsheet")
                            continue
                    
                    country_col = st.session_state.headers.index("CountryofOrigin") + 1
                    hts_col = st.session_state.headers.index("HTSCode") + 1
                    
                    st.session_state.worksheet.update_cell(row_index, country_col, country)
                    st.session_state.worksheet.update_cell(row_index, hts_col, hts)
                    
                    # Track this submission
                    if "submitted_items" not in st.session_state:
                        st.session_state.submitted_items = []
                    st.session_state.submitted_items.append(str(row['SKUID']))
                    newly_submitted.append(str(row['SKUID']))
                    
                    items_processed += 1
                except Exception as e:
                    st.error(f"Error saving SKU {row['SKUID']}: {e}")
            
            if items_processed > 0:
                st.session_state.total_remaining -= items_processed
                st.session_state.recent_submissions = newly_submitted
                st.success(f"✅ {items_processed} items submitted successfully.")
                st.session_state.refresh_data = True
                st.rerun()
            else:
                st.warning("No items were submitted. Please fill in required fields.")

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