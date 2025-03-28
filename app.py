import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Page configuration
st.set_page_config(
    page_title="Product Data Collection",
    page_icon="🌍",
    layout="wide"
)

# Define Google API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None

# Function to connect to Google Sheets API
def get_google_sheets_connection():
    try:
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

# Function to load data from Google Sheet
def load_sheet_data(sheet_name="Sheet1"):
    try:
        client = get_google_sheets_connection()
        if not client:
            return None
            
        # Open the spreadsheet
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        
        # Get the worksheet
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Convert to dataframe
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Login page
def login_page():
    st.title("Product Data Collection")
    
    st.write("Please login to continue.")
    
    # Create two columns for login options
    left_column, right_column = st.columns(2)
    
    # Vendor login
    with left_column:
        st.subheader("Vendor Login")
        
        # Check URL parameters
        query_params = st.query_params
        if "vendor" in query_params:
            vendor_id = query_params["vendor"]
            st.success(f"Vendor ID detected: {vendor_id}")
            
            # Verify vendor ID
            try:
                vendors_df = load_sheet_data("Vendors")
                if vendors_df is not None and vendor_id in vendors_df['VendorID'].values:
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_vendor = vendor_id
                    st.rerun()  # Fixed: Using st.rerun() instead of st.experimental_rerun()
                else:
                    st.error("Invalid vendor ID. Please contact the administrator.")
            except:
                st.warning("Could not verify vendor ID. Please try manual login.")
        
        # Manual vendor login
        vendor_id = st.text_input("Vendor ID")
        vendor_login = st.button("Login as Vendor")
        
        if vendor_login:
            if not vendor_id:
                st.error("Please enter your Vendor ID")
            else:
                try:
                    vendors_df = load_sheet_data("Vendors")
                    if vendors_df is not None and vendor_id in vendors_df['VendorID'].values:
                        st.session_state.logged_in = True
                        st.session_state.is_admin = False
                        st.session_state.current_vendor = vendor_id
                        st.rerun()  # Fixed: Using st.rerun() instead of st.experimental_rerun()
                    else:
                        st.error("Invalid Vendor ID")
                except Exception as e:
                    st.error(f"Error during login: {e}")
    
    # Admin login
    with right_column:
        st.subheader("Admin Login")
        
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
                    st.rerun()  # Fixed: Using st.rerun() instead of st.experimental_rerun()
                else:
                    st.error("Invalid admin password")

# Simple admin dashboard
def admin_dashboard():
    st.title("Admin Dashboard")
    
    st.success("You are logged in as an administrator")
    
    # Test connection to Google Sheets
    st.subheader("Google Sheets Connection Test")
    
    if st.button("Test Connection"):
        client = get_google_sheets_connection()
        if client:
            try:
                # Try to open the spreadsheet
                spreadsheet = client.open(st.secrets["spreadsheet_name"])
                st.success(f"Successfully connected to spreadsheet: {st.secrets.spreadsheet_name}")
                
                # List all worksheets
                worksheet_list = spreadsheet.worksheets()
                st.write(f"Available worksheets: {[ws.title for ws in worksheet_list]}")
                
                # Try to read data from the first worksheet
                sheet1 = spreadsheet.sheet1
                data = sheet1.get_all_records()
                
                if data:
                    st.success(f"Successfully read {len(data)} rows from the first worksheet")
                    st.write("Sample data (first 5 rows):")
                    st.dataframe(pd.DataFrame(data).head())
                else:
                    st.warning("The sheet exists but contains no data")
            except Exception as e:
                st.error(f"Error accessing spreadsheet: {e}")
        else:
            st.error("Failed to connect to Google Sheets API")
    
    # Logout button
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.current_vendor = None
        st.rerun()  # Fixed: Using st.rerun() instead of st.experimental_rerun()

# Simple vendor dashboard
def vendor_dashboard(vendor_id):
    st.title(f"Vendor Dashboard: {vendor_id}")
    
    st.success(f"You are logged in as vendor: {vendor_id}")
    
    # Try to load vendor-specific products
    try:
        data_df = load_sheet_data()
        if data_df is not None:
            vendor_products = data_df[data_df["PrimaryVendorNumber"] == vendor_id]
            
            if not vendor_products.empty:
                st.write(f"Found {len(vendor_products)} products for your vendor ID")
                st.dataframe(vendor_products)
            else:
                st.warning(f"No products found for vendor ID: {vendor_id}")
        else:
            st.error("Could not load product data")
    except Exception as e:
        st.error(f"Error loading vendor products: {e}")
    
    # Logout button
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_vendor = None
        st.rerun()  # Fixed: Using st.rerun() instead of st.experimental_rerun()

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