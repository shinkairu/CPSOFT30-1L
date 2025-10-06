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
    for user in sample_users:
        try:
            add_user(cursor, *user)
        except sqlite3.IntegrityError:
            pass  # User exists

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
    for shipment in sample_shipments:
        try:
            cursor.execute("""
                INSERT INTO Shipments (sender_name, receiver_name, origin, destination, status, tracking_id, created_date, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, shipment)
            shipment_id = cursor.lastrowid
            # Add corresponding order (sample)
            sample_orders = [
                (shipment_id, 'Laptop, Phone', 2, 1500.0),
                (shipment_id, 'Books, Notebook', 5, 200.0),
                (shipment_id, 'Clothes', 10, 300.0),
                (shipment_id, 'Electronics', 1, 800.0),
                (shipment_id, 'Furniture', 3, 500.0),
                (shipment_id, 'Test Items', 4, 100.0),
                (shipment_id, 'Manager Goods', 6, 400.0),
                (shipment_id, 'User  Parcel', 2, 250.0)
            ]
            cursor.execute("INSERT INTO Orders (shipment_id, items, quantity, total_cost) VALUES (?, ?, ?, ?)", sample_orders[sample_shipments.index(shipment)])
        except sqlite3.IntegrityError:
            pass  # Duplicate tracking_id

    conn.commit()
    conn.close()

def add_user(cursor, username, password, role):
    """Add a user (for init only)."""
    # Plain text for demo; in production, hash with hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("INSERT INTO Users (username, password, role) VALUES (?, ?, ?)", (username, password, role))

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
        query +=