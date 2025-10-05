"""
App_utils.py: Utility functions for TrackSwift logistics app.
Handles DB operations, authentication, and data queries.
"""

import streamlit as st
import sqlite3
import pandas as pd
import uuid
import hashlib
from datetime import datetime, timedelta

# Database connection helper (cached for performance)
@st.cache_resource
def get_conn():
    try:
        conn = sqlite3.connect('logistics.db', check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = OFF")  # Disable FK for demo to avoid init errors
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Hash password (simple SHA-256 for demo; use bcrypt in production)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize database with tables and sample data
def init_db():
    conn = get_conn()
    if not conn:
        st.error("Cannot initialize database. Check permissions or file system.")
        return

    try:
        c = conn.cursor()
        
        # Create users table (simplified, no FK for demo)
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Create shipments table (simplified, no FK for demo)
        c.execute('''
            CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                sender_name TEXT NOT NULL,
                receiver_name TEXT NOT NULL,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL,
                tracking_id TEXT UNIQUE NOT NULL,
                created_date DATETIME NOT NULL
            )
        ''')
        
        # Create orders table (simplified, no FK for demo)
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER NOT NULL,
                items TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_cost REAL NOT NULL
            )
        ''')
        
        conn.commit()  # Commit table creations
        
        # Insert default users if they don't exist (hashed passwords)
        default_users = [
            ('admin', hash_password('admin')),
            ('user', hash_password('user'))
        ]
        for username, password_hash in default_users:
            try:
                c.execute(
                    "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                    (username, password_hash)
                )
            except sqlite3.IntegrityError as e:
                st.warning(f"User  {username} already exists: {e}")
        
        conn.commit()
        
        # Get user IDs (fetch safely)
        c.execute("SELECT id FROM users WHERE username='admin'")
        admin_id_result = c.fetchone()
        admin_id = admin_id_result[0] if admin_id_result else None

        c.execute("SELECT id FROM users WHERE username='user'")
        user_id_result = c.fetchone()
        user_id = user_id_result[0] if user_id_result else None

        if not admin_id or not user_id:
            st.error("Failed to initialize default users. Check database.")
            conn.close()
            return

        # Sample shipments and orders (only insert if no shipments exist to avoid duplicates)
        c.execute("SELECT COUNT(*) FROM shipments")
        shipment_count = c.fetchone()[0]
        if shipment_count == 0:
            # Sample data: 5 for admin, 3 for user; varied statuses and dates
            sample_data = [
                # Admin shipments
                (admin_id, 'John Doe', 'Jane Smith', 'New York', 'Los Angeles', 'Pending', datetime.now() - timedelta(days=5)),
                (admin_id, 'Alice Johnson', 'Bob Wilson', 'Chicago', 'Miami', 'In Transit', datetime.now() - timedelta(days=3)),
                (admin_id, 'Charlie Brown', 'Diana Prince', 'Seattle', 'Boston', 'Delivered', datetime.now() - timedelta(days=1)),
                (admin_id, 'Eve Davis', 'Frank Miller', 'Denver', 'Atlanta', 'Pending', datetime.now()),
                (admin_id, 'Grace Lee', 'Henry Taylor', 'Phoenix', 'Detroit', 'In Transit', datetime.now() - timedelta(days=2)),
                # User shipments
                (user_id, 'User  Sender1', 'User  Receiver1', 'Dallas', 'Portland', 'Delivered', datetime.now() - timedelta(days=4)),
                (user_id, 'User  Sender2', 'User  Receiver2', 'Austin', 'Nashville', 'Pending', datetime.now() - timedelta(days=6)),
                (user_id, 'User  Sender3', 'User  Receiver3', 'Houston', 'Memphis', 'In Transit', datetime.now())
            ]

            sample_orders = [
                ('Electronics', 5, 500.0),
                ('Clothing', 10, 200.0),
                ('Books', 20, 100.0),
                ('Furniture', 2, 800.0),
                ('Groceries', 50, 150.0),
                ('Tools', 3, 300.0),
                ('Toys', 15, 75.0),
                ('Appliances', 1, 1000.0)
            ]

            success_count = 0
            for i, (u_id, sender, receiver, origin, dest, status, created) in enumerate(sample_data):
                try:
                    # Generate unique tracking ID
                    tracking_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
                    
                    # Insert shipment
                    c.execute(
                        """INSERT INTO shipments 
                        (user_id, sender_name, receiver_name, origin, destination, status, tracking_id, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (u_id, sender, receiver, origin, dest, status, tracking_id, created)
                    )
                    shipment_id = c.lastrowid
                    
                    # Insert corresponding order (cycle through sample_orders)
                    order_idx = i % len(sample_orders)
                    items, qty, cost = sample_orders[order_idx]
                    c.execute(
                        "INSERT INTO orders (shipment_id, items, quantity, total_cost) VALUES (?, ?, ?, ?)",
                        (shipment_id, items, qty, cost)
                    )
                    success_count += 1
                except sqlite3.IntegrityError as e:
                    st.warning(f"Skipping duplicate sample shipment {i+1}: {e}")
                except Exception as e:
                    st.error(f"Error inserting sample shipment {i+1}: {e}")

            conn.commit()
            if success_count > 0:
                st.success(f"Database initialized with {success_count} sample shipments.")
            else:
                st.warning("No sample data inserted (possible DB issue).")

    except sqlite3.ProgrammingError as e:
        st.error(f"SQL ProgrammingError in init_db: {e}. Check table syntax or DB state.")
        conn.rollback()
    except Exception as e:
        st.error(f"Unexpected error in init_db: {e}")
        conn.rollback()
    finally:
        conn.close()

# Login function (handles form and session state)
def handle_login():
    if st.session_state.get('logged_in', False):
        return True
    
    st.title("🔐 Login to TrackSwift")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
    
    if submit:
        if username and password:
            conn = get_conn()
            if not conn:
                st.error("Database connection failed during login.")
                return False
            try:
                c = conn.cursor()
                password_hash = hash_password(password)
                c.execute(
                    "SELECT id, username FROM users WHERE username = ? AND password = ?",
                    (username, password_hash)
                )
                user = c.fetchone()
                conn.close()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user[1]
                    st.session_state.user_id = user[0]
                    st.session_state.is_admin = (username == 'admin')
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                    return True
                else:
                    st.error("Invalid username or password.")
            except Exception as e:
                st.error(f"Login error: {e}")
                if conn:
                    conn.close()
        else:
            st.error("Please enter username and password.")
    
    return False

# Logout function
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Get user's shipments as DataFrame (with optional orders join)
def get_user_shipments_df(conn, user_id):
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT s.*, o.items, o.quantity, o.total_cost 
            FROM shipments s 
            LEFT JOIN orders o ON s.id = o.shipment_id 
            WHERE s.user_id = ?
        """
        return pd.read_sql(query, conn, params=(user_id,))
    except Exception as e:
        st.error(f"Error fetching user shipments: {e}")
        return pd.DataFrame()

# Get all shipments as DataFrame (with optional orders join)
def get_all_shipments_df(conn, include_orders=False):
    if not conn:
        return pd.DataFrame()
    try:
        if include_orders:
            query = """
                SELECT s.*, o.items, o.quantity, o.total_cost 
                FROM shipments s 
                LEFT JOIN orders o ON s.id = o.shipment_id
            """
            return pd.read_sql(query, conn)
        else:
            query = "SELECT * FROM shipments"
            return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Error fetching shipments: {e}")
        return pd.DataFrame()
