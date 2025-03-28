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
import base64

# SiteOne brand colors
SITEONE_GREEN = "#5a8f30"
SITEONE_LIGHT_GREEN = "#8bc53f"
SITEONE_DARK_GREEN = "#3e6023"
SITEONE_GRAY = "#f2f2f2"
SITEONE_DARK_GRAY = "#333333"

# Set page config with no menu and full width
st.set_page_config(
    page_title="Product Origin Data Collection", 
    page_icon="🌍", 
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# --- Custom CSS ---
st.markdown(f"""
    <style>
        /* Hide the gray top bar and other Streamlit UI elements */
        #MainMenu {{visibility: hidden;}}
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        .css-18e3th9 {{padding-top: 0 !important;}}
        .css-1d391kg {{padding-top: 0 !important;}}
        .block-container {{padding-top: 0 !important; max-width: 100% !important;}}
        
        /* Completely remove all gray bars */
        div.stDeployButton {{display: none;}}
        section[data-testid="stSidebar"] {{display: none;}}
        .stAlert {{display: none;}}
        
        /* Main theme colors */
        :root {{
            --siteone-green: {SITEONE_GREEN};
            --siteone-light-green: {SITEONE_LIGHT_GREEN};
            --siteone-dark-green: {SITEONE_DARK_GREEN};
            --siteone-gray: {SITEONE_GRAY};
            --siteone-dark-gray: {SITEONE_DARK_GRAY};
        }}
        
        /* Enhanced Header styling */
        .siteone-header {{
            background-color: var(--siteone-green);
            color: white;
            padding: 1.2rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0 !important;
            border-bottom: 5px solid var(--siteone-light-green);
            width: 100%;
        }}
        
        .header-logo {{
            display: flex;
            align-items: center;
        }}
        
        .header-vendor-info {{
            text-align: right;
        }}
        
        .header-vendor-name {{
            font-size: 36px;
            font-weight: bold;
            margin: 0;
        }}
        
        /* Column alignment */
        div[data-testid="column"] > div {{
            align-items: center !important;
        }}
        
        /* Input styling */
        .stTextInput input {{
            text-align: center;
        }}
        
        .stSelectbox > div {{
            margin-top: 0 !important;
        }}
        
        /* Progress gauge styling */
        .gauge-container {{
            background-color: var(--siteone-gray);
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem auto;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            max-width: 500px;
        }}
        
        .gauge-title {{
            font-size: 32px;
            font-weight: bold;
            color: var(--siteone-dark-gray);
            margin-bottom: 1rem;
            text-align: center;
            margin-top: 1rem;
        }}
        
        /* CSS-based gauge */
        .progress-gauge {{
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: #e0e0e0;
            position: relative;
            margin: 0 auto;
            overflow: hidden;
        }}
        
        .progress-gauge:before {{
            content: "";
            display: block;
            position: absolute;
            top: 10px;
            left: 10px;
            width: 130px;
            height: 130px;
            border-radius: 50%;
            background: #fff;
            z-index: 1;
        }}
        
        .progress-value {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: bold;
            color: var(--siteone-dark-green);
            z-index: 2;
        }}
        
        .progress-count {{
            position: absolute;
            top: 68%;
            left: 0;
            width: 100%;
            text-align: center;
            font-size: 14px;
            color: var(--siteone-dark-gray);
            z-index: 2;
        }}
        
        .progress-fill {{
            position: absolute;
            top: 0;
            left: 0;
            width: 150px;
            height: 150px;
            clip-path: polygon(50% 50%, 100% 0, 100% 100%, 0 100%, 0 0);
            background: var(--siteone-green);
            transform-origin: center;
        }}
        
        /* Success message styling */
        .submitted-row {{
            background-color: #d4edda;
            border-left: 5px solid var(--siteone-green);
            padding: 10px 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        }}
        
        /* Button styling */
        .stButton button {{
            background-color: var(--siteone-green) !important;
            color: white !important;
            font-weight: bold !important;
        }}
        
        .stButton button:hover {{
            background-color: var(--siteone-dark-green) !important;
        }}
        
        /* Table header styling */
        .table-header {{
            background-color: var(--siteone-gray);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        
        /* Instructions styling */
        .instructions {{
            background-color: #e9f5e9;
            border-left: 5px solid var(--siteone-green);
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        
        /* Footer styling */
        .footer {{
            margin-top: 3rem;
            text-align: center;
            color: var(--siteone-dark-gray);
            font-size: 14px;
        }}
        
        /* Remove gray bar under header */
        .stApp {{
            margin-top: 0 !important;
            padding-top: 0 !important;
        }}
        
        .stApp > header {{
            display: none !important;
        }}
        
        div:has(> .stApp) {{
            padding-top: 0 !important;
        }}
    </style>
""", unsafe_allow_html=True)

# --- SiteOne Logo Base64 ---
SITEONE_LOGO = "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"

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

# --- HTML/CSS-based gauge function ---
def create_gauge_html(percentage, remaining, total):
    # Calculate rotation angle based on percentage (0-360 degrees)
    rotation = min(360, max(0, percentage * 3.6))  # 3.6 = 360/100
    
    gauge_html = f"""
    <div class="progress-gauge">
        <div class="progress-fill" style="transform: rotate({rotation}deg);"></div>
        <div class="progress-value">{int(percentage)}%</div>
        <div class="progress-count">{remaining} of {total} items</div>
    </div>
    """
    
    return gauge_html

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

# --- Enhanced SiteOne Header Component ---
def render_header(vendor_name, vendor_id):
    st.markdown(f"""
    <div class="siteone-header">
        <div class="header-logo">
            <img src="data:image/png;base64,{SITEONE_LOGO}" alt="SiteOne Logo" height="60">
        </div>
        <div class="header-vendor-info">
            <p class="header-vendor-name">{vendor_name}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Vendor Form ---
def vendor_dashboard(vendor_id):
    vendor_id = vendor_id.strip().upper()
    
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
        
        if total_items == 0:
            st.error(f"No items found for vendor ID: {vendor_id}")
            return
        
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

    # Render the SiteOne header
    render_header(st.session_state.vendor_name, vendor_id)
    
    # Calculate stats
    if "submitted_skus" in st.session_state:
        submitted_count = len(st.session_state.submitted_skus)
    else:
        submitted_count = 0
    
    # Get total items and remaining items
    total_items = st.session_state.total_items
    remaining_items = len(st.session_state.vendor_df) - submitted_count
    if remaining_items < 0:
        remaining_items = 0
        
    completed_items = total_items - remaining_items
    completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
    
    # Progress gauge with larger title
    st.markdown('<h1 class="gauge-title">Items Remaining</h1>', unsafe_allow_html=True)
    st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
    gauge_html = create_gauge_html(completion_percentage, remaining_items, total_items)
    st.markdown(gauge_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Instructions
    st.markdown("""
    <div class="instructions">
        <h3>Instructions:</h3>
        <ul>
            <li>Select a <strong>Country of Origin</strong> using the dropdown.</li>
            <li>Enter the <strong>HTS Code</strong> as a 10-digit number (no periods).</li>
            <li>If you only have 6 or 8 digits, add trailing 0s (e.g. <code>0601101500</code>).</li>
            <li>Click <strong>Submit</strong> after completing each item.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

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
    
    # --- Table Header ---
    cols = st.columns([0.8, 1.8, 0.9, 1, 2.5, 2.5, 3])
    with cols[0]: st.markdown('<div class="table-header">Image</div>', unsafe_allow_html=True)
    with cols[1]: st.markdown('<div class="table-header">Taxonomy</div>', unsafe_allow_html=True)
    with cols[2]: st.markdown('<div class="table-header">SKU</div>', unsafe_allow_html=True)
    with cols[3]: st.markdown('<div class="table-header">Item #</div>', unsafe_allow_html=True)
    with cols[4]: st.markdown('<div class="table-header">Product Name</div>', unsafe_allow_html=True)
    with cols[5]: st.markdown('<div class="table-header">Country of Origin</div>', unsafe_allow_html=True)
    with cols[6]: st.markdown('<div class="table-header">HTS Code + Submit</div>', unsafe_allow_html=True)
    
    if "vendor_df" not in st.session_state or st.session_state.vendor_df is None or len(st.session_state.vendor_df) == 0:
        st.success("🎉 All items have been successfully completed! Thank you!")
        return

    all_countries = sorted([f"{c.alpha_2} - {c.name}" for c in pycountry.countries])
    dropdown_options = ["Select..."] + all_countries
    
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
                
                # Add prefix to HTS code to preserve leading zeros
                st.session_state.worksheet.update_cell(row_index, country_col, country)
                st.session_state.worksheet.update_cell(row_index, hts_col, f"'{hts_code}")
                
                # Mark this SKU as submitted
                st.session_state.submitted_skus.add(sku)
                
                # Force a rerun to update the UI
                st.rerun()
                
            except Exception as e:
                st.error(f"Error saving SKU {sku}: {e}")

    # Button for submitting all remaining items
    if len(skus_to_display) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Submit All Remaining Items", type="primary"):
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
                    
                    # Add prefix to HTS code to preserve leading zeros
                    st.session_state.worksheet.update_cell(row_index, country_col, country)
                    st.session_state.worksheet.update_cell(row_index, hts_col, f"'{hts}")
                    
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
    
    # Add footer
    st.markdown("""
    <div class="footer">
        <p>© 2025 SiteOne Landscape Supply. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)

# --- Login ---
def login_page():
    # Render SiteOne logo
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0;">
        <img src="data:image/png;base64,{SITEONE_LOGO}" alt="SiteOne Logo" height="100">
        <h1 style="color: {SITEONE_GREEN}; margin-top: 1rem;">Product Origin Data Collection</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Check URL parameters
    params = st.query_params
    if "vendor" in params:
        vendor_id = params["vendor"]
        st.session_state.logged_in = True
        st.session_state.current_vendor = vendor_id
        st.rerun()
    
    # Create a centered login box
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="background-color: white; padding: 2rem; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-top: 5px solid {SITEONE_GREEN};">
            <h3 style="color: {SITEONE_DARK_GREEN}; margin-bottom: 1rem;">Vendor Login</h3>
            <p>Please enter your Vendor ID to continue.</p>
        </div>
        """, unsafe_allow_html=True)
        
        vendor_id = st.text_input("Vendor ID")
        if st.button("Login", type="primary"):
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