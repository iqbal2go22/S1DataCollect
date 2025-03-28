import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import json

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
    "FR - France"
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

# Function to connect to Google Sheets API with detailed debug info
def get_google_sheets_connection():
    try:
        st.write("Attempting to connect to Google Sheets...")
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        
        # Debug output for credentials (with sensitive info masked)
        cred_dict = credentials.__dict__.copy()
        if "_private_key_id" in cred_dict:
            cred_dict["_private_key_id"] = cred_dict["_private_key_id"][:5] + "..."
        if "_private_key" in cred_dict:
            cred_dict["_private_key"] = "***PRIVATE KEY HIDDEN***"
        
        st.write("Credentials created successfully:")
        st.json(json.dumps({k: str(v) for k, v in cred_dict.items() if not k.startswith("_")}))
        
        client = gspread.authorize(credentials)
        st.write("✅ Google authentication successful")
        
        st.session_state.google_connected = True
        st.session_state.connection_error = None
        return client
    except Exception as e:
        st.session_state.google_connected = False
        st.session_state.connection_error = str(e)
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

# Function to test spreadsheet access with detailed error info
def test_spreadsheet_access():
    try:
        client = get_google_sheets_connection()
        if not client:
            return False, "Failed to connect to Google Sheets API"
            
        # Try to open the spreadsheet
        sheet_name = st.secrets["spreadsheet_name"]
        st.write(f"Attempting to open spreadsheet: '{sheet_name}'")
        
        try:
            # Try to open by name first
            spreadsheet = client.open(sheet_name)
            st.write(f"✅ Successfully opened spreadsheet by name: {sheet_name}")
        except gspread.exceptions.SpreadsheetNotFound:
            # If not found by name, display all available spreadsheets
            st.warning(f"Spreadsheet '{sheet_name}' not found by name")
            
            all_sheets = client.openall()
            if all_sheets:
                st.write("Available spreadsheets:")
                for sheet in all_sheets:
                    st.write(f"- {sheet.title}")
                return False, f"Spreadsheet '{sheet_name}' not found. Please check the name in your secrets configuration."
            else:
                st.warning("No spreadsheets available to this service account")
                return False, "No spreadsheets are shared with this service account. Please share your spreadsheet with the service account email."
        
        # List all worksheets in the spreadsheet
        worksheets = spreadsheet.worksheets()
        st.write(f"Worksheets in spreadsheet:")
        for worksheet in worksheets:
            st.write(f"- {worksheet.title}")
        
        # Try to access Sheet1
        try:
            worksheet = spreadsheet.worksheet("Sheet1")
            st.write("✅ Successfully accessed Sheet1")
            
            # Get basic info about Sheet1
            rows = worksheet.row_count
            cols = worksheet.col_count
            st.write(f"Sheet1 dimensions: {rows} rows x {cols} columns")
            
            # Try to read data
            data = worksheet.get_all_records()
            st.write(f"✅ Successfully read data: {len(data)} records")
            
            if not data:
                st.warning("Sheet1 exists but contains no data or no header row")
                return True, "Sheet exists but contains no data. Please add headers and data to your spreadsheet."
                
            # Show column headers
            headers = worksheet.row_values(1)
            st.write("Column headers:", headers)
            
            # Verify required columns
            required_cols = ["SKUID", "PrimaryVendorNumber", "ProductName"]
            missing_cols = [col for col in required_cols if col not in headers]
            
            if missing_cols:
                st.warning(f"Missing required columns: {', '.join(missing_cols)}")
                return True, f"Spreadsheet is accessible but missing required columns: {', '.join(missing_cols)}"
            
            return True, "Spreadsheet accessed successfully"
        except gspread.exceptions.WorksheetNotFound:
            st.warning("Sheet1 not found in spreadsheet")
            return False, "Sheet1 not found in spreadsheet. Please rename your main worksheet to 'Sheet1' or modify the code to use your worksheet name."
    except Exception as e:
        st.error(f"Error testing spreadsheet access: {e}")
        return False, str(e)

# Login page with spreadsheet testing
def login_page():
    st.title("🌍 Product Origin Data Collection")
    
    # Test spreadsheet access button
    if st.button("Test Google Sheets Connection"):
        success, message = test_spreadsheet_access()
        if success:
            st.success(message)
        else:
            st.error(message)
    
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
            st.write(f"Detected Vendor ID: {vendor_id}")
            
            # Simple login for now
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
    
    # Big button for testing Google Sheets connection
    if st.button("Test Google Sheets Connection", key="test_admin"):
        success, message = test_spreadsheet_access()
        if success:
            st.success(message)
        else:
            st.error(message)
    
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

    # Test Google Sheets Connection button
    if st.button("Test Google Sheets Connection", key="test_vendor"):
        success, message = test_spreadsheet_access()
        if success:
            st.success(message)
        else:
            st.error(message)
            return

    # Load product data from Google Sheets
    try:
        client = get_google_sheets_connection()
        if not client:
            st.error("Failed to connect to Google Sheets")
            return

        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        worksheet = spreadsheet.worksheet("Sheet1")
        data = worksheet.get_all_records()
        if not data:
            st.warning("Sheet1 exists but contains no data.")
            return

        df = pd.DataFrame(data)

        # Display raw sheet data (for debugging)
        st.write("📋 Raw Sheet1 Data (first 5 rows):")
        st.dataframe(df.head())

        # Normalize the vendor ID
        vendor_id = vendor_id.strip().upper()

        # Normalize column values
        if "PrimaryVendorNumber" not in df.columns:
            st.error("Missing 'PrimaryVendorNumber' column in Sheet1.")
            return

        df["PrimaryVendorNumber"] = df["PrimaryVendorNumber"].astype(str).str.strip().str.upper()

        # Filter rows for this vendor
        vendor_df = df[df["PrimaryVendorNumber"] == vendor_id]

        if vendor_df.empty:
            st.warning(f"No products found for Vendor ID '{vendor_id}'. Please ensure it's listed in the spreadsheet.")
            return

        st.success(f"✅ Loaded {len(vendor_df)} product(s) for Vendor ID '{vendor_id}'")
        st.dataframe(vendor_df)

        # TODO: Add form fields for COO, HTS, etc.

    except Exception as e:
        st.error(f"Error loading data from sheet 'Sheet1': {e}")

    
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