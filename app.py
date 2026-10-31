import os
import re
import secrets
from functools import wraps
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    abort,
)
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
import database as db

# Initialize Flask Application
app = Flask(__name__)
app.config.from_object(Config)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ============================================================================
# CSRF PROTECTION & TEMPLATE CONTEXT HELPERS
# ============================================================================

@app.before_request
def csrf_protect():
    """Generates CSRF token for sessions and verifies on mutating requests."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        req_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not req_token or req_token != session.get("csrf_token"):
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"error": "Invalid or missing CSRF token"}), 400
            flash("Security check failed: Invalid CSRF token. Please try again.", "danger")
            return redirect(request.referrer or url_for("home"))


@app.context_processor
def inject_global_data():
    """Injects user session, configuration constants, and CSRF token into all templates."""
    current_user = None
    if "user_id" in session:
        current_user = {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "email": session.get("user_email"),
            "role": session.get("user_role"),
        }

    return {
        "current_user": current_user,
        "csrf_token": session.get("csrf_token", ""),
        "config": Config,
        "is_supabase_ready": Config.is_supabase_configured(),
        "property_types": Config.PROPERTY_TYPES,
        "room_types": Config.ROOM_TYPES,
        "furnishing_statuses": Config.FURNISHING_STATUSES,
        "standard_amenities": Config.STANDARD_AMENITIES,
        "water_options": Config.WATER_OPTIONS,
    }


# ============================================================================
# AUTHENTICATION & ROLE-BASED ACCESS CONTROL DECORATORS
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login", next=request.url))
            user_role = session.get("user_role")
            if user_role not in allowed_roles:
                return render_template("403.html", message=f"Access denied. Required role: {', '.join(allowed_roles)}."), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# PUBLIC ROUTES (HOME, PROPERTIES, CONTACT)
# ============================================================================

@app.route("/")
def index():
    """First entry point: opens directly to the Sign Up page."""
    if "user_id" in session:
        if session.get("user_role") == Config.ROLE_ADMIN:
            return redirect(url_for("admin_dashboard"))
        elif session.get("user_role") == Config.ROLE_CUSTOMER:
            return redirect(url_for("customer_dashboard"))
        return redirect(url_for("home"))
    return redirect(url_for("register"))


@app.route("/home")
def home():
    """Home landing page with hero search bar and latest approved rental listings."""
    if session.get("user_role") == Config.ROLE_CUSTOMER:
        return redirect(url_for("customer_dashboard"))
    elif session.get("user_role") == Config.ROLE_ADMIN:
        return redirect(url_for("admin_dashboard"))
    featured_properties = db.get_properties(approval_status="approved", is_active=True, limit=6)
    return render_template("index.html", properties=featured_properties)


@app.route("/properties")
@app.route("/browse")
def properties_listing():
    """Search and browse all approved active properties with dynamic filters."""
    city = request.args.get("city", "").strip()
    locality = request.args.get("locality", "").strip()
    min_rent = request.args.get("min_rent", "").strip()
    max_rent = request.args.get("max_rent", "").strip()
    bedrooms = request.args.get("bedrooms", "").strip()
    property_type = request.args.get("property_type", "").strip()
    furnishing = request.args.get("furnishing", "").strip()
    sort_by = request.args.get("sort_by", "newest").strip()

    properties = db.get_properties(
        city=city or None,
        locality=locality or None,
        min_rent=min_rent or None,
        max_rent=max_rent or None,
        bedrooms=bedrooms or None,
        property_type=property_type or None,
        furnishing=furnishing or None,
        approval_status="approved",
        is_active=True,
        sort_by=sort_by,
        limit=60
    )

    user_fav_ids = set()
    if session.get("user_role") == Config.ROLE_CUSTOMER and "user_id" in session:
        favs = db.get_customer_favourites(session["user_id"])
        user_fav_ids = {p["id"] for p in favs if p and "id" in p}

    return render_template(
        "properties.html",
        properties=properties,
        user_fav_ids=user_fav_ids,
        filters={
            "city": city,
            "locality": locality,
            "min_rent": min_rent,
            "max_rent": max_rent,
            "bedrooms": bedrooms,
            "property_type": property_type,
            "furnishing": furnishing,
            "sort_by": sort_by,
        }
    )


@app.route("/properties/<property_id>")
def property_details(property_id):
    """Detailed view for a single property with gallery, rooms, amenities, Leaflet map, and enquiry form."""
    prop = db.get_property_by_id(property_id)
    if not prop:
        flash("The requested property listing was not found.", "danger")
        return render_template("404.html"), 404

    is_owner = session.get("user_id") == prop.get("owner_id")
    is_admin = session.get("user_role") == Config.ROLE_ADMIN
    is_rental = session.get("user_role") == Config.ROLE_RENTAL

    if not (is_owner or is_admin or is_rental):
        if prop.get("approval_status") != "approved" or not prop.get("is_active"):
            flash("This property listing is currently pending approval or inactive.", "info")
            return redirect(url_for("properties_listing"))

    is_fav = False
    if session.get("user_role") == Config.ROLE_CUSTOMER and "user_id" in session:
        is_fav = db.is_favourite(session["user_id"], property_id)

    rooms = db.get_rooms_for_property(property_id)

    return render_template(
        "property_details.html",
        property=prop,
        rooms=rooms,
        is_favourite=is_fav,
        is_owner=is_owner,
        is_admin=is_admin,
        is_rental=is_rental
    )


@app.route("/about")
def about():
    """About us page."""
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page with message form and FAQs."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            flash("Please fill in all required fields.", "danger")
            return render_template("contact.html", name=name, email=email, subject=subject, message=message)

        flash("Thank you for contacting Home Rental! Our team will respond to your inquiry shortly.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")


# ============================================================================
# USER AUTHENTICATION (REGISTER, LOGIN, LOGOUT, ADMIN LOGIN)
# ============================================================================

@app.route("/tenant/register", methods=["GET", "POST"])
@app.route("/register/tenant", methods=["GET", "POST"])
def tenant_register():
    """Dedicated Tenant Registration Route."""
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not name or len(name) < 2:
            errors.append("Full Name must be at least 2 characters.")

        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Please enter a valid email address.")

        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("tenant_register.html", name=name, email=email, phone=phone)

        try:
            existing = db.get_user_by_email(email)
            if existing:
                flash("An account with this email address already exists. Please sign in.", "warning")
                return redirect(url_for("tenant_login"))

            password_hash = generate_password_hash(password)
            new_user = db.create_user(name, email, phone, password_hash, Config.ROLE_CUSTOMER)

            flash(f"Account created successfully for {new_user['name']}! Please sign in with your email and password.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Registration error: {str(e)}", "danger")
            return render_template("tenant_register.html", name=name, email=email, phone=phone)

    return render_template("tenant_register.html")


@app.route("/owner/register", methods=["GET", "POST"])
@app.route("/register/owner", methods=["GET", "POST"])
def owner_register():
    """Dedicated Homeowner Registration Route."""
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not name or len(name) < 2:
            errors.append("Full Name must be at least 2 characters.")

        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Please enter a valid email address.")

        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("owner_register.html", name=name, email=email, phone=phone)

        try:
            existing = db.get_user_by_email(email)
            if existing:
                flash("An account with this email address already exists. Please sign in.", "warning")
                return redirect(url_for("owner_login"))

            password_hash = generate_password_hash(password)
            new_user = db.create_user(name, email, phone, password_hash, Config.ROLE_OWNER)

            session["user_id"] = new_user["id"]
            session["user_name"] = new_user["name"]
            session["user_email"] = new_user["email"]
            session["user_role"] = new_user["role"]

            flash(f"Welcome, {new_user['name']}! Your Homeowner account was created successfully.", "success")
            return redirect(url_for("home"))
        except Exception as e:
            flash(f"Registration error: {str(e)}", "danger")
            return render_template("owner_register.html", name=name, email=email, phone=phone)

    return render_template("owner_register.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration entrypoint directing to separate Tenant or Owner pages."""
    role = request.args.get("role", "").strip().lower()
    if role == "owner":
        return redirect(url_for("owner_register"))
    elif role in ("customer", "tenant"):
        return redirect(url_for("tenant_register"))
    
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        posted_role = request.form.get("role", "customer").strip().lower()
        if posted_role == "owner":
            return owner_register()
        return tenant_register()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Unified user login directing each user to their appropriate dashboard."""
    if "user_id" in session:
        return redirect(url_for("redirect_user_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        next_url = request.args.get("next")

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html", email=email)

        user = db.get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template("login.html", email=email)

        if user.get("status") == "suspended":
            flash("Your account has been suspended by an administrator. Please contact support.", "danger")
            return render_template("login.html", email=email)

        user_role = user.get("role") or Config.ROLE_CUSTOMER
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = user_role

        flash(f"Welcome back, {user['name']}!", "success")
        if next_url:
            return redirect(next_url)

        if user_role == Config.ROLE_ADMIN:
            return redirect(url_for("admin_dashboard"))
        elif user_role == Config.ROLE_OWNER:
            return redirect(url_for("owner_dashboard"))
        elif user_role == Config.ROLE_RENTAL:
            return redirect(url_for("rental_dashboard"))
        return redirect(url_for("customer_dashboard"))

    return render_template("login.html")


@app.route("/owner/login", methods=["GET", "POST"])
@app.route("/login/owner", methods=["GET", "POST"])
def owner_login():
    """Redirect to unified clean login."""
    return redirect(url_for("login"))


@app.route("/tenant/login", methods=["GET", "POST"])
@app.route("/login/tenant", methods=["GET", "POST"])
def tenant_login():
    """Redirect to unified clean login."""
    return redirect(url_for("login"))



@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Dedicated administrative login portal."""
    if "user_id" in session:
        if session.get("user_role") == Config.ROLE_ADMIN:
            return redirect(url_for("admin_dashboard"))
        csrf = session.get("csrf_token")
        session.clear()
        if csrf:
            session["csrf_token"] = csrf

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = db.get_user_by_email(email)
        if not user or user.get("role") != Config.ROLE_ADMIN or not check_password_hash(user["password_hash"], password):
            flash("Access denied. Invalid administrator credentials.", "danger")
            return render_template("admin_login.html", email=email)

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["user_role"] = Config.ROLE_ADMIN

        db.log_admin_action(user["id"], "ADMIN_LOGIN", f"Admin {user['email']} logged into portal.")
        flash("Administrator authenticated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html")


