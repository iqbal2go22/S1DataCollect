import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# Page configuration
st.set_page_config(
    page_title="Product Origin Data Collection",
    page_icon="🌍",
    layout="wide"
)

# Define Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Country options for dropdown
COUNTRY_OPTIONS = [
    "US - United States", 
    "CA - Canada", 
    "MX - Mexico", 
    "CN - China", 
    "IN - India", 
    "VN - Vietnam", 
    "DE - Germany",
    "JP - Japan",
    "GB - United Kingdom",
    "FR - France",
    "IT - Italy",
    "ES - Spain",
    "BR - Brazil",
    "AU - Australia",
    "KR - South Korea",
    "ID - Indonesia",
    "TH - Thailand",
    "MY - Malaysia",
    "SG - Singapore",
    "PH - Philippines"
]

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None
if "google_connected" not in st.session_state:
    st.session_state.google_connected = False
if "connection_error" not in st.session_state:
    st.session_state.connection_error = None

# Function to connect to Google Sheets API
def get_google_sheets_connection():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        st.session_state.google_connected = True
        st.session_state.connection_error = None
        return client
    except Exception as e:
        st.session_state.google_connected = False
        st.session_state.connection_error = str(e)
        return None

# Function to load data from Google Sheet with error handling
def load_sheet_data(sheet_name="Sheet1"):
    try:
        # Get Google Sheets connection
        client = get_google_sheets_connection()
        if not client:
            return None
            
        # Open the spreadsheet
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        
        # Get the worksheet
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Convert to dataframe
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        return df
    except Exception as e:
        st.error(f"Error loading data from sheet '{sheet_name}': {e}")
        return None

# Function to validate HTS code
def validate_hts_code(code):
    # Remove any non-numeric characters
    code = ''.join(filter(str.isdigit, str(code)))
    
    # Check if it's 6 or 10 digits
    if len(code) == 6:
        return True, code + "0000"  # Auto-expand to 10 digits
    elif len(code) == 10:
        return True, code
    else:
        return False, "HTS code must be 6 or 10 digits"

# Function to create Vendors worksheet if it doesn't exist
def ensure_vendors_worksheet_exists():
    try:
        client = get_google_sheets_connection()
        if not client:
            return False
            
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        
        # Check if vendors worksheet exists
        try:
            vendors_sheet = spreadsheet.worksheet("Vendors")
            return True
        except:
            # Create vendors worksheet if it doesn't exist
            vendors_sheet = spreadsheet.add_worksheet(title="Vendors", rows=100, cols=5)
            vendors_sheet.append_row(["VendorID", "VendorName", "Email"])
            return True
    except Exception as e:
        st.error(f"Error ensuring vendors worksheet exists: {e}")
        return False

# Function to update product data in spreadsheet
def update_product_data(vendor_id, sku, country, hts_code):
    try:
        client = get_google_sheets_connection()
        if not client:
            return False
            
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        worksheet = spreadsheet.worksheet("Sheet1")
        
        # Get all data
        data = worksheet.get_all_records()
        
        # Find row with matching SKU and vendor ID
        row_to_update = None
        for i, row in enumerate(data):
            if row.get("SKUID") == sku and row.get("PrimaryVendorNumber") == vendor_id:
                row_to_update = i + 2  # +2 because of header row and 0-indexing
                break
                
        if row_to_update:
            # Update Country of Origin
            country_col = None
            hts_col = None
            header_row = worksheet.row_values(1)
            
            # Find column indices for CountryOfOrigin and HTSCode
            try:
                country_col = header_row.index("CountryOfOrigin") + 1
            except:
                # Add CountryOfOrigin column if it doesn't exist
                country_col = len(header_row) + 1
                worksheet.update_cell(1, country_col, "CountryOfOrigin")
                
            try:
                hts_col = header_row.index("HTSCode") + 1
            except:
                # Add HTSCode column if it doesn't exist
                hts_col = len(header_row) + 1
                worksheet.update_cell(1, hts_col, "HTSCode")
            
            # Update cells
            worksheet.update_cell(row_to_update, country_col, country)
            worksheet.update_cell(row_to_update, hts_col, hts_code)
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error updating product data: {e}")
        return False

