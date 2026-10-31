# 🏠 Home Rental Management System

A complete, professional, responsive full-stack **Home Rental Website & Management System** built with **Python Flask**, **Supabase PostgreSQL**, **Supabase Storage**, and responsive HTML5/CSS3/JavaScript.

---

## 🌟 Key Features

- **Multi-Role Portal**:
  - 🏠 **Homeowner**: Add homes with full specifications, upload house photographs, add individual rooms, view approval status, track tenant enquiries.
  - 🔑 **Rental Manager**: View available owner homes, manage per-room rentals, set availability and room dimensions.
  - 👤 **Tenant / Customer**: Search and filter homes by city, budget, bedrooms, and furnishing; view interactive Leaflet maps, save favourites, and submit rental enquiries.
  - 🛡️ **Administrator**: Moderation dashboard with stats, pending approval queue (Approve / Reject with reason), user management (Activate / Suspend), and recent listings audit.
- **Supabase Integration**:
  - Direct connection using the official `supabase-py` Python SDK.
  - PostgreSQL schema with Row Level Security (RLS) policies, foreign keys, indexes, and triggers.
  - Supabase Storage bucket (`property-images`) for property photographs.
- **Security & Validation**:
  - Strict server-side input validation and file extension checking.
  - Secure password hashing using PBKDF2 / Scrypt via `werkzeug.security`.
  - CSRF protection across all state-mutating requests.
  - Role-based authorization preventing public users from registering as administrators.

---

## 📁 Project Structure

```text
home_rental/
├── app.py                   # Main Flask application and routes
├── config.py                # Environment configuration & constants
├── database.py              # Supabase database & storage operations
├── create_admin.py          # Secure CLI tool to create/reset administrator
├── seed_demo_data.py        # Seed script for demo homes, owners & tenants
├── schema.sql               # Complete Supabase PostgreSQL schema & RLS policies
├── requirements.txt         # Python package dependencies
├── .env                     # Local environment credentials
├── .env.example             # Template for environment variables
├── .gitignore               # Git ignore rules
├── run.ps1                  # One-terminal PowerShell launcher
├── README.md                # Documentation & Setup guide
├── static/
│   ├── css/
│   │   └── style.css        # Professional blue & white responsive stylesheet
│   └── js/
│       └── main.js          # Favourites toggle, photo preview, modal handlers
├── templates/
│   ├── base.html            # Core layout with navigation and footer
│   ├── index.html           # Home page with hero search and featured homes
│   ├── login.html           # Unified login for Tenants, Owners, Rentals
│   ├── register.html        # Registration with role selector
│   ├── admin_login.html     # Dedicated administrator portal login
│   ├── properties.html      # Search and browse properties with multi-filters
│   ├── property_details.html# Full details, rooms table, Leaflet map & enquiry
│   ├── add_property.html    # Add home form with photo uploads
│   ├── edit_property.html   # Edit home details and manage photos
│   ├── owner_dashboard.html # Owner view: My homes, added rooms, enquiries
│   ├── rental_dashboard.html# Rental view: Browse homes, add rooms
│   ├── customer_dashboard.html# Customer view: Saved favourites & enquiries
│   ├── admin_dashboard.html # Admin view: Stat cards, manage users, approvals
│   ├── contact.html         # Contact us & office locations
│   ├── about.html           # About the platform and roles
│   ├── 403.html             # Access forbidden error page
│   ├── 404.html             # Page not found error page
│   └── 500.html             # Server error page
└── tests/
    └── test_app.py          # Automated test suite
```

---

## ⚡ Quick Start: One-Terminal Execution (Windows PowerShell)

You can set up, install dependencies, and run the whole project using **ONE integrated terminal**:

```powershell
# Navigate to the project directory
cd "d:\mine project"

# Run the automated PowerShell setup and launcher script
.\run.ps1
```

Or execute the steps sequentially in the same terminal:

```powershell
# 1. Create a Python virtual environment
python -m venv venv

# 2. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install required packages
pip install -r requirements.txt

# 4. Start the Flask application
python app.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🗄️ Supabase Setup (3 Easy Steps)

### Step 1: Create a Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and create a free project.
2. Under **Project Settings -> API**, copy:
   - **Project URL**
   - **anon / public key**
   - **service_role key** (keep secret!)

### Step 2: Configure `.env`
Open the `.env` file in the project folder and paste your keys:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...your-anon-key...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...your-service-role-key...
FLASK_SECRET_KEY=9a4f61b7f920436bb53ef8d80c65d642398547b9ce34f2db0148ad65c9288e1a
PORT=5000
```

### Step 3: Run SQL Schema
1. In the Supabase Dashboard, click on **SQL Editor** in the left sidebar.
2. Click **New query**, open the `schema.sql` file from this project, copy its entire contents, paste it into the SQL editor, and click **Run**.
3. Under **Storage**, ensure the bucket named `property-images` has been created and set to **Public** for public image delivery.

---

## 🔑 Initial Administrator Setup & Demo Data

### 1. Create Your Administrator Account
Run the secure server-side admin creation tool in your terminal:
```powershell
python create_admin.py
```
Follow the interactive prompts to set your email and password.

### 2. Populate Demo Data (Optional)
To test the site immediately with realistic apartments, villas, and sample users:
```powershell
python seed_demo_data.py
```

**Default Demo Credentials:**
| Role | Email | Password |
|---|---|---|
| **Admin** | `admin@homerental.com` | `Admin@12345` |
| **Owner** | `owner@homerental.com` | `Owner@12345` |
| **Tenant** | `customer@homerental.com` | `Customer@12345` |

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:
```powershell
pytest -v
```
