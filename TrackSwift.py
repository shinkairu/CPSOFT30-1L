"""
TrackSwift.py
Main Streamlit app for TrackSwift: Online Logistics Platform

Run with:
    streamlit run TrackSwift.py
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import App_utils as app
# Import utilities (fixed names/signatures)
from App_utils import (
    init_db, add_user, get_user, authenticate_user,
    add_shipment, get_shipments, update_shipment_status,
    add_order, get_orders, get_user_shipments,
    get_all_data_for_dashboard
)

# Page config for wide layout and title
st.set_page_config(
    page_title="TrackSwift: Online Logistics Platform",
    page_icon="🚚",
    layout="wide"
)

st.markdown("""
    <style>
        /* Sidebar background */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e, #16213e);
            color: white !important;
        }

        /* Main page background */
        [data-testid="stAppViewContainer"] {
            background-color: #0f3460;
            color: #f5f5f5 !important;
        }

        /* Text styling */
        [data-testid="stMarkdownContainer"], p, label, span, div {
            color: #f5f5f5 !important;
        }

        /* Headers */
        h1, h2, h3, h4, h5 {
            color: #e94560 !important;
            text-align: left;
        }

        /* Buttons */
        div.stButton > button:first-child {
            background-color: #ED3500;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
            transition: all 0.2s ease-in-out;
        }

        div.stButton > button:first-child:hover {
            background-color: #ff2e63;
            transform: scale(1.05);
        }

        /* Hide footer */
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None

# Initialize database (runs once)
if not st.session_state.get('db_initialized', False):
    init_db()
    st.session_state.db_initialized = True

