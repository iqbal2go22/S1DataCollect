import streamlit as st
import pandas as pd
import os
import uuid
import datetime
import base64
import json
from pathlib import Path

# Set page config
st.set_page_config(
    page_title="Product Origin Data Collection",
    page_icon="🌍",
    layout="wide"
)

# Define paths for data storage
DATA_DIR = Path("data")
PRODUCTS_FILE = DATA_DIR / "products.csv"
VENDORS_FILE = DATA_DIR / "vendors.csv"
SUBMISSIONS_DIR = DATA_DIR / "submissions"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
SUBMISSIONS_DIR.mkdir(exist_ok=True)

# Country options for dropdown
COUNTRY_OPTIONS = [
    "US - United States", 
    "CA - Canada", 
    "MX - Mexico", 
    "CN - China", 
    "IN - India", 
    "VN - Vietnam", 
    "DE - Germany"
]

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
    
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None

if "vendor_token" not in st.session_state:
    st.session_state.vendor_token = None

# Admin Functions
def save_products_data(df):
    df.to_csv(PRODUCTS_FILE, index=False)
    
def save_vendors_data(df):
    df.to_csv(VENDORS_FILE, index=False)

def load_products_data():
    if PRODUCTS_FILE.exists():
        return pd.read_csv(PRODUCTS_FILE)
    else:
        return pd.DataFrame(columns=[
            "SKU", "ItemNumber", "ProductName", "VendorID", "VendorName", "ImageURL", 
            "CountryOfOrigin", "HTSCode", "Status"
        ])

def load_vendors_data():
    if VENDORS_FILE.exists():
        return pd.read_csv(VENDORS_FILE)
    else:
        return pd.DataFrame(columns=["VendorID", "VendorName", "AccessToken", "Email"])

def generate_access_token():
    return str(uuid.uuid4())

def create_vendor_link(vendor_id, access_token):
    base_url = st.secrets.get("BASE_URL", "http://localhost:8501")
    return f"{base_url}/?vendor={vendor_id}&token={access_token}"

def save_submission(vendor_id, data):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = SUBMISSIONS_DIR / f"{vendor_id}_{timestamp}.json"
    with open(filename, "w") as f:
        json.dump(data, f)
    
    # Update product status in main dataframe
    products_df = load_products_data()
    for sku, entry in data.items():
        if sku in products_df["SKU"].values:
            products_df.loc[products_df["SKU"] == sku, "CountryOfOrigin"] = entry.get("CountryOfOrigin", "")
            products_df.loc[products_df["SKU"] == sku, "HTSCode"] = entry.get("HTSCode", "")
            products_df.loc[products_df["SKU"] == sku, "Status"] = "Completed"
    
    save_products_data(products_df)

def get_vendor_products(vendor_id):
    products_df = load_products_data()
    return products_df[products_df["VendorID"] == vendor_id]

def validate_hts_code(code):
    if not code:
        return True, ""
    
    # Remove non-numeric characters
    code = ''.join(filter(str.isdigit, code))
    
    # Check if it's 6 or 10 digits
    if len(code) == 6:
        return True, code + "0000"  # Auto-expand to 10 digits
    elif len(code) == 10:
        return True, code
    else:
        return False, "HTS code must be 6 or 10 digits"

