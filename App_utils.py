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

# Database connection helper (cached for performance; DO NOT close manually)
@st.cache_resource
def get_conn():
    try:
        conn = sqlite3.connect('logistics.db', check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = OFF")  # Disable FK for demo
        conn.execute("PRAGMA synchronous = OFF")   # Faster writes on Cloud
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Hash password (simple SHA-256 for demo; use bcrypt in production)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize database with tables and sample data (uses NON-CACHED conn to avoid cache issues)
def init_db():
    # Use a fresh, non-cached connection for init only
    init_conn = None
    try:
        init_conn = sqlite3.connect('logistics.db', check_same_thread=False)
        init_conn.execute("PRAGMA foreign_keys = OFF")
        init_conn.execute("PRAGMA synchronous = OFF")
        c = init_conn.cursor()
        
        # Create users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Create shipments table
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
        
        # Create orders table
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_id INTEGER NOT NULL,
                items TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_cost REAL NOT NULL
            )
        ''')
        
        init_conn.commit()  # Commit table creations
        
        # Insert default users if they don't exist
        default_users = [
            ('admin', hash_password('admin')),
            ('user', hash_password('user'))
        ]
        init_conn.execute("BEGIN")  # Start transaction for users
        for username, password_hash in default_users:
            try:
                c.execute(
                    "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                    (username, password_hash)
                )
            except sqlite3.IntegrityError:
                pass  # Already exists
        init_conn.commit()
        
        # Get user IDs
        c.execute("SELECT id FROM users WHERE username='admin'")
        admin_id_result = c.fetchone()
        admin_id = admin_id_result[0] if admin_id_result else None

        c.execute("SELECT id FROM users WHERE username='user'")
        user_id_result = c.fetchone()
        user_id = user_id_result[0] if user_id_result else None

        if not admin_id or not user_id:
            st.error("Failed to initialize default users.")
            init_conn.close()
            return

        # Sample shipments and orders (only if no shipments)
        c.execute("SELECT COUNT(*) FROM shipments")
        shipment_count = c.fetchone()[0]
        if shipment_count == 0:
            init_conn.execute("BEGIN")  # Transaction for samples
            sample_data = [
                # Admin shipments (5)
                (admin_id, 'John Doe', 'Jane Smith', 'New York', 'Los Angeles', 'Pending', datetime.now() - timedelta(days=5)),
                (admin_id, 'Alice Johnson', 'Bob Wilson', 'Chicago', 'Miami', 'In Transit', datetime.now() - timedelta(days=3)),
                (admin_id, 'Charlie Brown', 'Diana Prince', 'Seattle', 'Boston', 'Delivered', datetime.now() - timedelta(days=1)),
                (admin_id, 'Eve Davis', 'Frank Miller', 'Denver', 'Atlanta', 'Pending', datetime.now()),
                (admin_id, 'Grace Lee', 'Henry Taylor', 'Phoenix', 'Detroit', 'In Transit', datetime.now() - timedelta(days=2)),
                # User shipments (3)
                (user_id, 'User  Sender1', 'User  Receiver1', 'Dallas', 'Portland', 'Delivered', datetime.now() - timedelta(days=4)),
                (user_id, 'User  Sender2', 'User  Receiver2', 'Austin', 'Nashville', 'Pending', datetime.now() - timedelta(days=6)),
                (user_id, 'User  Sender3', 'User  Receiver3', 'Houston', 'Memphis', 'In Transit', datetime.now())
            ]

            sample_orders = [
                ('Electronics', 5, 500.0), ('Clothing', 10, 200.0), ('Books', 20, 100.0),
                ('Furniture', 2, 800.0), ('Groceries', 50, 150.0), ('Tools', 3, 300.0),
                ('Toys', 15, 75.0), ('Appliances', 1, 1000.0)
            ]

            success_count = 0
            for i, (u_id, sender, receiver, origin, dest, status, created) in enumerate(sample_data):
                try:
                    tracking_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
                    c.execute(
                        """INSERT INTO shipments 
                        (user_id, sender_name, receiver_name, origin, destination, status, tracking_id, created_date) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (u_id, sender, receiver, origin, dest, status, tracking_id, created)
                    )
                    shipment_id = c.lastrowid
                    
                    order_idx = i % len(sample_orders)
                    items, qty, cost = sample_orders[order_idx]
                    c.execute(
                        "INSERT INTO orders (shipment_id, items, quantity, total_cost) VALUES (?, ?, ?, ?)",
                        (shipment_id, items, qty, cost)
                    )
                    success_count += 1
                except sqlite3.IntegrityError:
                    pass  # Skip duplicates
                except Exception as insert_e:
                    st.warning(f"Skipping sample {i+1}: {insert_e}")
                    continue

            init_conn.commit()
            if success_count > 0:
                st.success(f"Initialized with {success_count} sample shipments.")
            else:
                st.warning("No samples added (DB may already have data).")

    except sqlite3.ProgrammingError as e:
        st.error(f"SQL error in init_db: {e}")
        if init_conn:
            try:
                init_conn.rollback()
            except:
                pass  # Ignore if already closed
    except Exception as e:
        st.error(f"Unexpected init error: {e}")
        if init_conn:
            try:
                init_conn.rollback()
            except:
                pass
    finally:
        if init_conn:
            init_conn.close()  # Safe to close non-cached init conn

# Login function (uses cached conn; NO close)
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
                st.error("Database unavailable.")
                return False
            try:
                c = conn.cursor()
                password_hash = hash_password(password)
                c.execute(
                    "SELECT id, username FROM users WHERE username = ? AND password = ?",
                    (username, password_hash)
                )
                user = c.fetchone()
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user[1]
                    st.session_state.user_id = user[0]
                    st.session_state.is_admin = (username == 'admin')
                    st.success(f"Welcome, {username}!")
                    st.rerun()
                    return True
                else:
                    st.error("Invalid credentials.")
            except sqlite3.ProgrammingError as e:
                st.error(f"Login SQL error: {e}")
            except Exception as e:
                st.error(f"Login error: {e}")
        else:
            st.error("Enter username and password.")
    
    return False

# Logout function
def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Get user's shipments as DataFrame (uses cached conn; NO close)
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
        st.error(f"Error fetching user data: {e}")
        return pd.DataFrame()

# Get all shipments as DataFrame (uses cached conn; NO close)
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
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()