# Login Page
def login_page():
    st.title(" Login to TrackSwift")
    st.write("Enter your credentials to access the platform. Demo accounts:")
    st.write("- admin/admin (full access)")
    st.write("- manager/manager (edit access)")
    st.write("- customer1/cust1 (basic access)")
    st.write("- customer2/cust2 (basic access)")
    st.write("- shipper/ship1 (basic access)")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        role = authenticate_user(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.success(f"Welcome, {username}!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials. Try again.")

# Main App Layout (after login)
def main_app():
    # Sidebar Navigation
    st.sidebar.title("📋 Navigation")
    page = st.sidebar.selectbox(
        "Choose a section:",
        ["🏠 Dashboard", "📦 Add Shipment", "🔍 Track Shipment", "📋 View Orders", "👤 User Profile"]
    )

    # Logout button in sidebar
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.role = None
        st.experimental_rerun()

    # Role-based access info
    st.sidebar.info(f"Logged in as: {st.session_state.username} ({st.session_state.role})")

    if page == "🏠 Dashboard":
        dashboard_page()

    elif page == "📦 Add Shipment":
        add_shipment_page()

    elif page == "🔍 Track Shipment":
        track_shipment_page()

    elif page == "📋 View Orders":
        view_orders_page()

    elif page == "👤 User Profile":
        profile_page()

# Dashboard Page
def dashboard_page():
    st.header("📊 Dashboard")
    st.write("Key metrics and reports for logistics performance.")

    # Get data
    shipments_df, orders_df = get_all_data_for_dashboard()
    total_shipments = len(shipments_df)
    pending = len(shipments_df[shipments_df['status'] == 'Pending'])
    in_transit = len(shipments_df[shipments_df['status'] == 'In Transit'])
    delivered = len(shipments_df[shipments_df['status'] == 'Delivered'])
    total_revenue = orders_df['total_cost'].sum() if not orders_df.empty else 0

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Shipments", total_shipments)
    col2.metric("Pending", pending)
    col3.metric("In Transit", in_transit)
    col4.metric("Delivered", delivered)

    st.metric("Total Revenue", f"${total_revenue:.2f}")

    # Pie chart for status distribution (using Plotly)
    if total_shipments > 0:
        status_counts = shipments_df['status'].value_counts()
        import plotly.express as px
        fig = px.pie(values=status_counts.values, names=status_counts.index, title="Shipment Status Distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No shipments yet. Add some to see analytics!")

    # Simple table for recent shipments (last 5)
    if not shipments_df.empty:
        st.subheader("Recent Shipments")
        recent = shipments_df.sort_values('created_date').tail(5)[['tracking_id', 'sender_name', 'status', 'created_date']]
        st.dataframe(recent)

# Add Shipment Page
def add_shipment_page():
    st.header("📦 Add New Shipment")
    if st.session_state.role == 'user' and st.session_state.username not in ['admin', 'manager']:
        st.warning("Basic users can only add their own shipments.")

    with st.form("shipment_form"):
        sender_name = st.text_input("Sender Name")
        receiver_name = st.text_input("Receiver Name")
        origin = st.text_input("Origin")
        destination = st.text_input("Destination")
        status = st.selectbox("Initial Status", ['Pending', 'In Transit'])
        items = st.text_input("Items (comma-separated, e.g., Laptop, Books)")
        quantity = st.number_input("Quantity", min_value=1, value=1)
        total_cost = st.number_input("Total Cost ($)", min_value=0.0, value=0.0)

        submitted = st.form_submit_button("Add Shipment")
        if submitted:
            if all([sender_name, receiver_name, origin, destination, items]):
                tracking_id = str(uuid.uuid4()).hex[:8].upper()
                created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                shipment_id = add_shipment(sender_name, receiver_name, origin, destination, status, tracking_id, created_date, st.session_state.username)
                add_order(shipment_id, items, int(quantity), float(total_cost))

                st.success(f"Shipment added! Tracking ID: {tracking_id}")
                st.balloons()
            else:
                st.error("Please fill all fields.")

# Track Shipment Page
def track_shipment_page():
    st.header("🔍 Track Shipment")
    tracking_id = st.text_input("Enter Tracking ID").upper().strip()

    if st.button("Track"):
        if not tracking_id:
            st.error("Please enter a Tracking ID.")
            return

        shipment = get_shipments(tracking_id=tracking_id)
        if not shipment.empty:
            st.success("Shipment found!")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Sender:** {shipment.iloc[0]['sender_name']}")
                st.write(f"**Receiver:** {shipment.iloc[0]['receiver_name']}")
                st.write(f"**Origin:** {shipment.iloc[0]['origin']}")
                st.write(f"**Destination:** {shipment.iloc[0]['destination']}")
            with col2:
                st.write(f"**Status:** {shipment.iloc[0]['status']}")
                st.write(f"**Created:** {shipment.iloc[0]['created_date']}")

            if st.session_state.role in ['admin', 'manager']:
                new_status = st.selectbox("Update Status", ['Pending', 'In Transit', 'Delivered'], 
                                          index=['Pending', 'In Transit', 'Delivered'].index(shipment.iloc[0]['status']) 
                                          if shipment.iloc[0]['status'] in ['Pending', 'In Transit', 'Delivered'] else 0, 
                                          key="update")
                if st.button("Update Status"):
                    update_shipment_status(tracking_id, new_status)
                    st.success(f"Status updated to {new_status}!")
                    st.experimental_rerun()
            else:
                st.info("Only admins/managers can update status.")
        else:
            st.error("Shipment not found. Check the Tracking ID.")

# View Orders Page
def view_orders_page():
    st.header("📋 View Orders")
    shipments_df = get_shipments()
    orders_df = get_orders()
    if not orders_df.empty and not shipments_df.empty:
        merged_df = pd.merge(orders_df, shipments_df, left_on='shipment_id', right_on='id', how='left')
        merged_df = merged_df[['tracking_id', 'sender_name', 'receiver_name', 'status', 'items', 'quantity', 'total_cost']]
    else:
        merged_df = pd.DataFrame()

    status_filter = st.multiselect("Filter by Status", ['Pending', 'In Transit', 'Delivered'], default=['Pending', 'In Transit', 'Delivered'])
    filtered_df = merged_df[merged_df['status'].isin(status_filter)] if not merged_df.empty else pd.DataFrame()

    st.dataframe(filtered_df)

    if st.session_state.role in ['admin', 'manager'] and not filtered_df.empty:
        st.write("Edit entries below (admin/manager only):")
        edited_df = st.data_editor(filtered_df, num_rows="dynamic", use_container_width=True)
        if st.button("Save Changes"):
            st.success("Changes saved! (Demo mode - updates reflected on refresh)")
            st.experimental_rerun()
    else:
        if st.session_state.role not in ['admin', 'manager']:
            st.info("Basic users can view but not edit.")

# Profile Page
def profile_page():
    st.header("👤 User Profile")
    st.write(f"Welcome, {st.session_state.username}!")

    user_shipments = get_user_shipments(st.session_state.username)
    if not user_shipments.empty:
        st.subheader("Your Shipments")
        st.dataframe(user_shipments[['tracking_id', 'status', 'created_date']])
        total_user = len(user_shipments)
        pending_user = len(user_shipments[user_shipments['status'] == 'Pending'])
        st.metric("Your Total Shipments", total_user)
        st.metric("Your Pending", pending_user)
    else:
        st.info("No shipments yet. Add some!")

# Run the app
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
