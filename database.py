import io
import mimetypes
import os
import uuid
from datetime import datetime
from config import Config

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

_supabase_admin_client = None
_supabase_anon_client = None


def get_supabase_admin() -> Client:
    """Returns the Supabase client initialized with the SERVICE ROLE KEY for backend operations."""
    global _supabase_admin_client
    if _supabase_admin_client is not None:
        return _supabase_admin_client

    if not Config.is_supabase_configured():
        return None

    if create_client is None:
        return None

    try:
        _supabase_admin_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_SERVICE_ROLE_KEY
        )
        return _supabase_admin_client
    except Exception as e:
        print(f"[DATABASE] Error initializing Supabase Admin Client: {e}")
        return None


def get_supabase_anon() -> Client:
    """Returns the Supabase client initialized with the PUBLIC ANON KEY."""
    global _supabase_anon_client
    if _supabase_anon_client is not None:
        return _supabase_anon_client

    if not Config.is_supabase_configured() or not Config.SUPABASE_ANON_KEY:
        return None

    if create_client is None:
        return None

    try:
        _supabase_anon_client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_ANON_KEY
        )
        return _supabase_anon_client
    except Exception as e:
        print(f"[DATABASE] Error initializing Supabase Anon Client: {e}")
        return None


# ============================================================================
# USERS CRUD
# ============================================================================

def get_user_by_email(email: str):
    supabase = get_supabase_admin()
    if not supabase:
        return None
    try:
        res = supabase.table("users").select("*").ilike("email", email.strip()).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        print(f"[DATABASE ERROR] get_user_by_email: {e}")
        return None


def get_user_by_id(user_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return None
    try:
        res = supabase.table("users").select("id, name, email, phone, role, status, created_at").eq("id", user_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        print(f"[DATABASE ERROR] get_user_by_id: {e}")
        return None


def create_user(name: str, email: str, phone: str, password_hash: str, role: str):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase credentials not configured in .env.")

    if role not in Config.ALLOWED_REGISTRATION_ROLES and role != Config.ROLE_ADMIN:
        role = Config.ROLE_CUSTOMER

    payload = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "phone": phone.strip() if phone else None,
        "password_hash": password_hash,
        "role": role,
        "status": "active"
    }

    try:
        res = supabase.table("users").insert(payload).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise RuntimeError("Failed to create user record.")
    except Exception as e:
        print(f"[DATABASE ERROR] create_user: {e}")
        raise e


def get_all_users():
    supabase = get_supabase_admin()
    if not supabase:
        return []
    try:
        res = supabase.table("users").select("id, name, email, phone, role, status, created_at").order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[DATABASE ERROR] get_all_users: {e}")
        return []


def update_user_status(user_id: str, new_status: str):
    supabase = get_supabase_admin()
    if not supabase:
        return False
    try:
        supabase.table("users").update({"status": new_status}).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"[DATABASE ERROR] update_user_status: {e}")
        return False


def update_user(user_id: str, updates: dict):
    """Updates user information (name, email, phone, role, status)."""
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    try:
        res = supabase.table("users").update(updates).eq("id", user_id).execute()
        return res.data
    except Exception as e:
        print(f"[DATABASE ERROR] update_user: {e}")
        raise e


def delete_user(user_id: str):
    """Permanently deletes a user from the database."""
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    try:
        res = supabase.table("users").delete().eq("id", user_id).execute()
        return res.data
    except Exception as e:
        print(f"[DATABASE ERROR] delete_user: {e}")
        raise e


# ============================================================================
# PROPERTIES CRUD & SEARCH
# ============================================================================

