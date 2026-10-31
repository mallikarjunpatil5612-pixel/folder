"""
Create Administrator Script
Allows server administrators to create or reset the initial administrator account securely.
"""

import sys
import getpass
from werkzeug.security import generate_password_hash
from config import Config
from database import get_supabase_admin, get_user_by_email


def setup_admin(email=None, name=None, phone=None, password=None):
    print("=" * 60)
    print("  Home Rental Management System - Create Administrator Account")
    print("=" * 60)

    if not Config.is_supabase_configured():
        print("\n[ERROR] Supabase credentials are not configured in your .env file!")
        print("Please open .env and set valid values for:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_SERVICE_ROLE_KEY")
        print("\nAfter configuring .env and executing schema.sql in Supabase SQL editor, rerun this script.")
        return False

    supabase = get_supabase_admin()
    if not supabase:
        print("\n[ERROR] Failed to establish Supabase client connection.")
        return False

    # Collect inputs if not provided
    if not email:
        email = input("Admin Email: ").strip()
    if not email:
        print("[ERROR] Email cannot be empty.")
        return False

    # Check if user already exists
    existing = get_user_by_email(email)
    if existing:
        print(f"\n[INFO] User with email '{email}' already exists (Current Role: {existing.get('role')}).")
        choice = input("Do you want to promote this user to 'admin' and update their password? (y/N): ").strip().lower()
        if choice != 'y':
            print("Aborted.")
            return False

    if not name:
        name = input("Admin Full Name [Default: Administrator]: ").strip() or "Administrator"
    if not phone:
        phone = input("Admin Phone Number (optional): ").strip() or None

    if not password:
        password = getpass.getpass("Enter Admin Password (min 8 characters): ")
        confirm_password = getpass.getpass("Confirm Admin Password: ")
        if password != confirm_password:
            print("[ERROR] Passwords do not match.")
            return False

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        return False

    password_hash = generate_password_hash(password)

    try:
        if existing:
            # Update user role to admin and set new password
            res = supabase.table("users").update({
                "name": name,
                "phone": phone,
                "password_hash": password_hash,
                "role": Config.ROLE_ADMIN
            }).eq("id", existing["id"]).execute()
            print(f"\n[SUCCESS] User '{email}' was successfully promoted to Administrator!")
        else:
            # Insert brand new admin
            res = supabase.table("users").insert({
                "name": name,
                "email": email.lower(),
                "phone": phone,
                "password_hash": password_hash,
                "role": Config.ROLE_ADMIN
            }).execute()
            print(f"\n[SUCCESS] Administrator account for '{email}' created successfully!")

        print("\nYou can now login via /admin/login or /login.")
        return True
    except Exception as e:
        print(f"\n[DATABASE ERROR] Failed to create or update administrator: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # CLI usage: python create_admin.py <email> <password> [name] [phone]
        _email = sys.argv[1]
        _password = sys.argv[2]
        _name = sys.argv[3] if len(sys.argv) > 3 else "Administrator"
        _phone = sys.argv[4] if len(sys.argv) > 4 else None
        setup_admin(email=_email, password=_password, name=_name, phone=_phone)
    else:
        setup_admin()
