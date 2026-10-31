"""
Demo Data Seeder
Populates the Supabase database with realistic demo properties, owners, and customer accounts for immediate testing.
"""

from werkzeug.security import generate_password_hash
from config import Config
from database import get_supabase_admin, get_user_by_email


DEMO_PROPERTIES = [
    {
        "title": "Luxury 3BHK Sea-Facing Apartment in Bandra West",
        "property_type": "Apartment",
        "address": "402, Sea Green Heights, Carter Road, Bandra West",
        "city": "Mumbai",
        "locality": "Bandra West",
        "latitude": 19.0607,
        "longitude": 72.8258,
        "monthly_rent": 85000,
        "security_deposit": 250000,
        "bedrooms": 3,
        "bathrooms": 3,
        "balconies": 2,
        "area_sqft": 1650,
        "furnishing_status": "Furnished",
        "parking_available": True,
        "water_available": "24 Hours",
        "amenities": ["WiFi / High-Speed Internet", "Air Conditioning", "Swimming Pool", "Gym / Fitness Center", "Lift / Elevator", "24/7 Security & CCTV", "Modular Kitchen", "Balcony / Terrace"],
        "description": "Stunning sea-facing 3BHK apartment located in the prime locality of Carter Road, Bandra West. Equipped with designer Italian marble flooring, central AC, modular kitchen with dishwasher, and 2 designated covered car parking spaces.",
        "contact_phone": "+91 98201 12345",
        "approval_status": "approved",
        "is_active": True,
        "image_urls": [
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1000&q=80",
            "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1000&q=80",
            "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=80"
        ]
    },
    {
        "title": "Modern 2BHK Garden View Flat in Indiranagar",
        "property_type": "Apartment",
        "address": "12, 100 Feet Road, HAL 2nd Stage, Indiranagar",
        "city": "Bengaluru",
        "locality": "Indiranagar",
        "latitude": 12.9719,
        "longitude": 77.6412,
        "monthly_rent": 42000,
        "security_deposit": 120000,
        "bedrooms": 2,
        "bathrooms": 2,
        "balconies": 1,
        "area_sqft": 1150,
        "furnishing_status": "Semi-Furnished",
        "parking_available": True,
        "water_available": "24 Hours",
        "amenities": ["Power Backup / Inverter", "Lift / Elevator", "24/7 Security & CCTV", "Car Parking", "Modular Kitchen", "Balcony / Terrace"],
        "description": "Bright and airy 2BHK flat situated just minutes away from Indiranagar Metro Station. Wardrobes in both bedrooms, premium bathroom fittings, private balcony overlooking lush green avenue.",
        "contact_phone": "+91 98450 67890",
        "approval_status": "approved",
        "is_active": True,
        "image_urls": [
            "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=1000&q=80",
            "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=1000&q=80"
        ]
    },
    {
        "title": "Serene 4BHK Private Villa with Private Lawn & Pool",
        "property_type": "Villa",
        "address": "Villa 18, Palm Meadows, Whitefield",
        "city": "Bengaluru",
        "locality": "Whitefield",
        "latitude": 12.9698,
        "longitude": 77.7500,
        "monthly_rent": 120000,
        "security_deposit": 400000,
        "bedrooms": 4,
        "bathrooms": 5,
        "balconies": 3,
        "area_sqft": 3400,
        "furnishing_status": "Furnished",
        "parking_available": True,
        "water_available": "24 Hours",
        "amenities": ["Swimming Pool", "Gym / Fitness Center", "Club House", "Children Play Area", "Gated Community", "Air Conditioning", "WiFi / High-Speed Internet", "Power Backup / Inverter"],
        "description": "Luxurious duplex villa in the gated community of Palm Meadows. Expansive private garden, personal plunge pool, dedicated study/office room, and servant quarters.",
        "contact_phone": "+91 97110 54321",
        "approval_status": "approved",
        "is_active": True,
        "image_urls": [
            "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1000&q=80",
            "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=1000&q=80"
        ]
    },
    {
        "title": "Cozy 1BHK Studio Apartment near Cyber City",
        "property_type": "Studio Apartment",
        "address": "DLF Phase 2, Near Sikanderpur Metro Station",
        "city": "Gurugram",
        "locality": "DLF Phase 2",
        "latitude": 28.4862,
        "longitude": 77.0906,
        "monthly_rent": 24000,
        "security_deposit": 48000,
        "bedrooms": 1,
        "bathrooms": 1,
        "balconies": 1,
        "area_sqft": 580,
        "furnishing_status": "Furnished",
        "parking_available": True,
        "water_available": "24 Hours",
        "amenities": ["WiFi / High-Speed Internet", "Air Conditioning", "Power Backup / Inverter", "Lift / Elevator", "Modular Kitchen"],
        "description": "Fully furnished studio apartment ideal for IT professionals. Includes smart TV, refrigerator, microwave, queen size bed, work desk, and high-speed fiber internet.",
        "contact_phone": "+91 99100 98765",
        "approval_status": "approved",
        "is_active": True,
        "image_urls": [
            "https://images.unsplash.com/photo-1502005229762-ee152da92e06?auto=format&fit=crop&w=1000&q=80"
        ]
    },
    {
        "title": "Spacious 3BHK Independent Floor in Banjara Hills",
        "property_type": "Builder Floor",
        "address": "Road No. 12, Banjara Hills",
        "city": "Hyderabad",
        "locality": "Banjara Hills",
        "latitude": 17.4156,
        "longitude": 78.4350,
        "monthly_rent": 55000,
        "security_deposit": 150000,
        "bedrooms": 3,
        "bathrooms": 3,
        "balconies": 2,
        "area_sqft": 1950,
        "furnishing_status": "Semi-Furnished",
        "parking_available": True,
        "water_available": "Municipal Only",
        "amenities": ["24/7 Security & CCTV", "Power Backup / Inverter", "Lift / Elevator", "Modular Kitchen", "Car Parking"],
        "description": "Independent builder floor with separate entry and dedicated elevator. Peaceful residential neighborhood, close to international schools and hospitals.",
        "contact_phone": "+91 98490 11223",
        "approval_status": "pending",  # Demo pending listing for Admin testing
        "is_active": True,
        "image_urls": [
            "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1000&q=80"
        ]
    }
]


