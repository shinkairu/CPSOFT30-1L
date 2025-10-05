"""
TrackSwift: Online Logistics Platform
A modular Streamlit app for managing shipments and orders with user authentication and analytics.
Run with: streamlit run TrackSwift.py

Dependencies: See requirements.txt
Utilities: Imported from App_utils.py
"""

import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import uuid  # For tracking ID generation

# Try importing utilities; show error if failed
try:
    from App_utils import (get_conn, hash_password, init_db, handle_login, logout,
                           get_user_shipments_df, get_all_shipments_df)
except ImportError as e:
    st.error(f"Import error from App_utils.py: {e}")
    st.stop()

# Page config (wide layout for better UX)
st.set_page_config(
    page_title="TrackSwift",
    page_icon="🚚",
    layout="wide"
)

# Initialize DB on first run
init_db()

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.is_admin = False

# Handle authentication (redirects to login if not logged in)
if not handle_login():
    st.stop()

# Main interface after login
st.title("🚚 TrackSwift: Online Logistics Platform")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a section",
    ["📊 Dashboard", "➕ Add Shipment", "🔍 Track Shipment", "📋 View Orders", "👤 User Profile"]
)

# Logout button in sidebar
if st.sidebar.button("🚪 Logout"):
    logout()

# Role-based access note (simulates secure integration and access control)
if st.session_state.is_admin:
    st.sidebar.info("🛡️ Admin Access: Full editing capabilities")
else:
    st.sidebar.info("👤 User Access: View and add only")

# NO GLOBAL CONN OR CLOSE HERE - Handle per page to avoid cache issues

if page == "📊 Dashboard":
    st.header("Analytics & Reporting Dashboard")
    st.markdown("---")
    
    # Get conn locally for this page
    conn = get_conn()
    if not conn:
        st.error("Database unavailable for dashboard.")
    else:
        try:
            df_shipments = get_all_shipments_df(conn)
            if not df_shipments.empty:
                col1, col2, col3, col4 = st.columns(4)
                
                total = len(df_shipments)
                pending = len(df_shipments[df_shipments['status'] == 'Pending'])
                in_transit = len(df_shipments[df_shipments['status'] == 'In Transit'])
                delivered = len(df_shipments[df_shipments['status'] == 'Delivered'])
                
                with col1:
                    st.metric("Total Shipments", total)
                with col2:
                    st.metric("Pending", pending)
                with col3:
                    st.metric("In Transit", in_transit)
                with col4:
                    st.metric("Delivered", delivered)
                
                # Status distribution pie chart
                status_counts = df_shipments['status'].value_counts().reset_index()
                status_counts.columns = ['status', 'count']
                pie_chart = alt.Chart(status_counts).mark_arc().encode(
                    theta=alt.Theta(field='count', type='quantitative'),
                    color=alt.Color(field='status', type='nominal', legend=alt.Legend(title='Status'))
                ).properties(width=400, height=400)
                st.altair_chart(pie_chart, use_container_width=True)
                
                # Analytics & Reporting (Daily/Weekly/Monthly)
                st.subheader("Performance Reports")
                report_type = st.selectbox("Report Type", ["Daily", "Weekly", "Monthly"])
                
                # Date range input
                default_start = datetime.now().date() - timedelta(days=30)
                default_end = datetime.now().date()
                date_range = st.date_input(
                    "Select Date Range",
                    value=(default_start, default_end),
                    min_value=datetime.now().date() - timedelta(days=365)
                )
                start_date, end_date = date_range
                
                if start_date > end_date:
                    st.error("Start date must be before end date.")
                else:
                    # Filter shipments by date
                    df_filtered = df_shipments[
                        (pd.to_datetime(df_shipments['created_date']).dt.date >= start_date) &
                        (pd.to_datetime(df_shipments['created_date']).dt.date <= end_date)
                    ].copy()
                    
                    if df_filtered.empty:
                        st.info("No shipments in the selected date range.")
                    else:
                        df_filtered['created_date'] = pd.to_datetime(df_filtered['created_date'])
                        
                        if report_type == "Daily":
                            df_filtered['date_group'] = df_filtered['created_date'].dt.date
                            group_col = 'date_group'
                        elif report_type == "Weekly":
                            df_filtered['date_group'] = df_filtered['created_date'].dt.isocalendar().week
                            group_col = 'date_group'
                        else:  # Monthly
                            df_filtered['date_group'] = df_filtered['created_date'].dt.to_period('M')
                            group_col = 'date_group'
                        
                        # Aggregated report
                        report_df = df_filtered.groupby([group_col, 'status']).size().reset_index(name='count')
                        if not report_df.empty:
                            report_df = report_df.pivot(index=group_col, columns='status', values='count').fillna(0)
                            st.subheader(f"{report_type} Performance Report")
                            st.dataframe(report_df)
                        
                        # Line chart for total shipments over time
                        total_report = df_filtered.groupby(group_col).size().reset_index(name='total_shipments')
                        if report_type == "Monthly":
                            total_report[group_col] = total_report[group_col].astype(str)  # For display
                        
                        if not total_report.empty:
                            line_chart = alt.Chart(total_report).mark_line(color='steelblue').encode(
                                x=alt.X(group_col, title=f'{report_type}'),
                                y=alt.Y('total_shipments', title='Number of Shipments')
                            ).properties(width=600, height=400)
                            st.altair_chart(line_chart, use_container_width=True)
            else:
                st.info("No shipments data available. Add some shipments to see metrics!")
        except Exception as e:
            st.error(f"Dashboard error: {e}")