# Login page
def login_page():
    st.title("🌍 Product Origin Data Collection")
    
    # Check Google Sheets connection
    if not st.session_state.google_connected:
        client = get_google_sheets_connection()
        if not client:
            st.error(f"Error connecting to Google Sheets: {st.session_state.connection_error}")
            st.info("Basic login will still work, but Google Sheets functionality will be limited.")
    
    # Create two columns for login options
    left_column, right_column = st.columns(2)
    
    # Vendor login
    with left_column:
        st.subheader("Vendor Login")
        st.info("If you're a vendor, please use the link provided to you by email.")
        
        # Check URL parameters
        params = st.query_params
        if "vendor" in params:
            vendor_id = params["vendor"]
            
            # Verify vendor ID
            if st.session_state.google_connected:
                try:
                    # Try to load vendors from sheet
                    vendors_df = load_sheet_data("Vendors")
                    if vendors_df is not None and not vendors_df.empty and 'VendorID' in vendors_df.columns:
                        if vendor_id in vendors_df['VendorID'].values:
                            st.session_state.logged_in = True
                            st.session_state.is_admin = False
                            st.session_state.current_vendor = vendor_id
                            st.rerun()
                        else:
                            st.error("Invalid vendor ID. Please contact the administrator.")
                    else:
                        # If Vendors sheet doesn't exist or is empty
                        st.warning("Vendor verification is unavailable. Using basic login.")
                        st.session_state.logged_in = True
                        st.session_state.is_admin = False
                        st.session_state.current_vendor = vendor_id
                        st.rerun()
                except Exception as e:
                    st.warning(f"Error verifying vendor: {e}")
                    st.warning("Using basic login instead.")
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_vendor = vendor_id
                    st.rerun()
            else:
                # If Google Sheets connection failed, use basic login
                st.warning("Vendor verification is unavailable. Using basic login.")
                st.session_state.logged_in = True
                st.session_state.is_admin = False
                st.session_state.current_vendor = vendor_id
                st.rerun()
        
        # Manual vendor login
        vendor_id = st.text_input("Vendor ID")
        vendor_login = st.button("Login as Vendor")
        
        if vendor_login:
            if not vendor_id:
                st.error("Please enter your Vendor ID")
            else:
                if st.session_state.google_connected:
                    try:
                        # Try to load vendors from sheet
                        vendors_df = load_sheet_data("Vendors")
                        if vendors_df is not None and not vendors_df.empty and 'VendorID' in vendors_df.columns:
                            if vendor_id in vendors_df['VendorID'].values:
                                st.session_state.logged_in = True
                                st.session_state.is_admin = False
                                st.session_state.current_vendor = vendor_id
                                st.rerun()
                            else:
                                st.error("Invalid vendor ID. Please contact the administrator.")
                        else:
                            # If Vendors sheet doesn't exist or is empty
                            st.warning("Vendor verification is unavailable. Using basic login.")
                            st.session_state.logged_in = True
                            st.session_state.is_admin = False
                            st.session_state.current_vendor = vendor_id
                            st.rerun()
                    except Exception as e:
                        st.warning(f"Error verifying vendor: {e}")
                        st.warning("Using basic login instead.")
                        st.session_state.logged_in = True
                        st.session_state.is_admin = False
                        st.session_state.current_vendor = vendor_id
                        st.rerun()
                else:
                    # If Google Sheets connection failed, use basic login
                    st.warning("Vendor verification is unavailable. Using basic login.")
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_vendor = vendor_id
                    st.rerun()
    
    # Admin login
    with right_column:
        st.subheader("Admin Login")
        st.info("For admin access to manage products and vendors.")
        
        # Admin login form
        admin_password = st.text_input("Admin Password", type="password")
        admin_login = st.button("Login as Admin")
        
        if admin_login:
            if not admin_password:
                st.error("Please enter the admin password")
            else:
                # Get expected password from secrets
                expected_pwd = st.secrets.get("admin_password", "admin123")
                
                if admin_password == expected_pwd:
                    st.session_state.logged_in = True
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Invalid admin password")

