# 🚚 TrackSwift: Online Logistics Platform

TrackSwift is a full-featured, user-friendly web application built with **Streamlit** for managing logistics operations. It serves as an online platform for handling shipments, orders, tracking, and analytics. The app includes user authentication, role-based access (admin vs. user), a local SQLite database for persistence, and interactive dashboards for reporting. It's self-contained, responsive, and designed for ease of use—no external APIs or complex setups required.

This project demonstrates core logistics functionalities like adding shipments, real-time tracking, order management, and performance analytics. It's ideal for small businesses, demos, or learning purposes. The app simulates secure integration (e.g., role-based controls) and customer portals.

## Key Features

- **User  Authentication**: Simple login system with default users (`admin/admin` for full access, `user/user` for basic access). Uses session state for persistence.
- **Order & Shipment Management**:
  - Add new shipments with auto-generated tracking IDs (UUID-based).
  - View and filter all orders/shipments in a table (editable for admins).
- **Real-Time Shipment Tracking**: Search by tracking ID to view details and update status (admin-only).
- **Customer Portal & Notifications**: Personalized profile view with user-specific metrics and shipments.
- **Analytics & Reporting Dashboard**:
  - Key metrics (total/pending/in-transit/delivered shipments).
  - Interactive pie charts for status distribution (using Altair).
  - Customizable reports (daily/weekly/monthly) with line charts and filtered dataframes.
- **Secure Integration and Access Control**: Role-based permissions (e.g., admins can edit/update; users can only view/add). Parameterized SQL queries prevent injection. Simulates ERP/accounting integration via local DB.
- **UX Enhancements**: Sidebar navigation, emojis/icons, forms with validation, error handling (e.g., "Shipment not found"), and Streamlit's wide layout for responsiveness.
- **Data Persistence**: Local SQLite database (`logistics.db`) with sample data (8 shipments, 2 users) auto-initialized on first run.

The app is modular: Main logic in `TrackSwift.py`, utilities in `App_utils.py`.

Built with blood, sweat, and tears using Streamlit. Questions? Email us at FantasticF4UR@gmail.com

---

*Last Updated: 05/10/2025*  
*Authors: Keith Ivan Del Carmen, Mykel Tristan Detrago, Joaquin Olarte, Enrico Lee Pitular*
