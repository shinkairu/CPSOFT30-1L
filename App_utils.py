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
    return sqlite3.connect('logistics.db', check_same_thread=False)

# Hash password (simple SHA-256 for demo; use bcrypt in production)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize database with tables and sample data
def init_db():
    conn = get_conn()
    c = conn.cursor()
    
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
            created_date DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    ''')
    
    # Create orders table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total_cost REAL NOT NULL,
            FOREIGN KEY(shipment_id) REFERENCES shipments (id)
        )
    ''')
    
    # Insert default users if they don't exist (hashed passwords)
    default_users = [
        ('admin', hash_password('admin')),
        ('user', hash_password('user'))
    ]
    for username, password_hash in default_users:
        c.execute(
            "INSERT OR IGNORE INTO users (username, password) VALUES
