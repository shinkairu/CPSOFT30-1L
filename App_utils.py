"""
App_utils.py
Utility functions for TrackSwift Streamlit app.
Provides DB init, auth, and CRUD helpers.

This version fixes function names and signatures so TrackSwift.py and App_utils.py match.
"""

import sqlite3
import pandas as pd
from datetime import datetime
import hashlib
from typing import Optional, Tuple

DB_FILE = "logistics.db"

def get_connection():
    """Return a sqlite3 connection. Set row_factory for named access."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables and seed demo data if missing."""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Shipments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name TEXT NOT NULL,
            receiver_name TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            status TEXT NOT NULL,
            tracking_id TEXT UNIQUE NOT NULL,
            created_date TEXT NOT NULL,
            user_id TEXT NOT NULL
        )
    """)

    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_cost REAL NOT NULL,
            FOREIGN KEY (shipment_id) REFERENCES Shipments (id)
        )
    """)

    # Seed users if table empty
    cursor.execute("SELECT COUNT(*) as c FROM Users")
    if cursor.fetchone()["c"] == 0:
        sample_users = [
            ('admin', 'admin', 'admin'),
            ('manager', 'manager', 'manager'),
            ('customer1', 'cust1', 'user'),
            ('customer2', 'cust2', 'user'),
            ('shipper', 'ship1', 'user')
        ]
        for username, password, role in sample_users:
            try:
                cursor.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            except sqlite3.IntegrityError:
                pass

    # Seed shipments + orders if shipments empty
    cursor.execute("SELECT COUNT(*) as c FROM Shipments")
    if cursor.fetchone()["c"] == 0:
        sample_order_details = [
            ('Laptop, Phone', 2, 1500.0),
            ('Books, Notebook', 5, 200.0),
            ('Clothes', 10, 300.0),
            ('Electronics', 1, 800.0),
            ('Furniture', 3, 500.0),
            ('Test Items', 4, 100.0),
            ('Manager Goods', 6, 400.0),
            ('User Parcel', 2, 250.0)
        ]

        sample_shipments = [
            ('John Doe', 'Jane Smith', 'New York', 'Los Angeles', 'Pending', 'TRK001', '2024-01-01 10:00:00', 'admin'),
            ('Alice Brown', 'Bob Wilson', 'Chicago', 'Miami', 'In Transit', 'TRK002', '2024-01-02 11:00:00', 'manager'),
            ('Customer One', 'Receiver A', 'Boston', 'Seattle', 'Delivered', 'TRK003', '2024-01-03 12:00:00', 'customer1'),
            ('Customer Two', 'Receiver B', 'Dallas', 'Denver', 'Pending', 'TRK004', '2024-01-04 13:00:00', 'customer2'),
            ('Shipper X', 'Receiver C', 'Phoenix', 'Portland', 'In Transit', 'TRK005', '2024-01-05 14:00:00', 'shipper'),
            ('Admin Test', 'User Test', 'Atlanta', 'Austin', 'Delivered', 'TRK006', '2024-01-06 15:00:00', 'admin'),
            ('Manager Shipment', 'Client D', 'San Francisco', 'San Diego', 'Pending', 'TRK007', '2024-01-07 16:00:00', 'manager'),
            ('User Shipment', 'Friend E', 'Houston', 'Honolulu', 'In Transit', 'TRK008', '2024-01-08 17:00:00', 'customer1')
        ]

        for idx, shipment in enumerate(sample_shipments):
            try:
                cursor.execute("""
                    INSERT INTO Shipments (sender_name, receiver_name, origin, destination, status, tracking_id, created_date, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, shipment)
                shipment_id = cursor.lastrowid
                items, quantity, total_cost = sample_order_details[idx]
                cursor.execute("""
                    INSERT INTO Orders (shipment_id, items, quantity, total_cost)
                    VALUES (?, ?, ?, ?)
                """, (shipment_id, items, quantity, total_cost))
            except sqlite3.IntegrityError:
                pass

    conn.commit()
    conn.close()

def add_user(username: str, password: str, role: str = 'user') -> bool:
    """
    Add a new user. Returns True if added, False if username exists.
    (Plain-text password used for demo only. In production, hash passwords.)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(username: str) -> Optional[sqlite3.Row]:
    """Return user row (sqlite Row) or None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def authenticate_user(username: str, password: str) -> Optional[str]:
    """
    Authenticate user (plain-text for demo). Returns role string on success, otherwise None.
    """
    user = get_user(username)
    if user and user['password'] == password:
        return user['role']
    return None

def add_shipment(sender_name: str, receiver_name: str, origin: str, destination: str, status: str, tracking_id: str, created_date: str, user_id: str) -> int:
    """Insert a new shipment and return its id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Shipments (sender_name, receiver_name, origin, destination, status, tracking_id, created_date, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (sender_name, receiver_name, origin, destination, status, tracking_id, created_date, user_id))
    shipment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return shipment_id

def get_shipments(tracking_id: Optional[str] = None) -> pd.DataFrame:
    """Return shipments as a pandas DataFrame. If tracking_id provided, filter by it."""
    conn = get_connection()
    if tracking_id:
        df = pd.read_sql_query("SELECT * FROM Shipments WHERE tracking_id = ?", conn, params=(tracking_id,))
    else:
        df = pd.read_sql_query("SELECT * FROM Shipments", conn)
    conn.close()
    return df

def update_shipment_status(tracking_id: str, new_status: str) -> None:
    """Update shipment status by tracking_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Shipments SET status = ? WHERE tracking_id = ?", (new_status, tracking_id))
    conn.commit()
    conn.close()

def add_order(shipment_id: int, items: str, quantity: int, total_cost: float) -> int:
    """Insert an order linked to a shipment and return the new order id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Orders (shipment_id, items, quantity, total_cost)
        VALUES (?, ?, ?, ?)
    """, (shipment_id, items, quantity, total_cost))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_orders() -> pd.DataFrame:
    """Return all orders as a DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Orders", conn)
    conn.close()
    return df

def get_user_shipments(username: str) -> pd.DataFrame:
    """Return shipments associated with the given username."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Shipments WHERE user_id = ?", conn, params=(username,))
    conn.close()
    return df

def get_all_data_for_dashboard() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return shipments_df and orders_df for dashboard analytics."""
    shipments_df = get_shipments()
    orders_df = get_orders()
    # ensure datetime column parsed for sorting if exists
    if 'created_date' in shipments_df.columns:
        try:
            shipments_df['created_date'] = pd.to_datetime(shipments_df['created_date'])
        except Exception:
            pass
    return shipments_df, orders_df