def get_properties(
    city=None,
    locality=None,
    min_rent=None,
    max_rent=None,
    bedrooms=None,
    property_type=None,
    furnishing=None,
    owner_id=None,
    approval_status=None,
    is_active=None,
    sort_by="newest",
    limit=50,
    offset=0
):
    supabase = get_supabase_admin()
    if not supabase:
        return []

    try:
        query = supabase.table("properties").select("*, property_images(id, storage_path, image_url, is_primary), rooms(id, room_type, size, price, availability)")

        if approval_status is not None:
            query = query.eq("approval_status", approval_status)
        elif owner_id is None:
            query = query.eq("approval_status", "approved")

        if is_active is not None:
            query = query.eq("is_active", is_active)
        elif owner_id is None:
            query = query.eq("is_active", True)

        if owner_id:
            query = query.eq("owner_id", owner_id)

        if city:
            query = query.ilike("city", f"%{city.strip()}%")

        if locality:
            query = query.ilike("locality", f"%{locality.strip()}%")

        if min_rent is not None and str(min_rent).strip() != "":
            try:
                query = query.gte("monthly_rent", float(min_rent))
            except ValueError:
                pass

        if max_rent is not None and str(max_rent).strip() != "":
            try:
                query = query.lte("monthly_rent", float(max_rent))
            except ValueError:
                pass

        if bedrooms is not None and str(bedrooms).strip() != "":
            try:
                bed_val = int(bedrooms)
                if bed_val >= 4:
                    query = query.gte("bedrooms", 4)
                else:
                    query = query.eq("bedrooms", bed_val)
            except ValueError:
                pass

        if property_type and property_type.strip() != "":
            query = query.eq("property_type", property_type.strip())

        if furnishing and furnishing.strip() != "":
            query = query.eq("furnishing_status", furnishing.strip())

        if sort_by == "rent_low_high":
            query = query.order("monthly_rent", desc=False)
        elif sort_by == "rent_high_low":
            query = query.order("monthly_rent", desc=True)
        elif sort_by == "area_high":
            query = query.order("area_sqft", desc=True)
        else:
            query = query.order("created_at", desc=True)

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        res = query.execute()
        return res.data or []
    except Exception as e:
        print(f"[DATABASE ERROR] get_properties: {e}")
        return []


