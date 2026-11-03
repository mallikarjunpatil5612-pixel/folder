import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    # Flask settings
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "t")
    PORT = int(os.getenv("PORT", 5000))
    ENV = os.getenv("FLASK_ENV", "development")

    # Supabase credentials
    SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    # Image upload limits and configurations
    STORAGE_BUCKET_NAME = "property-images"
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB per image
    MAX_IMAGES_PER_PROPERTY = 10

    # Role definitions matching project flow: Customer (Tenant), Owner, Rental Manager, Admin
    ROLE_CUSTOMER = "customer"
    ROLE_OWNER = "owner"
    ROLE_RENTAL = "rental"
    ROLE_ADMIN = "admin"
    ALLOWED_REGISTRATION_ROLES = [ROLE_CUSTOMER, ROLE_OWNER]
    ADMIN_EMAIL = "mallikarjunpatil5612@gmail.com"

    # Property Constants
    PROPERTY_TYPES = [
        "Apartment",
        "Independent House",
        "Villa",
        "Studio Apartment",
        "Penthouse",
        "Duplex",
        "Builder Floor",
    ]

    ROOM_TYPES = [
        "Bedroom",
        "Master Bedroom",
        "Guest Bedroom",
        "Hall",
        "Kitchen",
        "Studio Room",
        "Single Room"
    ]

    FURNISHING_STATUSES = [
        "Furnished",
        "Semi-Furnished",
        "Unfurnished",
    ]

    WATER_OPTIONS = [
        "24 Hours",
        "Morning & Evening",
        "Borewell + Municipal",
        "Municipal Only",
    ]

    STANDARD_AMENITIES = [
        "WiFi / High-Speed Internet",
        "Air Conditioning",
        "Swimming Pool",
        "Gym / Fitness Center",
        "Lift / Elevator",
        "Power Backup / Inverter",
        "24/7 Security & CCTV",
        "Car Parking",
        "Club House",
        "Children Play Area",
        "Gated Community",
        "Modular Kitchen",
        "Balcony / Terrace",
        "Pet Friendly",
        "Fire Safety System",
    ]

    @classmethod
    def is_supabase_configured(cls) -> bool:
        """Returns True if the required Supabase URL and service role key are populated with real values."""
        if not cls.SUPABASE_URL or not cls.SUPABASE_SERVICE_ROLE_KEY:
            return False
        if "your-project-id" in cls.SUPABASE_URL or "your-service-role-key" in cls.SUPABASE_SERVICE_ROLE_KEY:
            return False
        return True
