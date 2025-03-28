import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import uuid
import datetime
import pycountry

# Set page config
st.set_page_config(
    page_title="Product Origin Data Collection",
    page_icon="🌍",
    layout="wide"
)

# Define scope for Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Generate country options with ISO codes for all countries
def get_country_options():
    country_list = []
    for country in pycountry.countries:
        # Format as "US - United States"
        country_list.append(f"{country.alpha_2} - {country.name}")
    return sorted(country_list)

# Initialize country options
COUNTRY_OPTIONS = get_country_options()

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None

# Function to connect to Google Sheets
@st.cache_resource
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
@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_sheet_data(sheet_name="Sheet1"):
    try:
        client = get_google_sheets_connection()
        if not client:
            return None
            
        # Open the spreadsheet by its name (use URL if preferred)
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        
        # Get the specified worksheet
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Convert to dataframe
        df = get_as_dataframe(worksheet, evaluate_formulas=True, skiprows=0)
        
        # Clean up dataframe (remove empty rows)
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Function to update Google Sheet with vendor submissions
def update_sheet_with_submissions(vendor_id, submissions):
    try:
        client = get_google_sheets_connection()
        if not client:
            return False
            
        # Open the spreadsheet
        spreadsheet = client.open(st.secrets["spreadsheet_name"])
        
        # Get the main data worksheet
        worksheet = spreadsheet.worksheet("Sheet1")
        
        # Get all data
        df = get_as_dataframe(worksheet)
        
        # Update the matching rows with submission data
        for sku, data in submissions.items():
            # Find row with matching SKU
            idx = df.index[df['SKUID'] == sku].tolist()
            if idx:
                row_idx = idx[0]
                df.at[row_idx, 'CountryOfOrigin'] = data['country']
                df.at[row_idx, 'HTSCode'] = data['hts_code']
                df.at[row_idx, 'LastUpdated'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save back to the worksheet
        set_with_dataframe(worksheet, df)
        
        # Log submission in a separate sheet
        try:
            log_sheet = spreadsheet.worksheet("SubmissionLog")
        except:
            # Create log sheet if it doesn't exist
            log_sheet = spreadsheet.add_worksheet(title="SubmissionLog", rows=1000, cols=5)
            log_sheet.append_row(["Timestamp", "VendorID", "SKU", "CountryOfOrigin", "HTSCode"])
        
        # Log each submission
        for sku, data in submissions.items():
            log_sheet.append_row([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                vendor_id,
                sku,
                data['country'],
                data['hts_code']
            ])
        
        return True
    except Exception as e:
        st.error(f"Error updating data: {e}")
        return False

# Function to validate HTS code
def validate_hts_code(code):
    # Remove any non-numeric characters
    code = ''.join(filter(str.isdigit, code))
    
    # Check if it's 10 digits
    if len(code) == 10:
        return True, code
    # Check if it's 6 digits (auto-expand to 10)
    elif len(code) == 6:
        return True, code + "0000"
    else:
        return False, "HTS code must be 6 or 10 digits"

# Authentication
def login_page():
    st.title("🌍 Product Country of Origin Data Collection")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Vendor Login")
        st.info("If you're a vendor, please use the link provided to you by email.")
        
        # Check if URL contains vendor param
        query_params = st.query_params
        if "vendor" in query_params:
            vendor_id = query_params["vendor"]
            
            # Load vendor data from sheet
            vendors_df = load_sheet_data("Vendors")
            if vendors_df is not None and vendor_id in vendors_df['VendorID'].values:
                st.session_state.logged_in = True
                st.session_state.is_admin = False
                st.session_state.current_vendor = vendor_id
                st.rerun()
        
        # Manual vendor login (backup)
        vendor_id = st.text_input("Vendor ID")
        
        if st.button("Login as Vendor"):
            vendors_df = load_sheet_data("Vendors")
            if vendors_df is not None and vendor_id in vendors_df['VendorID'].values:
                st.session_state.logged_in = True
                st.session_state.is_admin = False
                st.session_state.current_vendor = vendor_id
                st.rerun()
            else:
                st.error("Vendor ID not found")
    
    with col2:
        st.subheader("Admin Login")
        st.info("For admin access to manage products and vendors.")
        
        admin_password = st.text_input("Admin Password", type="password")
        
        if st.button("Login as Admin"):
            # Get admin password from secrets
            correct_password = st.secrets.get("admin_password", "admin123")
            
            if admin_password == correct_password:
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
        
        # Load product data
        data_df = load_sheet_data()
        
        if data_df is not None:
            # Add CountryOfOrigin and HTSCode columns if they don't exist
            if 'CountryOfOrigin' not in data_df.columns:
                data_df['CountryOfOrigin'] = ""
            
            if 'HTSCode' not in data_df.columns:
                data_df['HTSCode'] = ""
            
            if 'LastUpdated' not in data_df.columns:
                data_df['LastUpdated'] = ""
            
            # Filter options
            vendor_filter = st.selectbox(
                "Filter by Vendor", 
                options=["All"] + sorted(data_df["PrimaryVendorName"].unique().tolist())
            )
            
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "Completed", "Pending"]
            )
            
            # Apply filters
            filtered_df = data_df.copy()
            
            if vendor_filter != "All":
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
        
        # Load vendors data
        try:
            vendors_df = load_sheet_data("Vendors")
        except:
            # Create a sample vendors dataframe if it doesn't exist
            vendors_df = pd.DataFrame(columns=["VendorID", "VendorName", "Email"])
        
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
                elif vendors_df is not None and vendor_id in vendors_df["VendorID"].values:
                    st.error(f"Vendor ID '{vendor_id}' already exists")
                else:
                    # Add new vendor to dataframe
                    new_vendor = pd.DataFrame({
                        "VendorID": [vendor_id],
                        "VendorName": [vendor_name],
                        "Email": [vendor_email]
                    })
                    
                    # Update the vendors worksheet
                    try:
                        client = get_google_sheets_connection()
                        spreadsheet = client.open(st.secrets["spreadsheet_name"])
                        
                        # Check if vendors sheet exists
                        try:
                            vendors_sheet = spreadsheet.worksheet("Vendors")
                        except:
                            # Create vendors sheet if it doesn't exist
                            vendors_sheet = spreadsheet.add_worksheet(title="Vendors", rows=100, cols=5)
                            vendors_sheet.append_row(["VendorID", "VendorName", "Email"])
                        
                        # Add vendor
                        vendors_sheet.append_row([vendor_id, vendor_name, vendor_email])
                        st.success("Vendor added successfully")
                        
                        # Refresh data
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding vendor: {e}")
        
        # Display vendors
        if vendors_df is not None and not vendors_df.empty:
            st.subheader("Current Vendors")
            
            for i, row in vendors_df.iterrows():
                with st.expander(f"{row['VendorName']} ({row['VendorID']})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.text(f"Email: {row['Email']}")
                        
                        # Generate vendor link
                        base_url = st.secrets.get("base_url", st.experimental_get_query_params().get("_streamlit_url", ["http://localhost:8501"])[0])
                        vendor_link = f"{base_url}/?vendor={row['VendorID']}"
                        st.text("Vendor Link:")
                        st.code(vendor_link)
                        
                        # Product stats
                        if data_df is not None:
                            vendor_products = data_df[data_df["PrimaryVendorNumber"] == row['VendorID']]
                            
                            total = len(vendor_products)
                            completed = len(vendor_products[vendor_products["HTSCode"].notna() & (vendor_products["HTSCode"] != "")])
                            pending = total - completed
                            
                            st.text(f"Products: {total} total, {completed} completed, {pending} pending")
        else:
            st.info("No vendors in the database. Add some vendors to get started.")
    
    # Data Export Tab
    with tab3:
        st.header("Data Export")
        
        data_df = load_sheet_data()
        
        if data_df is not None:
            # Filter options
            export_vendor = st.selectbox(
                "Vendor", 
                options=["All"] + sorted(data_df["PrimaryVendorName"].unique().tolist()),
                key="export_vendor"
            )
            
            export_status = st.selectbox(
                "Status",
                options=["All", "Completed", "Pending"],
                key="export_status"
            )
            
            # Apply filters
            export_df = data_df.copy()
            
            if export_vendor != "All":
                export_df = export_df[export_df["PrimaryVendorName"] == export_vendor]
                
            if export_status != "All":
                if export_status == "Completed":
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
            st.error("Unable to load product data. Please check your Google Sheet configuration.")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.current_vendor = None
        st.rerun()

# Vendor Dashboard
def vendor_dashboard(vendor_id):
    # Load vendor data
    vendors_df = load_sheet_data("Vendors")
    if vendors_df is not None and vendor_id in vendors_df["VendorID"].values:
        vendor_data = vendors_df[vendors_df["VendorID"] == vendor_id].iloc[0]
        vendor_name = vendor_data["VendorName"]
    else:
        vendor_name = vendor_id
    
    st.title(f"Welcome, {vendor_name}")
    st.subheader("Product Country of Origin Data Collection")
    
    # Load product data
    data_df = load_sheet_data()
    
    # Filter products for this vendor
    if data_df is not None:
        vendor_products = data_df[data_df["PrimaryVendorNumber"] == vendor_id]
        
        if vendor_products.empty:
            st.warning(f"No products assigned to vendor ID: {vendor_id}")
        else:
            # Count total and completed products
            total_products = len(vendor_products)
            completed_products = len(vendor_products[vendor_products["HTSCode"].notna() & (vendor_products["HTSCode"] != "")])
            
            # Progress bar
            if total_products > 0:
                progress = completed_products / total_products
                st.progress(progress)
                st.text(f"Completed: {completed_products}/{total_products} products ({int(progress*100)}%)")
            
            # Create form for submission
            with st.form("product_submission_form"):
                st.subheader("Enter Country of Origin and HTS Code")
                st.markdown("""
                **Instructions:**
                - Select the country of origin for each product
                - Enter the HTS Code (Harmonized Tariff Schedule) code:
                  - Must be a 10-digit numeric code
                  - If you only have the first 6 digits, enter those and the system will add "0000" to the end
                """)
                
                # Track submissions for batch update
                submissions = {}
                has_errors = False
                
                # Create form fields for each product
                for i, (_, product) in enumerate(vendor_products.iterrows()):
                    st.markdown(f"### {product['ProductName']}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.text(f"SKU: {product['SKUID']}")
                        st.text(f"Item #: {product['PIMItemNumber']}")
                        if 'Taxonomy' in product:
                            st.text(f"Category: {product['Taxonomy']}")
                    
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        # Country selection with search
                        current_country = product.get('CountryOfOrigin', '')
                        country = st.selectbox(
                            "Country of Origin",
                            options=COUNTRY_OPTIONS,
                            index=COUNTRY_OPTIONS.index(current_country) if current_country in COUNTRY_OPTIONS else 0,
                            key=f"country_{i}",
                            placeholder="Search for a country...",
                        )
                    
                    with col4:
                        # HTS Code input with validation
                        current_hts = str(product.get('HTSCode', '')) if not pd.isna(product.get('HTSCode', '')) else ''
                        hts_code = st.text_input(
                            "HTS Code (6 or 10 digits)",
                            value=current_hts,
                            key=f"hts_{i}",
                            placeholder="Enter 6 or 10 digit code",
                            help="Enter 6 or 10 digits. If you enter 6 digits, '0000' will be added automatically."
                        )
                        
                        # Validate HTS code format
                        if hts_code:
                            is_valid, result = validate_hts_code(hts_code)
                            if not is_valid:
                                st.error(result)
                                has_errors = True
                            else:
                                hts_code = result  # Use the formatted result
                        
                    # Store valid submissions
                    if country and hts_code and not has_errors:
                        submissions[product['SKUID']] = {
                            'country': country,
                            'hts_code': hts_code
                        }
                    
                    st.markdown("---")
                
                submitted = st.form_submit_button("Submit Data")
                
                if submitted:
                    if has_errors:
                        st.error("Please fix the HTS code errors before submitting")
                    elif not submissions:
                        st.warning("Please complete at least one product before submitting")
                    else:
                        # Update the sheet
                        success = update_sheet_with_submissions(vendor_id, submissions)
                        
                        if success:
                            st.success("Data submitted successfully!")
                            st.balloons()
                            
                            # Force refresh of data
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Error submitting data. Please try again.")
    else:
        st.error("Unable to load product data. Please contact the administrator.")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_vendor = None
        st.rerun()

# Main app
def main():
    # Add some styling
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 {
        color: #1E88E5;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check login state
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.is_admin:
            admin_dashboard()
        else:
            vendor_dashboard(st.session_state.current_vendor)

if __name__ == "__main__":
    main()