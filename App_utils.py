import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import hashlib  # For simple hashing, but using plain text for demo as specified

# Database file
DB_FILE = "logistics.db"

def get_connection():
    """Get SQLite connection."""
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_db():
    """Initialize database: create tables and insert sample data."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Create Shipments table
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
            user_id TEXT NOT NULL  -- Links to username for simplicity
        )
    """)

    # Create Orders table
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

    # Insert sample users (5 demo accounts, plain text passwords)
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
            pass  # User exists

    # Sample order details (one per shipment)
    sample_order_details = [
        ('Laptop, Phone', 2, 1500.0),
        ('Books, Notebook', 5, 200.0),
        ('Clothes', 10, 300.0),
        ('Electronics', 1, 800.0),
        ('Furniture', 3, 500.0),
        ('Test Items', 4, 100.0),
        ('Manager Goods', 6, 400.0),
        ('User  Parcel', 2, 250.0)
    ]

    # Insert sample shipments (8 samples, linked to users)
    sample_shipments = [
        ('John Doe', 'Jane Smith', 'New York', 'Los Angeles', 'Pending', 'TRK001', '2024-01-01 10:00:00', 'admin'),
        ('Alice Brown', 'Bob Wilson', 'Chicago', 'Miami', 'In Transit', 'TRK002', '2024-01-02 11:00:00', 'manager'),
        ('Customer One', 'Receiver A', 'Boston', 'Seattle', 'Delivered', 'TRK003', '2024-01-03 12:00:00', 'customer1'),
        ('Customer Two', 'Receiver B', 'Dallas', 'Denver', 'Pending', 'TRK004', '2024-01-04 13:00:00', 'customer2'),
        ('Shipper X', 'Receiver C', 'Phoenix', 'Portland', 'In Transit', 'TRK005', '2024-01-05 14:00:00', 'shipper'),
        ('Admin Test', 'User  Test', 'Atlanta', 'Austin', 'Delivered', 'TRK006', '2024-01-06 15:00:00', 'admin'),
        ('Manager Shipment', 'Client D', 'San Francisco', 'San Diego', 'Pending', 'TRK007', '2024-01-07 16:00:00', 'manager'),
        ('User  Shipment', 'Friend E', 'Houston', 'Honolulu', 'In Transit', 'TRK008', '2024-01-08 17:00:00', 'customer1')
    ]
    for idx, shipment in enumerate(sample_shipments):
        try:
            cursor.execute("""
                INSERT INTO Shipments (sender_name, receiver_name, origin, destination, status, tracking_id, created_date, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, shipment)
            shipment_id = cursor.lastrowid
            # Add corresponding order
            items, quantity, total_cost = sample_order_details[idx]
            cursor.execute("""
                INSERT INTO Orders (shipment_id, items, quantity, total_cost)
                VALUES (?, ?, ?, ?)
            """, (shipment_id, items, quantity, total_cost))
        except sqlite3.IntegrityError:
            pass  # Duplicate tracking_id or other constraint

    conn.commit()
    conn.close()

def get_user(cursor, username):
    """Get user by username."""
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    return cursor.fetchone()

def authenticate_user(username, password):
    """Authenticate user (plain text comparison for demo)."""
    conn = get_connection()
    cursor = conn.cursor()
    user = get_user(cursor, username)
    conn.close()
    if user and user[2] == password:  # user[2] is password
        return user[3]  # role
    return None

def add_shipment(sender_name, receiver_name, origin, destination, status, tracking_id, created_date, user_id):
    """Add a new shipment."""
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

def get_shipments(tracking_id=None):
    """Get shipments DataFrame, optional filter by tracking_id."""
    conn = get_connection()
    query = "SELECT * FROM Shipments"
    params = ()
    if tracking_id:
        query += " WHERE tracking_id = ?"
        params = (tracking_id,)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_shipment_status(tracking_id, new_status):
    """Update shipment status by tracking_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Shipments SET status = ? WHERE tracking_id = ?", (new_status, tracking_id))
    conn.commit()
    conn.close()

def add_order(shipment_id, items, quantity, total_cost):
    """Add a new order linked to shipment_id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Orders (shipment_id, items, quantity, total_cost)
        VALUES (?, ?, ?, ?)
    """, (shipment_id, items, quantity, total_cost))
    conn.commit()
    conn.close()

def get_orders():
    """Get all orders DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM Orders", conn)
    conn