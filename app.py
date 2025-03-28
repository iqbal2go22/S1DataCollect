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
        div[data-testid="stDecoration"] {{display: none;}}
        div[data-testid="collapsedControl"] {{display: none;}}
        
        /* Remove all whitespace gaps */
        .css-1544g2n {{padding-top: 0 !important;}}
        .st-emotion-cache-1544g2n {{padding-top: 0 !important;}}
        .st-emotion-cache-183lzff {{white-space: unset;}}
        
        /* Force all elements to the top */
        body > div {{padding-top: 0 !important; margin-top: 0 !important;}}
        
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
            margin: 2rem auto;
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
SITEONE_LOGO = "YOUR_BASE64_LOGO_HERE"

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
    
    # Progress gauge - centered with larger title
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