# Admin Dashboard
def admin_dashboard():
    st.title("🔐 Admin Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["📋 Products", "👥 Vendors", "📊 Data Export"])
    
    # Products Tab
    with tab1:
        st.header("Product Management")
        
        # Check Google Sheets connection
        if not st.session_state.google_connected:
            st.error(f"Error connecting to Google Sheets: {st.session_state.connection_error}")
            st.info("Connect to Google Sheets to manage products.")
        else:
            # Load product data
            data_df = load_sheet_data("Sheet1")
            
            if data_df is not None:
                # Display product data
                st.subheader("Current Products")
                
                if data_df.empty:
                    st.info("No products found in the sheet. Make sure your spreadsheet contains product data.")
                else:
                    # Add CountryOfOrigin and HTSCode columns if they don't exist
                    if 'CountryOfOrigin' not in data_df.columns:
                        data_df['CountryOfOrigin'] = ""
                    
                    if 'HTSCode' not in data_df.columns:
                        data_df['HTSCode'] = ""
                    
                    # Filter options
                    if 'PrimaryVendorName' in data_df.columns:
                        vendor_filter = st.selectbox(
                            "Filter by Vendor", 
                            options=["All"] + sorted(data_df["PrimaryVendorName"].unique().tolist())
                        )
                    else:
                        vendor_filter = "All"
                        st.warning("'PrimaryVendorName' column not found in data")
                    
                    status_filter = st.selectbox(
                        "Filter by Status",
                        options=["All", "Completed", "Pending"]
                    )
                    
                    # Apply filters
                    filtered_df = data_df.copy()
                    
                    if vendor_filter != "All" and 'PrimaryVendorName' in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df["PrimaryVendorName"] == vendor_filter]
                        
                    if status_filter != "All":
                        if status_filter == "Completed":
                            filtered_df = filtered_df[filtered_df["HTSCode"].notna() & (filtered_df["HTSCode"] != "")]
                        else:  # Pending
                            filtered_df = filtered_df[(filtered_df["HTSCode"].isna()) | (filtered_df["HTSCode"] == "")]
                    
                    # Display data
                    st.dataframe(filtered_df, use_container_width=True)
                    
                    # Stats
                    total = len(filtered_df)
                    completed = len(filtered_df[filtered_df["HTSCode"].notna() & (filtered_df["HTSCode"] != "")])
                    pending = total - completed
                    
                    st.text(f"Total: {total} products, Completed: {completed}, Pending: {pending}")
            else:
                st.error("Unable to load product data. Please check your Google Sheet configuration.")
    
    # Vendors Tab
    with tab2:
        st.header("Vendor Management")
        
        # Check Google Sheets connection
        if not st.session_state.google_connected:
            st.error(f"Error connecting to Google Sheets: {st.session_state.connection_error}")
            st.info("Connect to Google Sheets to manage vendors.")
        else:
            # Ensure Vendors worksheet exists
            if ensure_vendors_worksheet_exists():
                # Add new vendor
                with st.form("add_vendor_form"):
                    st.subheader("Add New Vendor")
                    
                    vendor_id = st.text_input("Vendor ID (must match PrimaryVendorNumber in product sheet)")
                    vendor_name = st.text_input("Vendor Name")
                    vendor_email = st.text_input("Vendor Email")
                    
                    submit_button = st.form_submit_button("Add Vendor")
                    
                    if submit_button:
                        if not vendor_id or not vendor_name:
                            st.error("Vendor ID and Name are required")
                        else:
                            # Try to load vendors from sheet
                            vendors_df = load_sheet_data("Vendors")
                            
                            if vendors_df is not None:
                                if 'VendorID' in vendors_df.columns and vendor_id in vendors_df["VendorID"].values:
                                    st.error(f"Vendor ID '{vendor_id}' already exists")
                                else:
                                    # Add new vendor to sheet
                                    try:
                                        client = get_google_sheets_connection()
                                        spreadsheet = client.open(st.secrets["spreadsheet_name"])
                                        vendors_sheet = spreadsheet.worksheet("Vendors")
                                        vendors_sheet.append_row([vendor_id, vendor_name, vendor_email])
                                        st.success("Vendor added successfully")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error adding vendor: {e}")
                
                # Display vendors
                vendors_df = load_sheet_data("Vendors")
                
                if vendors_df is not None and not vendors_df.empty and 'VendorID' in vendors_df.columns:
                    st.subheader("Current Vendors")
                    
                    for _, row in vendors_df.iterrows():
                        with st.expander(f"{row['VendorName']} ({row['VendorID']})"):
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                st.text(f"Email: {row.get('Email', 'N/A')}")
                                
                                # Generate vendor link
                                base_url = st.secrets.get("base_url", "http://localhost:8501")
                                vendor_link = f"{base_url}/?vendor={row['VendorID']}"
                                st.text("Vendor Link:")
                                st.code(vendor_link)
                                
                                # Product stats
                                data_df = load_sheet_data("Sheet1")
                                if data_df is not None and not data_df.empty and 'PrimaryVendorNumber' in data_df.columns:
                                    vendor_products = data_df[data_df["PrimaryVendorNumber"] == row['VendorID']]
                                    
                                    total = len(vendor_products)
                                    if 'HTSCode' in vendor_products.columns:
                                        completed = len(vendor_products[vendor_products["HTSCode"].notna() & (vendor_products["HTSCode"] != "")])
                                        pending = total - completed
                                    else:
                                        completed = 0
                                        pending = total
                                    
                                    st.text(f"Products: {total} total, {completed} completed, {pending} pending")
                else:
                    st.info("No vendors found. Add some vendors to get started.")
            else:
                st.error("Unable to access or create Vendors worksheet.")
    
    # Data Export Tab
    with tab3:
        st.header("Data Export")
        
        # Check Google Sheets connection
        if not st.session_state.google_connected:
            st.error(f"Error connecting to Google Sheets: {st.session_state.connection_error}")
            st.info("Connect to Google Sheets to export data.")
        else:
            # Load data
            data_df = load_sheet_data("Sheet1")
            
            if data_df is not None and not data_df.empty:
                # Filter options
                if 'PrimaryVendorName' in data_df.columns:
                    export_vendor = st.selectbox(
                        "Vendor", 
                        options=["All"] + sorted(data_df["PrimaryVendorName"].unique().tolist()),
                        key="export_vendor"
                    )
                else:
                    export_vendor = "All"
                    st.warning("'PrimaryVendorName' column not found in data")
                
                status_filter = st.selectbox(
                    "Status",
                    options=["All", "Completed", "Pending"],
                    key="export_status"
                )
                
                # Apply filters
                export_df = data_df.copy()
                
                if export_vendor != "All" and 'PrimaryVendorName' in export_df.columns:
                    export_df = export_df[export_df["PrimaryVendorName"] == export_vendor]
                    
                if status_filter != "All" and 'HTSCode' in export_df.columns:
                    if status_filter == "Completed":
                        export_df = export_df[export_df["HTSCode"].notna() & (export_df["HTSCode"] != "")]
                    else:  # Pending
                        export_df = export_df[(export_df["HTSCode"].isna()) | (export_df["HTSCode"] == "")]
                
                # Preview
                st.dataframe(export_df, use_container_width=True)
                
                # Export options
                st.subheader("Export Options")
                
                if st.button("Download CSV"):
                    csv = export_df.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        label="Download Data as CSV",
                        data=csv,
                        file_name=f"product_data_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                    )
            else:
                st.info("No product data available for export.")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.current_vendor = None
        st.rerun()

