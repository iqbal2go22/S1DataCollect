import streamlit as st

# Set page config
st.set_page_config(
    page_title="Simple Test App",
    page_icon="🌍",
    layout="wide"
)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_page():
    st.title("Simple Test App")
    
    st.write("This is a simple test app to verify basic functionality.")
    
    # Display raw secrets for debugging
    st.subheader("Debug Information")
    
    # Check if secrets exist
    if hasattr(st, "secrets"):
        st.success("Secrets are available")
        
        # Check for specific secrets
        for key in ["spreadsheet_name", "admin_password", "gcp_service_account"]:
            if key in st.secrets:
                st.success(f"✓ {key} is defined")
            else:
                st.error(f"✗ {key} is NOT defined")
        
        # If gcp_service_account exists, check its structure
        if "gcp_service_account" in st.secrets:
            st.write("gcp_service_account structure:")
            try:
                for key in st.secrets.gcp_service_account:
                    masked_value = "***" if key in ["private_key", "private_key_id", "client_id"] else str(st.secrets.gcp_service_account[key])[:20] + "..."
                    st.write(f"- {key}: {masked_value}")
            except:
                st.error("Error accessing gcp_service_account structure")
    else:
        st.error("No secrets found")
    
    # Simple password login
    password = st.text_input("Enter password:", type="password")
    
    login_button = st.button("Login")
    if login_button:
        expected_password = "test123"
        
        try:
            # Try to get from secrets first
            if hasattr(st, "secrets") and "admin_password" in st.secrets:
                expected_password = st.secrets.admin_password
        except:
            st.warning("Could not read admin_password from secrets, using default")
        
        st.write(f"You entered: {password}")
        st.write(f"Expected: {expected_password}")
        
        if password == expected_password:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Invalid password")

def main_page():
    st.title("Success!")
    st.write("You are logged in. This means basic functionality is working.")
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_page()

if __name__ == "__main__":
    main()