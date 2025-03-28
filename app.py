import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Product Data Collection",
    page_icon="🌍",
    layout="wide"
)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
if "current_vendor" not in st.session_state:
    st.session_state.current_vendor = None

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
        params = st.query_params
        if "vendor" in params:
            vendor_id = params["vendor"]
            st.success(f"Vendor ID detected: {vendor_id}")
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

# Simple admin dashboard
def admin_dashboard():
    st.title("Admin Dashboard")
    
    st.success("You are logged in as an administrator")
    
    # Display the secret values (masked for security)
    st.subheader("Secrets Configuration")
    
    if "spreadsheet_name" in st.secrets:
        st.success(f"✓ spreadsheet_name is set to: {st.secrets.spreadsheet_name}")
    else:
        st.error("✗ spreadsheet_name is not set")
        
    if "admin_password" in st.secrets:
        st.success("✓ admin_password is set (value hidden)")
    else:
        st.error("✗ admin_password is not set")
        
    if "gcp_service_account" in st.secrets:
        st.success("✓ gcp_service_account is set")
        st.write("Service account email:", st.secrets.gcp_service_account.get("client_email", "Not found"))
    else:
        st.error("✗ gcp_service_account is not set")
    
    # Logout button
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_admin = False
        st.session_state.current_vendor = None
        st.rerun()

# Simple vendor dashboard
def vendor_dashboard(vendor_id):
    st.title(f"Vendor Dashboard: {vendor_id}")
    
    st.success(f"You are logged in as vendor: {vendor_id}")
    st.info("This is a basic working version. When fully implemented, this page will show your products and allow you to enter Country of Origin and HTS codes.")
    
    # Logout button
    if st.button("Logout"):
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