# Vendor Dashboard
def vendor_dashboard(vendor_id):
    st.title(f"Welcome, Vendor #{vendor_id}")
    st.subheader("Product Country of Origin and HTS Code Data Collection")
    
    # Check Google Sheets connection
    if not st.session_state.google_connected:
        st.error(f"Error connecting to Google Sheets: {st.session_state.connection_error}")
        st.info("Connect to Google Sheets to view your products.")
        
        # Logout button
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.current_vendor = None
            st.rerun()
    else:
        # Load product data
        data_df = load_sheet_data("Sheet1")
        
        if data_df is not None and not data_df.empty and 'PrimaryVendorNumber' in data_df.columns:
            # Filter products for this vendor
            vendor_products = data_df[data_df["PrimaryVendorNumber"] == vendor_id]
            
            if vendor_products.empty:
                st.warning(f"No products found for vendor ID: {vendor_id}")
            else:
                # Count total and completed products
                total_products = len(vendor_products)
                
                if 'HTSCode' in vendor_products.columns:
                    completed_products = len(vendor_products[vendor_products["HTSCode"].notna() & (vendor_products["HTSCode"] != "")])
                else:
                    completed_products = 0
                
                # Progress bar
                progress = completed_products / total_products if total_products > 0 else 0
                st.progress(progress)
                st.text(f"Completed: {completed_products}/{total_products} products ({int(progress*100)}%)")
                
                # Display products
                st.subheader("Your Products")
                
                for i, (_, product) in enumerate(vendor_products.iterrows()):
                    with st.expander(f"{product.get('ProductName', f'Product {i+1}')} (SKU: {product.get('SKUID', 'N/A')})"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.text(f"SKU: {product.get('SKUID', 'N/A')}")
                            st.text(f"Item #: {product.get('PIMItemNumber', 'N/A')}")
                            if 'Taxonomy' in product:
                                st.text(f"Category: {product.get('Taxonomy', 'N/A')}")
                        
                        col3, col4 = st.columns(2)
                        
                        with col3:
                            # Country selection
                            current_country = product.get('CountryOfOrigin', '')
                            country = st.selectbox(
                                "Country of Origin",
                                options=[""] + COUNTRY_OPTIONS,
                                index=0 if not current_country or current_country not in COUNTRY_OPTIONS else COUNTRY_OPTIONS.index(current_country) + 1,
                                key=f"country_{i}",
                            )
                        
                        with col4:
                            # HTS Code input
                            current_hts = str(product.get('HTSCode', '')) if not pd.isna(product.get('HTSCode', '')) else ''
                            hts_code = st.text_input(
                                "HTS Code (6 or 10 digits)",
                                value=current_hts,
                                key=f"hts_{i}",
                                help="Enter 6 or 10 digits. If you enter 6 digits, '0000' will be added automatically."
                            )
                            
                            # Validate HTS code
                            if hts_code:
                                is_valid, result = validate_hts_code(hts_code)
                                if not is_valid:
                                    st.error(result)
                                else:
                                    hts_code = result
                        
                        # Save button for individual product
                        if st.button("Save", key=f"save_{i}"):
                            if not country:
                                st.error("Please select a Country of Origin")
                            elif not hts_code:
                                st.error("Please enter an HTS Code")
                            else:
                                # Update product data
                                if update_product_data(vendor_id, product.get('SKUID'), country, hts_code):
                                    st.success("Product updated successfully")
                                    # Rerun to refresh data
                                    st.rerun()
                                else:
                                    st.error("Error updating product data")
        else:
            st.error("Unable to load product data or no products found for your vendor ID")
        
        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.current_vendor = None
            st.rerun()

# Main app logic
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.is_admin:
            admin_dashboard()
        else:
            vendor_dashboard(st.session_state.current_vendor)

if __name__ == "__main__":
    main()