@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():
    """Administrator Registration Route."""
    if "user_id" in session:
        if session.get("user_role") == Config.ROLE_ADMIN:
            return redirect(url_for("admin_dashboard"))
        csrf = session.get("csrf_token")
        session.clear()
        if csrf:
            session["csrf_token"] = csrf

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not name or len(name) < 2:
            errors.append("Admin Full Name must be at least 2 characters.")

        if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors.append("Please enter a valid email address.")

        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("admin_register.html", name=name, email=email, phone=phone)

        try:
            existing = db.get_user_by_email(email)
            if existing:
                if existing.get("role") == Config.ROLE_ADMIN:
                    flash("An administrator account with this email address already exists. Please sign in.", "info")
                    return redirect(url_for("admin_login"))
                else:
                    # User was previously a tenant/customer or owner; upgrade them to Administrator
                    password_hash = generate_password_hash(password)
                    db.update_user(existing["id"], {
                        "name": name,
                        "phone": phone or existing.get("phone"),
                        "password_hash": password_hash,
                        "role": Config.ROLE_ADMIN
                    })
                    session["user_id"] = existing["id"]
                    session["user_name"] = name
                    session["user_email"] = existing["email"]
                    session["user_role"] = Config.ROLE_ADMIN

                    db.log_admin_action(existing["id"], "ADMIN_REGISTER", f"Account {email} upgraded to Administrator.")
                    flash(f"Welcome Administrator, {name}! Your account has been upgraded to Administrator.", "success")
                    return redirect(url_for("admin_dashboard"))

            password_hash = generate_password_hash(password)
            new_user = db.create_user(name, email, phone, password_hash, Config.ROLE_ADMIN)

            session["user_id"] = new_user["id"]
            session["user_name"] = new_user["name"]
            session["user_email"] = new_user["email"]
            session["user_role"] = Config.ROLE_ADMIN

            db.log_admin_action(new_user["id"], "ADMIN_REGISTER", f"New Administrator {new_user['email']} registered.")
            flash(f"Welcome Administrator, {new_user['name']}! Your admin account was created successfully.", "success")
            return redirect(url_for("admin_dashboard"))
        except Exception as e:
            flash(f"Admin Registration error: {str(e)}", "danger")
            return render_template("admin_register.html", name=name, email=email, phone=phone)

    return render_template("admin_register.html")