def get_property_by_id(property_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return None

    try:
        res = supabase.table("properties").select(
            "*, property_images(id, storage_path, image_url, is_primary, created_at), rooms(id, room_type, size, price, availability, created_at), users(id, name, email, phone)"
        ).eq("id", property_id).limit(1).execute()

        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        print(f"[DATABASE ERROR] get_property_by_id: {e}")
        return None


def create_property(prop_dict: dict):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase connection not active.")

    if "approval_status" not in prop_dict or not prop_dict["approval_status"]:
        prop_dict["approval_status"] = "pending"
    if "is_active" not in prop_dict:
        prop_dict["is_active"] = True

    try:
        res = supabase.table("properties").insert(prop_dict).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        raise RuntimeError("Could not insert property record.")
    except Exception as e:
        print(f"[DATABASE ERROR] create_property: {e}")
        raise e


def update_property(property_id: str, updates: dict):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase connection not active.")

    try:
        res = supabase.table("properties").update(updates).eq("id", property_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        print(f"[DATABASE ERROR] update_property: {e}")
        raise e


def delete_property(property_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase connection not active.")

    try:
        img_res = supabase.table("property_images").select("storage_path").eq("property_id", property_id).execute()
        if img_res.data:
            storage_paths = [img["storage_path"] for img in img_res.data if img.get("storage_path")]
            if storage_paths:
                try:
                    supabase.storage.from_(Config.STORAGE_BUCKET_NAME).remove(storage_paths)
                except Exception as se:
                    print(f"[STORAGE WARNING] Remove image error: {se}")

        supabase.table("properties").delete().eq("id", property_id).execute()
        return True
    except Exception as e:
        print(f"[DATABASE ERROR] delete_property: {e}")
        raise e


# ============================================================================
# ROOMS OPERATIONS (Per-room rentals for Owner and Rental manager)
# ============================================================================

def create_room(property_id: str, created_by: str, room_type: str, size: str, price: float, availability: str = "Available"):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase connection not active.")
    try:
        payload = {
            "property_id": property_id,
            "created_by": created_by,
            "room_type": room_type,
            "size": size,
            "price": float(price),
            "availability": availability
        }
        res = supabase.table("rooms").insert(payload).execute()
        return res.data[0] if res.data else payload
    except Exception as e:
        print(f"[DATABASE ERROR] create_room: {e}")
        raise e


def get_rooms_for_property(property_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return []
    try:
        res = supabase.table("rooms").select("*").eq("property_id", property_id).order("created_at", desc=False).execute()
        return res.data or []
    except Exception as e:
        print(f"[DATABASE ERROR] get_rooms_for_property: {e}")
        return []


def update_room(room_id: str, updates: dict):
    supabase = get_supabase_admin()
    if not supabase:
        return False
    try:
        supabase.table("rooms").update(updates).eq("id", room_id).execute()
        return True
    except Exception as e:
        print(f"[DATABASE ERROR] update_room: {e}")
        return False


def delete_room(room_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return False
    try:
        supabase.table("rooms").delete().eq("id", room_id).execute()
        return True
    except Exception as e:
        print(f"[DATABASE ERROR] delete_room: {e}")
        return False


# ============================================================================
# PROPERTY IMAGES & SUPABASE STORAGE
# ============================================================================

def upload_property_image(file_storage, property_id: str, is_primary: bool = False):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase is not configured.")

    filename = file_storage.filename or "image.jpg"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
    if ext not in Config.ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"Invalid file extension '.{ext}'. Allowed: {', '.join(Config.ALLOWED_IMAGE_EXTENSIONS)}")

    unique_name = f"{property_id}/{uuid.uuid4().hex}.{ext}"
    file_bytes = file_storage.read()
    if len(file_bytes) > Config.MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"File size exceeds maximum allowed ({Config.MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB)")

    mime_type = mimetypes.guess_type(filename)[0] or "image/jpeg"

    try:
        supabase.storage.from_(Config.STORAGE_BUCKET_NAME).upload(
            path=unique_name,
            file=file_bytes,
            file_options={"content-type": mime_type, "upsert": "true"}
        )
    except Exception as e:
        print(f"[STORAGE ERROR] Upload failed: {e}")

    try:
        public_url_resp = supabase.storage.from_(Config.STORAGE_BUCKET_NAME).get_public_url(unique_name)
        image_url = public_url_resp if isinstance(public_url_resp, str) else public_url_resp.get("publicURL", "")
    except Exception:
        image_url = f"{Config.SUPABASE_URL}/storage/v1/object/public/{Config.STORAGE_BUCKET_NAME}/{unique_name}"

    try:
        img_record = {
            "property_id": property_id,
            "storage_path": unique_name,
            "image_url": image_url,
            "is_primary": is_primary
        }
        res = supabase.table("property_images").insert(img_record).execute()
        return res.data[0] if res.data else img_record
    except Exception as e:
        print(f"[DATABASE ERROR] Could not save property_image record: {e}")
        raise e


def delete_property_image(image_id: str, property_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return False
    try:
        img_res = supabase.table("property_images").select("*").eq("id", image_id).eq("property_id", property_id).limit(1).execute()
        if not img_res.data:
            return False
        img_data = img_res.data[0]
        storage_path = img_data.get("storage_path")
        if storage_path:
            try:
                supabase.storage.from_(Config.STORAGE_BUCKET_NAME).remove([storage_path])
            except Exception as se:
                print(f"[STORAGE WARNING] Image remove warning: {se}")

        supabase.table("property_images").delete().eq("id", image_id).execute()
        return True
    except Exception as e:
        print(f"[DATABASE ERROR] delete_property_image: {e}")
        return False


# ============================================================================
# FAVOURITES
# ============================================================================

def toggle_favourite(customer_id: str, property_id: str) -> bool:
    supabase = get_supabase_admin()
    if not supabase:
        return False
    try:
        check = supabase.table("favourites").select("id").eq("customer_id", customer_id).eq("property_id", property_id).execute()
        if check.data and len(check.data) > 0:
            fav_id = check.data[0]["id"]
            supabase.table("favourites").delete().eq("id", fav_id).execute()
            return False
        else:
            supabase.table("favourites").insert({
                "customer_id": customer_id,
                "property_id": property_id
            }).execute()
            return True
    except Exception as e:
        print(f"[DATABASE ERROR] toggle_favourite: {e}")
        return False


def is_favourite(customer_id: str, property_id: str) -> bool:
    supabase = get_supabase_admin()
    if not supabase or not customer_id:
        return False
    try:
        res = supabase.table("favourites").select("id").eq("customer_id", customer_id).eq("property_id", property_id).limit(1).execute()
        return bool(res.data and len(res.data) > 0)
    except Exception:
        return False


def get_customer_favourites(customer_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return []
    try:
        res = supabase.table("favourites").select(
            "id, created_at, properties(*, property_images(id, image_url, is_primary))"
        ).eq("customer_id", customer_id).order("created_at", desc=True).execute()

        fav_list = []
        if res.data:
            for item in res.data:
                prop = item.get("properties")
                if prop:
                    fav_list.append(prop)
        return fav_list
    except Exception as e:
        print(f"[DATABASE ERROR] get_customer_favourites: {e}")
        return []


# ============================================================================
# RENTAL ENQUIRIES / BOOKINGS
# ============================================================================

def create_rental_enquiry(property_id: str, customer_id: str, owner_id: str, message: str, room_id: str = None):
    supabase = get_supabase_admin()
    if not supabase:
        raise RuntimeError("Supabase connection not active.")
    try:
        payload = {
            "property_id": property_id,
            "customer_id": customer_id,
            "owner_id": owner_id,
            "room_id": room_id,
            "message": message.strip(),
            "status": "pending"
        }
        res = supabase.table("rental_enquiries").insert(payload).execute()
        return res.data[0] if res.data else payload
    except Exception as e:
        print(f"[DATABASE ERROR] create_rental_enquiry: {e}")
        raise e


def get_enquiries_for_owner(owner_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return []
    try:
        res = supabase.table("rental_enquiries").select(
            "*, properties(id, title, city, monthly_rent), rooms(id, room_type, price)"
        ).eq("owner_id", owner_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[DATABASE ERROR] get_enquiries_for_owner: {e}")
        return []


def get_enquiries_for_customer(customer_id: str):
    supabase = get_supabase_admin()
    if not supabase:
        return []
    try:
        res = supabase.table("rental_enquiries").select(
            "*, properties(id, title, city, monthly_rent, contact_phone), rooms(id, room_type, price)"
        ).eq("customer_id", customer_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        print(f"[DATABASE ERROR] get_enquiries_for_customer: {e}")
        return []


def update_enquiry_status(enquiry_id: str, new_status: str, owner_id: str = None):
    supabase = get_supabase_admin()
    if not supabase:
        return False
    try:
        query = supabase.table("rental_enquiries").update({"status": new_status}).eq("id", enquiry_id)
        if owner_id:
            query = query.eq("owner_id", owner_id)
        res = query.execute()
        return bool(res.data and len(res.data) > 0)
    except Exception as e:
        print(f"[DATABASE ERROR] update_enquiry_status: {e}")
        return False


# ============================================================================
# ADMIN ACTIONS & LOGS
# ============================================================================

def log_admin_action(admin_id: str, action: str, details: str = None):
    supabase = get_supabase_admin()
    if not supabase:
        return
    try:
        supabase.table("admin_logs").insert({
            "admin_id": admin_id,
            "action": action,
            "details": details or ""
        }).execute()
    except Exception as e:
        print(f"[ADMIN LOG ERROR]: {e}")


def get_admin_logs(limit: int = 50):
    supabase = get_supabase_admin()
    if not supabase:
        return []
    try:
        res = supabase.table("admin_logs").select("*, users(name, email)").order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"[DATABASE ERROR] get_admin_logs: {e}")
        return []


def get_admin_dashboard_stats():
    supabase = get_supabase_admin()
    if not supabase:
        return {
            "total_users": 0,
            "total_customers": 0,
            "total_owners": 0,
            "total_properties": 0,
            "pending_approvals": 0,
            "approved_properties": 0,
            "rejected_properties": 0,
            "total_enquiries": 0
        }

    stats = {}
    try:
        u_res = supabase.table("users").select("role").execute()
        users = u_res.data or []
        stats["total_users"] = len(users)
        stats["total_customers"] = sum(1 for u in users if u.get("role") == "customer")
        stats["total_owners"] = sum(1 for u in users if u.get("role") == "owner")
        stats["total_rentals"] = sum(1 for u in users if u.get("role") == "rental")
        stats["total_admins"] = sum(1 for u in users if u.get("role") == "admin")

        p_res = supabase.table("properties").select("approval_status, is_active").execute()
        props = p_res.data or []
        stats["total_properties"] = len(props)
        stats["pending_approvals"] = sum(1 for p in props if p.get("approval_status") == "pending")
        stats["approved_properties"] = sum(1 for p in props if p.get("approval_status") == "approved")
        stats["rejected_properties"] = sum(1 for p in props if p.get("approval_status") == "rejected")
        stats["inactive_properties"] = sum(1 for p in props if not p.get("is_active"))

        e_res = supabase.table("rental_enquiries").select("id").execute()
        stats["total_enquiries"] = len(e_res.data or [])

        return stats
    except Exception as e:
        print(f"[DATABASE ERROR] get_admin_dashboard_stats: {e}")
        return {
            "total_users": 0,
            "total_customers": 0,
            "total_owners": 0,
            "total_properties": 0,
            "pending_approvals": 0,
            "approved_properties": 0,
            "rejected_properties": 0,
            "total_enquiries": 0
        }