elif page == "➕ Add Shipment":
    st.header("Order & Shipment Management - Add New Shipment")
    st.markdown("Create a new shipment and associated order.")
    
    # Get conn locally
    conn = get_conn()
    if not conn:
        st.error("Database unavailable for adding shipment.")
    else:
        with st.form("add_shipment_form"):
            sender_name = st.text_input("Sender Name", placeholder="e.g., John Doe")
            receiver_name = st.text_input("Receiver Name", placeholder="e.g., Jane Smith")
            origin = st.text_input("Origin", placeholder="e.g., New York")
            destination = st.text_input("Destination", placeholder="e.g., Los Angeles")
            initial_status = st.selectbox("Initial Status", ['Pending', 'In Transit', 'Delivered'])
            items = st.text_input("Items", placeholder="e.g., Electronics, Clothing")
            quantity = st.number_input("Quantity", min_value=1, step=1)
            total_cost = st.number_input("Total Cost ($)", min_value=0.0, step=0.01)
            
            submitted = st.form_submit_button("🚚 Add Shipment")
        
        # Use session state for reliable submission check (avoids scope issues)
        if st.session_state.get('form_submitted', False) or submitted:
            st.session_state.form_submitted = True
            if all([sender_name, receiver_name, origin, destination, items]):
                try:
                    c = conn.cursor()
                    tracking_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
                    created_date = datetime.now()
                    
                    # Insert shipment
                    c.execute(
                        """INSERT INTO shipments 
                        (user_id, sender_name, receiver_name, origin, destination, status, tracking_id, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (st.session_state.user_id, sender_name, receiver_name, origin, destination, initial_status, tracking_id, created_date)
                    )
                    shipment_id = c.lastrowid
                    
                    # Insert order
                    c.execute(
                        "INSERT INTO orders (shipment_id, items, quantity, total_cost) VALUES (?, ?, ?, ?)",
                        (shipment_id, items, quantity, total_cost)
                    )
                    
                    conn.commit()
                    st.success(f"✅ Shipment added successfully! Tracking ID: **{tracking_id}**")
                    st.balloons()
                    st.rerun()  # Refresh to show new data
                    st.session_state.form_submitted = False  # Reset
                except Exception as e:
                    st.error(f"Error adding shipment: {str(e)}")
                    conn.rollback()
            else:
                st.error("❌ Please fill in all required fields.")

elif page == "🔍 Track Shipment":
    st.header("Real-Time Shipment Tracking")
    st.markdown("Enter the tracking ID to view details and update status (Admin only).")
    
    tracking_id = st.text_input("Tracking ID", placeholder="e.g., ABC12345")
    
    if tracking_id:
        conn = get_conn()
        if not conn:
            st.error("Database unavailable for tracking.")
        else:
            try:
                c = conn.cursor()
                c.execute(
                    """SELECT s.*, o.items, o.quantity, o.total_cost 
                    FROM shipments s 
                    LEFT JOIN orders o ON s.id = o.shipment_id 
                    WHERE s.tracking_id = ?""",
                    (tracking_id,)
                )
                row = c.fetchone()
                columns = [description[0] for description in c.description]
                
                if row:
                    shipment_data = dict(zip(columns, row))
                    st.success("📦 Shipment Found!")
                    st.json(shipment_data)  # Display as JSON for clarity
                    
                    # Admin status update (Secure Access Control)
                    if st.session_state.is_admin:
                        st.subheader("Update Status")
                        current_status = shipment_data['status']
                        status_options = ['Pending', 'In Transit', 'Delivered']
                        new_status = st.selectbox(
                            "Select New Status",
                            status_options,
                            index=status_options.index(current_status)
                        )
                        
                        if st.button("🔄 Update Status") and new_status != current_status:
                            c.execute(
                                "UPDATE shipments SET status = ? WHERE tracking_id = ?",
                                (new_status, tracking_id)
                            )
                            conn.commit()
                            st.success(f"✅ Status updated to '{new_status}'!")
                            st.rerun()
                        elif st.button("🔄 Update Status"):
                            st.info("No change needed.")
                else:
                    st.error("❌ Shipment not found. Please check the tracking ID.")
            except Exception as e:
                st.error(f"Error tracking shipment: {str(e)}")

elif page == "📋 View Orders":
    st.header("Order & Shipment Management - View All")
    st.markdown("View and filter shipments with order details. Admins can edit (demo mode).")
    
    # Get conn locally
    conn = get_conn()
    if not conn:
        st.error("Database unavailable for viewing orders.")
    else:
        try:
            # Fetch joined data
            df_joined = get_all_shipments_df(conn, include_orders=True)
            
            if df_joined.empty:
                st.info("No orders or shipments yet.")
            else:
                # Filters
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=['All'] + sorted(df_joined['status'].unique().tolist())
                )
                if st.session_state.is_admin:
                    user_filter = st.selectbox(
                        "Filter by User",
                        options=['All', 'Admin', 'User ']
                    )
                else:
                    user_filter = st.selectbox(
                        "Filter by User",
                        options=['All', st.session_state.username]
                    )
                
                filtered_df = df_joined.copy()
                if status_filter != 'All':
                    filtered_df = filtered_df[filtered_df['status'] == status_filter]
                if user_filter != 'All' and st.session_state.is_admin:
                    # Map user_filter to user_id (admin=1, user=2 from init)
                    user_id_map = {'Admin': 1, 'User ': 2}
                    user_id_filter = user_id_map.get(user_filter, st.session_state.user_id)
                    filtered_df = filtered_df[filtered_df['user_id'] == user_id_filter]
                elif user_filter != 'All':
                    filtered_df = filtered_df[filtered_df['user_id'] == st.session_state.user_id]
                
                st.dataframe(filtered_df, use_container_width=True)
                
                # Admin editing (basic; edits in-memory, not persisted for simplicity)
                if st.session_state.is_admin:
                    st.subheader("Edit Entries (Admin Only - Demo)")
                    edited_df = st.data_editor(
                        filtered_df,
                        num_rows="dynamic",
                        use_container_width=True
                    )
                    if st.button("💾 Save Changes (Simulated)"):
                        st.info("Changes saved in session (DB persistence would require additional logic).")
        except Exception as e:
            st.error(f"View orders error: {e}")

elif page == "👤 User Profile":
    st.header(f"👤 Customer Portal - Profile: {st.session_state.username}")
    st.markdown("View your personal shipments and manage account.")
    
    # Get conn locally
    conn = get_conn()
    if not conn:
        st.error("Database unavailable for profile.")
    else:
        try:
            # User's shipments
            df_user_shipments = get_user_shipments_df(conn, st.session_state.user_id)
            
            if df_user_shipments.empty:
                st.info("No shipments associated with your account yet.")
            else:
                st.subheader("Your Shipments")
                st.dataframe(df_user_shipments, use_container_width=True)
                
                # Simple metrics for user (Customer Portal)
                col1, col2 = st.columns(2)
                with col1:
