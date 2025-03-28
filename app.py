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
    menu_items=None  # Remove the menu
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
            margin-bottom: 2rem;
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
            font-size: 28px;
            font-weight: bold;
            margin: 0;
            margin-bottom: 5px;
        }}
        
        .header-vendor-id {{
            font-size: 18px;
            opacity: 0.9;
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
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .gauge-title {{
            font-size: 22px;
            font-weight: bold;
            color: var(--siteone-dark-gray);
            margin-bottom: 0.5rem;
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

# --- SiteOne Logo Base64 ---
# Replace this with your actual SiteOne logo - this is a placeholder
SITEONE_LOGO = """
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
"""

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
            <p class="header-vendor-id">Vendor ID: {vendor_id}</p>
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
    
    # Progress gauge
    st.markdown('<div class="gauge-container">', unsafe_allow_html=True)
    st.markdown('<p class="gauge-title">Items Remaining</p>', unsafe_allow_html=True)
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
                    
                    st.session_state.worksheet.update_cell(row_index, country_col, country)
                    st.session_state.worksheet.update_cell(row_index, hts_col, hts)
                    
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