@app.route("/admin/logout")
@app.route("/logout")
def logout():
    """Clear session and redirect to the appropriate login page."""
    is_admin = (session.get("user_role") == Config.ROLE_ADMIN) or request.path.startswith("/admin")
    csrf = session.get("csrf_token")
    session.clear()
    if csrf:
        session["csrf_token"] = csrf
    flash("You have been logged out successfully.", "info")
    if is_admin:
        return redirect(url_for("admin_login"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def redirect_user_dashboard():
    role = session.get("user_role")
    if role == Config.ROLE_OWNER:
        return redirect(url_for("owner_dashboard"))
    elif role == Config.ROLE_RENTAL:
        return redirect(url_for("rental_dashboard"))
    elif role == Config.ROLE_ADMIN:
        return redirect(url_for("admin_dashboard"))
    else:
        return redirect(url_for("customer_dashboard"))


# ============================================================================
# OWNER VIEW (ADD HOME & ROOMS, DASHBOARD)
# ============================================================================

@app.route("/owner/dashboard")
@login_required
@role_required([Config.ROLE_OWNER])
def owner_dashboard():
    """Owner dashboard matching mockup with Add Home, My Homes, Added Rooms, and Enquiries."""
    owner_id = session["user_id"]
    properties = db.get_properties(owner_id=owner_id, limit=100)
    enquiries = db.get_enquiries_for_owner(owner_id)

    # Fetch all rooms for all homes owned by this owner
    all_rooms = []
    for prop in properties:
        rooms = db.get_rooms_for_property(prop["id"])
        for r in rooms:
            r["property_title"] = prop["title"]
            all_rooms.append(r)

    stats = {
        "total": len(properties),
        "approved": sum(1 for p in properties if p.get("approval_status") == "approved"),
        "pending": sum(1 for p in properties if p.get("approval_status") == "pending"),
        "rejected": sum(1 for p in properties if p.get("approval_status") == "rejected"),
        "enquiries": len(enquiries),
        "total_rooms": len(all_rooms)
    }

    return render_template(
        "owner_dashboard.html",
        properties=properties,
        rooms=all_rooms,
        enquiries=enquiries,
        stats=stats
    )


@app.route("/properties/add", methods=["GET", "POST"])
@login_required
@role_required([Config.ROLE_ADMIN, Config.ROLE_OWNER])
def add_property():
    """Add Home form strictly for Administrator."""
    if request.method == "POST":
        owner_id = session["user_id"]
        title = request.form.get("title", "").strip()
        property_type = request.form.get("property_type", "Apartment").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        locality = request.form.get("locality", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        monthly_rent = request.form.get("monthly_rent", "0").strip()
        security_deposit = request.form.get("security_deposit", "0").strip()
        bedrooms = request.form.get("bedrooms", "1").strip()
        bathrooms = request.form.get("bathrooms", "1").strip()
        balconies = request.form.get("balconies", "0").strip()
        area_sqft = request.form.get("area_sqft", "1000").strip()
        furnishing_status = request.form.get("furnishing_status", "Furnished").strip()
        parking_available = request.form.get("parking_available") == "on"
        water_available = request.form.get("water_available", "24 Hours").strip()
        description = request.form.get("description", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()
        amenities = request.form.getlist("amenities")
        uploaded_files = request.files.getlist("photos")

        errors = []
        if not title or len(title) < 4:
            errors.append("Home title must be at least 4 characters.")
        if not address or len(address) < 4:
            errors.append("Location/Address is required.")
        if not city:
            errors.append("City is required.")

        try:
            rent_val = float(monthly_rent)
            if rent_val <= 0:
                errors.append("Monthly rent must be greater than zero.")
        except ValueError:
            errors.append("Please enter a valid numeric monthly rent.")

        try:
            deposit_val = float(security_deposit) if security_deposit else 0.0
        except ValueError:
            deposit_val = 0.0

        try:
            area_val = int(area_sqft)
            if area_val <= 0:
                errors.append("Square footage area must be greater than zero.")
        except ValueError:
            area_val = 1000

        lat_val = None
        long_val = None
        if latitude and longitude:
            try:
                lat_val = float(latitude)
                long_val = float(longitude)
            except ValueError:
                pass

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template("add_property.html", form_data=request.form)

        is_admin = session.get("user_role") == Config.ROLE_ADMIN
        approval_status = "approved" if is_admin else "pending"

        prop_payload = {
            "owner_id": owner_id,
            "title": title,
            "property_type": property_type or "Apartment",
            "address": address,
            "city": city,
            "locality": locality or None,
            "latitude": lat_val,
            "longitude": long_val,
            "monthly_rent": rent_val,
            "security_deposit": deposit_val,
            "bedrooms": int(bedrooms) if bedrooms.isdigit() else 1,
            "bathrooms": int(bathrooms) if bathrooms.isdigit() else 1,
            "balconies": int(balconies) if balconies.isdigit() else 0,
            "area_sqft": area_val,
            "furnishing_status": furnishing_status,
            "parking_available": parking_available,
            "water_available": water_available,
            "amenities": amenities,
            "description": description or None,
            "contact_phone": contact_phone or None,
            "approval_status": approval_status,
            "is_active": True,
        }

        try:
            created_property = db.create_property(prop_payload)
            property_id = created_property["id"]

            for idx, file in enumerate(uploaded_files):
                if file and file.filename:
                    try:
                        db.upload_property_image(file, property_id=property_id, is_primary=(idx == 0))
                    except Exception as img_err:
                        print(f"Warning uploading image: {img_err}")

            if is_admin:
                try:
                    db.log_admin_action(session["user_id"], "ADD_PROPERTY", f"Admin added home listing: {title}")
                except Exception as log_err:
                    print(f"Admin log warning: {log_err}")
                flash(f"Home '{title}' added and published live! Visible on Admin Page and Tenant Web.", "success")
                return redirect(url_for("admin_dashboard") + "#recent-listings")
            else:
                flash(f"Home '{title}' submitted! It is now pending admin approval.", "success")
                return redirect(url_for("owner_dashboard"))
        except Exception as e:
            flash(f"Failed to add home: {str(e)}", "danger")
            return render_template("add_property.html", form_data=request.form)

    return render_template("add_property.html", form_data={})


@app.route("/properties/<property_id>/edit", methods=["GET", "POST"])
@login_required
@role_required([Config.ROLE_OWNER, Config.ROLE_ADMIN])
def edit_property(property_id):
    prop = db.get_property_by_id(property_id)
    if not prop:
        flash("Property not found.", "danger")
        return redirect(url_for("owner_dashboard"))

    is_owner = session.get("user_id") == prop.get("owner_id")
    is_admin = session.get("user_role") == Config.ROLE_ADMIN

    if not (is_owner or is_admin):
        flash("You are not authorized to edit this property.", "danger")
        return redirect(url_for("owner_dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        property_type = request.form.get("property_type", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        locality = request.form.get("locality", "").strip()
        latitude = request.form.get("latitude", "").strip()
        longitude = request.form.get("longitude", "").strip()
        monthly_rent = request.form.get("monthly_rent", "").strip()
        security_deposit = request.form.get("security_deposit", "0").strip()
        bedrooms = request.form.get("bedrooms", "1").strip()
        bathrooms = request.form.get("bathrooms", "1").strip()
        balconies = request.form.get("balconies", "0").strip()
        area_sqft = request.form.get("area_sqft", "").strip()
        furnishing_status = request.form.get("furnishing_status") or prop.get("furnishing_status") or "Furnished"
        parking_available = request.form.get("parking_available") == "on"
        water_available = request.form.get("water_available", "24 Hours").strip()
        description = request.form.get("description", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()
        amenities = request.form.getlist("amenities")
        uploaded_files = request.files.getlist("photos")

        lat_val = None
        long_val = None
        if latitude and longitude:
            try:
                lat_val = float(latitude)
                long_val = float(longitude)
            except ValueError:
                pass

        updates = {
            "title": title,
            "property_type": property_type,
            "address": address,
            "city": city,
            "locality": locality or None,
            "latitude": lat_val,
            "longitude": long_val,
            "monthly_rent": float(monthly_rent),
            "security_deposit": float(security_deposit) if security_deposit else 0.0,
            "bedrooms": int(bedrooms),
            "bathrooms": int(bathrooms),
            "balconies": int(balconies),
            "area_sqft": int(area_sqft),
            "furnishing_status": furnishing_status,
            "parking_available": parking_available,
            "water_available": water_available,
            "amenities": amenities,
            "description": description or None,
            "contact_phone": contact_phone or None,
        }

        if is_owner and not is_admin:
            updates["approval_status"] = "pending"
            updates["rejection_reason"] = None

        try:
            db.update_property(property_id, updates)
            for file in uploaded_files:
                if file and file.filename:
                    try:
                        db.upload_property_image(file, property_id=property_id)
                    except Exception as e:
                        print(f"Upload warning: {e}")

            flash("Home details updated successfully!", "success")
            return redirect(url_for("admin_dashboard" if is_admin else "owner_dashboard"))
        except Exception as e:
            flash(f"Failed to update property: {str(e)}", "danger")

    rooms = db.get_rooms_for_property(property_id)
    return render_template("edit_property.html", property=prop, rooms=rooms)


@app.route("/properties/<property_id>/delete", methods=["POST"])
@login_required
@role_required([Config.ROLE_OWNER, Config.ROLE_ADMIN])
def delete_property(property_id):
    prop = db.get_property_by_id(property_id)
    if not prop:
        flash("Property not found.", "danger")
        return redirect(url_for("redirect_user_dashboard"))

    is_owner = session.get("user_id") == prop.get("owner_id")
    is_admin = session.get("user_role") == Config.ROLE_ADMIN

    if not (is_owner or is_admin):
        flash("Permission denied.", "danger")
        return redirect(url_for("redirect_user_dashboard"))

    try:
        db.delete_property(property_id)
        if is_admin:
            db.log_admin_action(session["user_id"], "DELETE_PROPERTY", f"Deleted property {property_id}")
        flash("Property listing deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting property: {str(e)}", "danger")

    return redirect(url_for("admin_dashboard" if is_admin else "owner_dashboard"))


@app.route("/properties/<property_id>/images/<image_id>/delete", methods=["POST"])
@login_required
@role_required([Config.ROLE_OWNER, Config.ROLE_ADMIN])
def delete_image(property_id, image_id):
    prop = db.get_property_by_id(property_id)
    if not prop:
        flash("Property not found.", "danger")
        return redirect(url_for("owner_dashboard"))

    is_owner = session.get("user_id") == prop.get("owner_id")
    is_admin = session.get("user_role") == Config.ROLE_ADMIN

    if not (is_owner or is_admin):
        flash("Permission denied.", "danger")
        return redirect(url_for("owner_dashboard"))

    try:
        db.delete_property_image(image_id, property_id)
        flash("Photo removed successfully.", "success")
    except Exception as e:
        flash(f"Error removing photo: {str(e)}", "danger")

    return redirect(url_for("edit_property", property_id=property_id))


# ============================================================================
# ROOMS OPERATIONS (ADD, UPDATE, DELETE ROOMS)
# ============================================================================

@app.route("/properties/<property_id>/rooms/add", methods=["POST"])
@login_required
@role_required([Config.ROLE_OWNER, Config.ROLE_RENTAL, Config.ROLE_ADMIN])
def add_room(property_id):
    """Add a room (e.g. Bedroom, Kitchen, Hall) to a home listing."""
    prop = db.get_property_by_id(property_id)
    if not prop:
        flash("Property not found.", "danger")
        return redirect(request.referrer or url_for("redirect_user_dashboard"))

    room_type = request.form.get("room_type", "Bedroom").strip()
    size = request.form.get("size", "12 x 10 ft").strip()
    price = request.form.get("price", "0").strip()
    availability = request.form.get("availability", "Available").strip()

    try:
        price_val = float(price) if price else 0.0
        db.create_room(
            property_id=property_id,
            created_by=session["user_id"],
            room_type=room_type,
            size=size,
            price=price_val,
            availability=availability
        )
        flash(f"{room_type} room added successfully to {prop['title']}!", "success")
    except Exception as e:
        flash(f"Failed to add room: {str(e)}", "danger")

    return redirect(request.referrer or url_for("redirect_user_dashboard"))


@app.route("/rooms/<room_id>/delete", methods=["POST"])
@login_required
@role_required([Config.ROLE_OWNER, Config.ROLE_RENTAL, Config.ROLE_ADMIN])
def delete_room(room_id):
    db.delete_room(room_id)
    flash("Room removed successfully.", "info")
    return redirect(request.referrer or url_for("redirect_user_dashboard"))


@app.route("/rooms/<room_id>/availability", methods=["POST"])
@login_required
@role_required([Config.ROLE_OWNER, Config.ROLE_RENTAL, Config.ROLE_ADMIN])
def toggle_room_availability(room_id):
    new_avail = request.form.get("availability", "Available")
    db.update_room(room_id, {"availability": new_avail})
    flash(f"Room availability updated to {new_avail}.", "success")
    return redirect(request.referrer or url_for("redirect_user_dashboard"))


# ============================================================================
# RENTAL VIEW (VIEW HOMES & ADD ROOMS)
# ============================================================================

@app.route("/rental/dashboard")
@login_required
@role_required([Config.ROLE_RENTAL])
def rental_dashboard():
    """Rental view: Browse owner homes, add rooms to homes, and view rooms table."""
    available_homes = db.get_properties(approval_status="approved", is_active=True, limit=50)

    # Fetch rooms managed
    all_rooms = []
    for home_item in available_homes:
        rooms = db.get_rooms_for_property(home_item["id"])
        for r in rooms:
            r["home_title"] = home_item["title"]
            all_rooms.append(r)

    return render_template(
        "rental_dashboard.html",
        available_homes=available_homes,
        rooms=all_rooms
    )


# ============================================================================
# CUSTOMER / TENANT VIEW (BROWSE, FAVOURITES, ENQUIRIES)
# ============================================================================

@app.route("/tenant/dashboard")
@app.route("/tenant")
@app.route("/customer/dashboard")
@login_required
@role_required([Config.ROLE_CUSTOMER])
def customer_dashboard():
    """Tenant view: Saved favourite homes and rental enquiries/bookings sent. Strictly accessible by Tenants."""
    customer_id = session["user_id"]
    favourites = db.get_customer_favourites(customer_id)
    enquiries = db.get_enquiries_for_customer(customer_id)
    featured_homes = db.get_properties(approval_status="approved", is_active=True, limit=6)

    return render_template(
        "customer_dashboard.html",
        favourites=favourites,
        enquiries=enquiries,
        featured_homes=featured_homes
    )


@app.route("/properties/<property_id>/enquiry", methods=["POST"])
@login_required
@role_required([Config.ROLE_CUSTOMER, Config.ROLE_ADMIN])
def submit_enquiry(property_id):
    """Customer sends enquiry or booking request to home owner."""
    prop = db.get_property_by_id(property_id)
    if not prop:
        flash("Property not found.", "danger")
        return redirect(url_for("properties_listing"))

    message = request.form.get("message", "").strip()
    room_id = request.form.get("room_id") or None

    if not message or len(message) < 5:
        flash("Please enter a message for your enquiry/booking request.", "warning")
        return redirect(url_for("property_details", property_id=property_id))

    customer_id = session["user_id"]
    owner_id = prop["owner_id"]

    try:
        db.create_rental_enquiry(property_id, customer_id, owner_id, message, room_id=room_id)
        flash("Your enquiry/booking request was sent to the owner! You can track it in your Tenant Dashboard.", "success")
    except Exception as e:
        flash(f"Failed to send enquiry: {str(e)}", "danger")

    return redirect(url_for("property_details", property_id=property_id))


@app.route("/api/favourite/toggle/<property_id>", methods=["POST"])
@login_required
def api_toggle_favourite(property_id):
    if session.get("user_role") not in (Config.ROLE_CUSTOMER, Config.ROLE_ADMIN):
        return jsonify({"error": "Only tenant/customer accounts can save favourites."}), 403

    customer_id = session["user_id"]
    is_fav = db.toggle_favourite(customer_id, property_id)
    return jsonify({
        "success": True,
        "is_favourite": is_fav,
        "property_id": property_id
    })


@app.route("/enquiries/<enquiry_id>/status", methods=["POST"])
@login_required
def update_enquiry_status(enquiry_id):
    new_status = request.form.get("status")
    if new_status in ("pending", "contacted", "approved", "closed"):
        db.update_enquiry_status(enquiry_id, new_status)
        flash(f"Enquiry status updated to {new_status.capitalize()}.", "success")
    return redirect(request.referrer or url_for("redirect_user_dashboard"))


# ============================================================================
# ADMIN VIEW (MANAGE USERS & LISTINGS)
# ============================================================================

@app.route("/admin/dashboard")
@login_required
@role_required([Config.ROLE_ADMIN])
def admin_dashboard():
    """Admin dashboard matching the exact mockup: Stat cards, Manage Users table, Recent Listings."""
    stats = db.get_admin_dashboard_stats()
    all_users = db.get_all_users()
    recent_listings = db.get_properties(limit=200)
    pending_properties = db.get_properties(approval_status="pending", limit=100)
    admin_logs = db.get_admin_logs(limit=50)

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        users=all_users,
        recent_listings=recent_listings,
        pending_properties=pending_properties,
        admin_logs=admin_logs
    )


@app.route("/admin/users/<user_id>/status", methods=["POST"])
@login_required
@role_required([Config.ROLE_ADMIN])
def admin_toggle_user_status(user_id):
    new_status = request.form.get("status", "active")
    db.update_user_status(user_id, new_status)
    db.log_admin_action(session["user_id"], "UPDATE_USER_STATUS", f"User {user_id} set to {new_status}")
    flash(f"User status updated to {new_status}.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/users/<user_id>/edit", methods=["POST"])
@login_required
@role_required([Config.ROLE_ADMIN])
def admin_edit_user(user_id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    role = request.form.get("role", "customer").strip().lower()

    if not name or len(name) < 2:
        flash("User name must be at least 2 characters.", "danger")
        return redirect(url_for("admin_dashboard"))

    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        flash("Invalid email address provided.", "danger")
        return redirect(url_for("admin_dashboard"))

    updates = {
        "name": name,
        "email": email,
        "phone": phone or None,
        "role": role if role in (Config.ROLE_CUSTOMER, Config.ROLE_OWNER, Config.ROLE_RENTAL, Config.ROLE_ADMIN) else Config.ROLE_CUSTOMER,
    }

    try:
        db.update_user(user_id, updates)
        db.log_admin_action(session["user_id"], "EDIT_USER", f"Admin updated user {email} ({name}, role: {role})")
        flash(f"User '{name}' updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating user: {str(e)}", "danger")

    return redirect(url_for("admin_dashboard") + "#registered-users")


@app.route("/admin/users/<user_id>/delete", methods=["POST"])
@login_required
@role_required([Config.ROLE_ADMIN])
def admin_delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own logged-in administrator account.", "warning")
        return redirect(url_for("admin_dashboard") + "#registered-users")

    try:
        user = db.get_user_by_id(user_id)
        user_name = user["name"] if user else "User"
        db.delete_user(user_id)
        db.log_admin_action(session["user_id"], "DELETE_USER", f"Admin deleted user {user_id} ({user_name})")
        flash(f"User '{user_name}' deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "danger")

    return redirect(url_for("admin_dashboard") + "#registered-users")


@app.route("/admin/property/<property_id>/approve", methods=["POST"])
@login_required
@role_required([Config.ROLE_ADMIN])
def admin_approve_property(property_id):
    try:
        db.update_property(property_id, {
            "approval_status": "approved",
            "rejection_reason": None,
            "is_active": True
        })
        db.log_admin_action(session["user_id"], "APPROVE_PROPERTY", f"Approved property {property_id}")
        flash("Home listing approved and published live!", "success")
    except Exception as e:
        flash(f"Error approving property: {str(e)}", "danger")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/property/<property_id>/reject", methods=["POST"])
@login_required
@role_required([Config.ROLE_ADMIN])
def admin_reject_property(property_id):
    reason = request.form.get("rejection_reason", "").strip() or "Listing standards not met."
    try:
        db.update_property(property_id, {
            "approval_status": "rejected",
            "rejection_reason": reason
        })
        db.log_admin_action(session["user_id"], "REJECT_PROPERTY", f"Rejected property {property_id}. Reason: {reason}")
        flash("Home listing rejected.", "warning")
    except Exception as e:
        flash(f"Error rejecting property: {str(e)}", "danger")
    return redirect(url_for("admin_dashboard"))


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(403)
def forbidden_error(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found_error(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    print("=" * 60)
    print("  HOME RENTAL MANAGEMENT SYSTEM")
    print(f"  Server URL: http://localhost:{Config.PORT}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