def get_download_link(df, filename, text):
    """Generate a download link for the dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 {text}</a>'
    return href

# Authentication
def login_page():
    st.title("🌍 Product Country of Origin Data Collection")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Vendor Login")
        st.info("If you're a vendor, please use the link provided to you by email.")
        
        # Check if URL contains vendor and token params
        query_params = st.query_params
        if "vendor" in query_params and "token" in query_params:
            vendor_id = query_params["vendor"]
            token = query_params["token"]
            
            vendors_df = load_vendors_data()
            if vendor_id in vendors_df["VendorID"].values:
                vendor_row = vendors_df[vendors_df["VendorID"] == vendor_id].iloc[0]
                if vendor_row["AccessToken"] == token:
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_vendor = vendor_id
                    st.session_state.vendor_token = token
                    st.rerun()
        
        # Manual vendor login (backup)
        vendor_id = st.text_input("Vendor ID")
        vendor_token = st.text_input("Access Token", type="password")
        
        if st.button("Login as Vendor"):
            vendors_df = load_vendors_data()
            if vendor_id in vendors_df["VendorID"].values:
                vendor_row = vendors_df[vendors_df["VendorID"] == vendor_id].iloc[0]
                if vendor_row["AccessToken"] == vendor_token:
                    st.session_state.logged_in = True
                    st.session_state.is_admin = False
                    st.session_state.current_vendor = vendor_id
                    st.session_state.vendor_token = vendor_token
                    st.rerun()
                else:
                    st.error("Invalid access token")
            else:
                st.error("Vendor ID not found")
    
    with col2:
        st.subheader("Admin Login")
        st.info("For admin access to manage products and vendors.")
        
        admin_password = st.text_input("Admin Password", type="password")
        
        if st.button("Login as Admin"):
            # Very simple authentication - in production use proper auth
            correct_password = st.secrets.get("ADMIN_PASSWORD", "admin123")  # Set in secrets.toml
            
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
        
        products_df = load_products_data()
        
        # Upload new products
        st.subheader("Upload Products")
        uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    new_products = pd.read_csv(uploaded_file)
                else:
                    new_products = pd.read_excel(uploaded_file)
                
                required_columns = ["SKU", "ItemNumber", "ProductName", "VendorID", "VendorName"]
                missing_columns = [col for col in required_columns if col not in new_products.columns]
                
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                else:
                    # Initialize columns if they don't exist
                    for col in ["ImageURL", "CountryOfOrigin", "HTSCode", "Status"]:
                        if col not in new_products.columns:
                            new_products[col] = ""
                    
                    # Set initial status
                    new_products["Status"] = "Pending"
                    
                    # Check if vendors exist, create if not
                    vendors_df = load_vendors_data()
                    new_vendors = []
                    
                    for _, row in new_products[["VendorID", "VendorName"]].drop_duplicates().iterrows():
                        if row["VendorID"] not in vendors_df["VendorID"].values:
                            access_token = generate_access_token()
                            new_vendors.append({
                                "VendorID": row["VendorID"],
                                "VendorName": row["VendorName"],
                                "AccessToken": access_token,
                                "Email": ""
                            })
                    
                    if new_vendors:
                        new_vendors_df = pd.DataFrame(new_vendors)
                        vendors_df = pd.concat([vendors_df, new_vendors_df], ignore_index=True)
                        save_vendors_data(vendors_df)
                        st.success(f"Added {len(new_vendors)} new vendors")
                    
                    # Merge with existing products (update if exists)
                    if not products_df.empty:
                        # Remove existing SKUs that match the new products
                        products_df = products_df[~products_df["SKU"].isin(new_products["SKU"])]
                    
                    # Combine old and new products
                    products_df = pd.concat([products_df, new_products], ignore_index=True)
                    save_products_data(products_df)
                    
                    st.success(f"Successfully uploaded {len(new_products)} products")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
        
        # Display products
        st.subheader("Current Products")
        
        if not products_df.empty:
            # Filter options
            vendor_filter = st.selectbox(
                "Filter by Vendor", 
                options=["All"] + products_df["VendorName"].unique().tolist()
            )
            
            status_filter = st.selectbox(
                "Filter by Status",
                options=["All", "Pending", "Completed"]
            )
            
            # Apply filters
            filtered_df = products_df.copy()
            
            if vendor_filter != "All":
                filtered_df = filtered_df[filtered_df["VendorName"] == vendor_filter]
                
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df["Status"] == status_filter]
            
            # Display data
            st.dataframe(filtered_df, use_container_width=True)
            
            # Stats
            total = len(filtered_df)
            completed = len(filtered_df[filtered_df["Status"] == "Completed"])
            pending = total - completed
            
            st.text(f"Total: {total} products, Completed: {completed}, Pending: {pending}")
        else:
            st.info("No products in the database. Upload some products to get started.")
    
    # Vendors Tab
    with tab2:
        st.header("Vendor Management")
        
        vendors_df = load_vendors_data()
        
        # Add new vendor manually
        st.subheader("Add New Vendor")
        
        with st.form("add_vendor_form"):
            vendor_id = st.text_input("Vendor ID (unique identifier)")
            vendor_name = st.text_input("Vendor Name")
            vendor_email = st.text_input("Vendor Email")
            
            submit_button = st.form_submit_button("Add Vendor")
            
            if submit_button:
                if not vendor_id or not vendor_name:
                    st.error("Vendor ID and Name are required")
                elif vendor_id in vendors_df["VendorID"].values:
                    st.error(f"Vendor ID '{vendor_id}' already exists")
                else:
                    access_token = generate_access_token()
                    new_vendor = pd.DataFrame([{
                        "VendorID": vendor_id,
                        "VendorName": vendor_name,
                        "AccessToken": access_token,
                        "Email": vendor_email
                    }])
                    
                    vendors_df = pd.concat([vendors_df, new_vendor], ignore_index=True)
                    save_vendors_data(vendors_df)
                    st.success("Vendor added successfully")
        
        # Display vendors
        st.subheader("Current Vendors")
        
        if not vendors_df.empty:
            for i, row in vendors_df.iterrows():
                with st.expander(f"{row['VendorName']} ({row['VendorID']})"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.text(f"Email: {row['Email']}")
                        
                        # Generate vendor link
                        vendor_link = create_vendor_link(row['VendorID'], row['AccessToken'])
                        st.text("Vendor Link:")
                        st.code(vendor_link)
                        
                        # Product stats
                        products_df = load_products_data()
                        vendor_products = products_df[products_df["VendorID"] == row['VendorID']]
                        
                        total = len(vendor_products)
                        completed = len(vendor_products[vendor_products["Status"] == "Completed"])
                        pending = total - completed
                        
                        st.text(f"Products: {total} total, {completed} completed, {pending} pending")
                    
                    with col2:
                        if st.button("Reset Token", key=f"reset_{row['VendorID']}"):
                            new_token = generate_access_token()
                            vendors_df.at[i, "AccessToken"] = new_token
                            save_vendors_data(vendors_df)
                            st.success("Token reset successfully")
                            st.rerun()
                            
                        if st.button("Delete Vendor", key=f"delete_{row['VendorID']}"):
                            # Check if there are any products for this vendor
                            products_df = load_products_data()
                            vendor_products = products_df[products_df["VendorID"] == row['VendorID']]
                            
                            if not vendor_products.empty:
                                st.error("Cannot delete vendor with assigned products")
                            else:
                                vendors_df = vendors_df.drop(i)
                                save_vendors_data(vendors_df)
                                st.success("Vendor deleted successfully")
                                st.rerun()
        else:
            st.info("No vendors in the database. Add some vendors to get started.")
    
    # Data Export Tab
    with tab3:
        st.header("Data Export")
        
        products_df = load_products_data()
        
        if not products_df.empty:
            # Filter options
            export_vendor = st.selectbox(
                "Vendor", 
                options=["All"] + products_df["VendorName"].unique().tolist(),
                key="export_vendor"
            )
            
            export_status = st.selectbox(
                "Status",
                options=["All", "Completed", "Pending"],
                key="export_status"
            )
            
            # Apply filters
            export_df = products_df.copy()
            
            if export_vendor != "All":
                export_df = export_df[export_df["VendorName"] == export_vendor]
                
            if export_status != "All":
                export_df = export_df[export_df["Status"] == export_status]
            
            # Preview
            st.dataframe(export_df, use_container_width=True)
            
            # Export options
            st.subheader("Export Options")
            
            # Generate download link for CSV
            st.markdown(
                get_download_link(export_df, "product_data.csv", "Download as CSV"), 
                unsafe_allow_html=True
            )
            
            # Export JSON
            if st.button("Export as JSON"):
                json_data = export_df.to_json(orient="records")
                b64 = base64.b64encode(json_data.encode()).decode()
                href = f'<a href="data:file/json;base64,{b64}" download="product_data.json">📥 Download JSON</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("No products in the database to export.")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.current_vendor = None
        st.rerun()

# Vendor Dashboard
def vendor_dashboard(vendor_id):
    vendors_df = load_vendors_data()
    vendor_data = vendors_df[vendors_df["VendorID"] == vendor_id].iloc[0]
    vendor_name = vendor_data["VendorName"]
    
    st.title(f"Welcome, {vendor_name}")
    st.subheader("Product Country of Origin Data Collection")
    
    # Get vendor's products
    products_df = get_vendor_products(vendor_id)
    
    if products_df.empty:
        st.warning("No products assigned to your vendor ID.")
    else:
        # Count total and remaining products
        total_products = len(products_df)
        completed_products = len(products_df[products_df["Status"] == "Completed"])
        pending_products = total_products - completed_products
        
        # Progress bar
        progress = completed_products / total_products if total_products > 0 else 0
        st.progress(progress)
        st.text(f"Completed: {completed_products}/{total_products} products ({int(progress*100)}%)")
        
        # Create form for submission
        with st.form("product_submission_form"):
            st.subheader("Enter Country of Origin and HTS Code for your products")
            
            # Track valid entries for submission
            valid_entries = {}
            has_errors = False
            
            # Create form fields for each product
            for i, product in products_df.iterrows():
                st.markdown(f"### Product: {product['ProductName']}")
                st.text(f"SKU: {product['SKU']} | Item Number: {product['ItemNumber']}")
                
                # Display image if available
                if product["ImageURL"] and str(product["ImageURL"]) != "nan":
                    st.image(product["ImageURL"], width=200)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    country = st.selectbox(
                        "Country of Origin",
                        options=[""] + COUNTRY_OPTIONS,
                        key=f"country_{product['SKU']}",
                        index=0 if pd.isna(product["CountryOfOrigin"]) else COUNTRY_OPTIONS.index(product["CountryOfOrigin"])+1 if product["CountryOfOrigin"] in COUNTRY_OPTIONS else 0
                    )
                
                with col2:
                    hts_code = st.text_input(
                        "HTS Code (6 or 10 digits)",
                        key=f"hts_{product['SKU']}",
                        value="" if pd.isna(product["HTSCode"]) else product["HTSCode"]
                    )
                    
                    # Validate HTS code
                    if hts_code:
                        is_valid, formatted_code = validate_hts_code(hts_code)
                        if not is_valid:
                            st.error("HTS code must be 6 or 10 digits")
                            has_errors = True
                        else:
                            hts_code = formatted_code
                
                # Store valid entries
                if country and hts_code:
                    valid_entries[product["SKU"]] = {
                        "ProductName": product["ProductName"],
                        "CountryOfOrigin": country,
                        "HTSCode": hts_code
                    }
                
                st.markdown("---")
            
            submit_button = st.form_submit_button("Submit Data")
            
            if submit_button:
                if has_errors:
                    st.error("Please fix the errors before submitting")
                elif not valid_entries:
                    st.error("Please fill in at least one product before submitting")
                else:
                    # Save submission
                    save_submission(vendor_id, valid_entries)
                    st.success("Data submitted successfully!")
                    st.balloons()
                    
                    # Show submit another button
                    st.info("You can make changes and submit again if needed.")
        
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