def seed_demo():
    print("=" * 60)
    print("  Seeding Demo Data into Supabase...")
    print("=" * 60)

    if not Config.is_supabase_configured():
        print("[ERROR] Supabase is not configured in .env. Please configure credentials first.")
        return

    supabase = get_supabase_admin()
    if not supabase:
        print("[ERROR] Could not connect to Supabase.")
        return

    # 1. Create or fetch Demo Owner
    owner_email = "owner@homerental.com"
    owner = get_user_by_email(owner_email)
    if not owner:
        print(f"Creating demo owner account: {owner_email}")
        res = supabase.table("users").insert({
            "name": "Rajesh Sharma (Owner)",
            "email": owner_email,
            "phone": "+91 98200 99887",
            "password_hash": generate_password_hash("Owner@12345"),
            "role": "owner"
        }).execute()
        owner = res.data[0]
    else:
        print(f"Found existing demo owner account: {owner_email}")

    # 2. Create or fetch Demo Customer
    customer_email = "customer@homerental.com"
    customer = get_user_by_email(customer_email)
    if not customer:
        print(f"Creating demo customer account: {customer_email}")
        res = supabase.table("users").insert({
            "name": "Priya Nair (Customer)",
            "email": customer_email,
            "phone": "+91 98111 22334",
            "password_hash": generate_password_hash("Customer@12345"),
            "role": "customer"
        }).execute()
        customer = res.data[0]
    else:
        print(f"Found existing demo customer account: {customer_email}")

    # 3. Create or fetch Demo Admin
    admin_email = "admin@homerental.com"
    admin = get_user_by_email(admin_email)
    if not admin:
        print(f"Creating demo admin account: {admin_email}")
        res = supabase.table("users").insert({
            "name": "System Administrator",
            "email": admin_email,
            "phone": "+91 99999 88888",
            "password_hash": generate_password_hash("Admin@12345"),
            "role": "admin"
        }).execute()
        admin = res.data[0]

    # 4. Insert Properties and Images
    owner_id = owner["id"]
    for p_data in DEMO_PROPERTIES:
        title = p_data["title"]
        # Check if already exists
        chk = supabase.table("properties").select("id").eq("title", title).execute()
        if chk.data and len(chk.data) > 0:
            print(f"  [SKIPPED] Property already exists: {title}")
            continue

        images = p_data.pop("image_urls", [])
        p_data["owner_id"] = owner_id

        try:
            prop_res = supabase.table("properties").insert(p_data).execute()
            if prop_res.data:
                prop_id = prop_res.data[0]["id"]
                print(f"  [CREATED] Property: {title}")
                # Insert images
                for idx, img_url in enumerate(images):
                    supabase.table("property_images").insert({
                        "property_id": prop_id,
                        "storage_path": f"demo/{prop_id}_{idx}.jpg",
                        "image_url": img_url,
                        "is_primary": (idx == 0)
                    }).execute()
        except Exception as e:
            print(f"  [ERROR] Failed to insert property '{title}': {e}")

    print("\n[SUCCESS] Demo data seeding completed successfully!")
    print("\nDemo Accounts for testing:")
    print("  Customer: customer@homerental.com / Customer@12345")
    print("  Owner:    owner@homerental.com / Owner@12345")
    print("  Admin:    admin@homerental.com / Admin@12345")


if __name__ == "__main__":
    seed_demo()
