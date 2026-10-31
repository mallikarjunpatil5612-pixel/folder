"""
Clear / Reset Database Script
Deletes all existing listings, rooms, favourites, enquiries, and non-admin data
so the website starts completely fresh without existing data.
"""

import sys
from config import Config
from database import get_supabase_admin

def clear_all_data(keep_admin=True):
    print("=" * 60)
    print("  Home Rental Management System - Clear Database")
    print("=" * 60)

    if not Config.is_supabase_configured():
        print("\n[ERROR] Supabase credentials not found in .env.")
        return

    supabase = get_supabase_admin()
    if not supabase:
        print("\n[ERROR] Failed to connect to Supabase.")
        return

    print("\nDeleting existing data across all tables...")

    try:
        # 1. Enquiries
        supabase.table("rental_enquiries").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("  [x] rental_enquiries cleared.")

        # 2. Favourites
        supabase.table("favourites").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("  [x] favourites cleared.")

        # 3. Rooms
        supabase.table("rooms").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("  [x] rooms cleared.")

        # 4. Property Images
        supabase.table("property_images").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("  [x] property_images cleared.")

        # 5. Properties
        supabase.table("properties").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("  [x] properties cleared.")

        # 6. Admin Logs
        supabase.table("admin_logs").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("  [x] admin_logs cleared.")

        # 7. Users
        if keep_admin:
            supabase.table("users").delete().neq("role", "admin").execute()
            print("  [x] users (non-admin) cleared (admin accounts preserved).")
        else:
            supabase.table("users").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            print("  [x] all users cleared.")

        print("\n[SUCCESS] All existing data has been cleared successfully!")
        print("Your Admin and Tenant portals are now completely empty and ready.")

    except Exception as e:
        print(f"\n[ERROR] Failed to clear data: {e}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete all existing data? (y/N): ").strip().lower()
    if confirm == "y":
        clear_all_data(keep_admin=True)
    else:
        print("Aborted.")
