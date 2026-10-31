"""
Phase 10 Comprehensive End-to-End Audit Test Suite
Covers Frontend Routes, Forms, Authentication, RBAC, Security, and Database Integration
"""
import uuid
import pytest
from app import app
from config import Config
import database as db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        with app.app_context():
            yield client


# ============================================================================
# 1. PUBLIC ROUTES & NAVIGATION AUDIT
# ============================================================================

def test_all_public_get_routes(client):
    """Verify all public facing pages load with HTTP 200."""
    routes = [
        "/home",
        "/about",
        "/contact",
        "/properties",
        "/browse",
        "/login",
        "/register",
        "/tenant/register",
        "/owner/register",
        "/admin/login",
        "/admin/register",
    ]
    for r in routes:
        res = client.get(r)
        assert res.status_code in (200, 302), f"Route {r} returned {res.status_code}"


def test_contact_form_validation(client):
    """Test contact form validation with empty and invalid data."""
    # CSRF token generation
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    # Empty submission
    res = client.post("/contact", data={
        "csrf_token": "test-csrf-token",
        "name": "",
        "email": "",
        "subject": "",
        "message": ""
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Please fill in all required fields" in res.data

    # Valid submission
    res_valid = client.post("/contact", data={
        "csrf_token": "test-csrf-token",
        "name": "Audit Tester",
        "email": "tester@example.com",
        "subject": "System Verification",
        "message": "Testing contact form delivery."
    }, follow_redirects=True)
    assert res_valid.status_code == 200
    assert b"Thank you for contacting Home Rental" in res_valid.data


# ============================================================================
# 2. SEARCH & FILTERING LOGIC AUDIT
# ============================================================================

def test_property_search_and_filtering(client):
    """Test property search with various filters."""
    # Basic browse
    res = client.get("/properties")
    assert res.status_code == 200

    # Filter with query params
    res_filter = client.get("/properties?city=Bengaluru&bedrooms=2&min_rent=10000&max_rent=50000&property_type=Apartment")
    assert res_filter.status_code == 200

    # Sorting
    res_sort = client.get("/properties?sort_by=price_asc")
    assert res_sort.status_code == 200


# ============================================================================
# 3. FORM VALIDATION & REGISTRATION FLOWS
# ============================================================================

def test_tenant_registration_validation(client):
    """Test tenant registration with password mismatch, short password, invalid email."""
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    # Password mismatch
    res = client.post("/tenant/register", data={
        "csrf_token": "test-csrf-token",
        "name": "Test User",
        "email": "testuser@example.com",
        "phone": "+919876543210",
        "password": "Password123",
        "confirm_password": "MismatchPassword"
    }, follow_redirects=True)
    assert b"Passwords do not match" in res.data

    # Short password
    res = client.post("/tenant/register", data={
        "csrf_token": "test-csrf-token",
        "name": "Test User",
        "email": "testuser@example.com",
        "phone": "+919876543210",
        "password": "123",
        "confirm_password": "123"
    }, follow_redirects=True)
    assert b"Password must be at least 6 characters" in res.data

    # Invalid email
    res = client.post("/tenant/register", data={
        "csrf_token": "test-csrf-token",
        "name": "Test User",
        "email": "invalid-email-format",
        "phone": "+919876543210",
        "password": "Password123",
        "confirm_password": "Password123"
    }, follow_redirects=True)
    assert b"Please enter a valid email address" in res.data


def test_admin_registration_validation(client):
    """Test administrator registration validation."""
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    # Short name
    res = client.post("/admin/register", data={
        "csrf_token": "test-csrf-token",
        "name": "A",
        "email": "admin-audit@example.com",
        "password": "Password123",
        "confirm_password": "Password123"
    }, follow_redirects=True)
    assert b"Admin Full Name must be at least 2 characters" in res.data


# ============================================================================
# 4. AUTHENTICATION & LOGIN AUDIT
# ============================================================================

def test_login_invalid_credentials(client):
    """Test login with non-existent user and wrong password."""
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    res = client.post("/login", data={
        "csrf_token": "test-csrf-token",
        "email": "nonexistent_user_999@example.com",
        "password": "WrongPassword999"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid email or password" in res.data


def test_admin_login_rejects_non_admin_credentials(client):
    """Test that admin login strictly rejects accounts without admin role."""
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    res = client.post("/admin/login", data={
        "csrf_token": "test-csrf-token",
        "email": "non_admin_account@example.com",
        "password": "Password123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Access denied. Invalid administrator credentials" in res.data


# ============================================================================
# 5. ROLE-BASED ACCESS CONTROL (RBAC) & PERMISSIONS
# ============================================================================

def test_tenant_rbac_restrictions(client):
    """Ensure customer/tenant cannot access owner or admin dashboards."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-tenant-uuid"
        sess["user_name"] = "Tenant Tester"
        sess["user_role"] = Config.ROLE_CUSTOMER

    # Tenant dashboard is allowed
    assert client.get("/tenant/dashboard").status_code == 200

    # Owner dashboard is forbidden (403)
    assert client.get("/owner/dashboard").status_code == 403

    # Admin dashboard is forbidden (403)
    assert client.get("/admin/dashboard").status_code == 403

    # Add property is forbidden (403)
    assert client.get("/properties/add").status_code == 403


def test_owner_rbac_restrictions(client):
    """Ensure owner cannot access tenant or admin dashboards."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-owner-uuid"
        sess["user_name"] = "Owner Tester"
        sess["user_role"] = Config.ROLE_OWNER

    # Owner dashboard is allowed
    assert client.get("/owner/dashboard").status_code == 200

    # Tenant dashboard is forbidden (403)
    assert client.get("/tenant/dashboard").status_code == 403

    # Admin dashboard is forbidden (403)
    assert client.get("/admin/dashboard").status_code == 403


def test_admin_rbac_access(client):
    """Ensure admin can access admin dashboard."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-admin-uuid"
        sess["user_name"] = "Admin Tester"
        sess["user_role"] = Config.ROLE_ADMIN

    # Admin dashboard is allowed
    assert client.get("/admin/dashboard").status_code == 200


# ============================================================================
# 6. SECURITY & CSRF AUDIT
# ============================================================================

def test_csrf_protection_on_mutating_requests(client):
    """Verify that POST requests without CSRF token are blocked."""
    # Direct POST without CSRF token
    res = client.post("/contact", data={
        "name": "Hacker",
        "email": "hacker@example.com",
        "subject": "Attack",
        "message": "Attack payload"
    }, follow_redirects=False)
    # Blocked with 302 redirect and flash error or 400
    assert res.status_code in (302, 400)

    # JSON request without CSRF
    res_json = client.post("/api/favourite/toggle/some-id", headers={
        "X-Requested-With": "XMLHttpRequest"
    })
    assert res_json.status_code == 400
    assert b"Invalid or missing CSRF token" in res_json.data


# ============================================================================
# 7. LOGOUT & SESSION TERMINATION
# ============================================================================

def test_logout_clears_session(client):
    """Verify logout terminates session and redirects appropriately."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-session-id"
        sess["user_name"] = "Active User"
        sess["user_role"] = Config.ROLE_CUSTOMER

    res = client.get("/logout", follow_redirects=True)
    assert res.status_code == 200
    assert b"You have been logged out successfully" in res.data

    # Subsequent access to protected route must redirect
    res_dash = client.get("/tenant/dashboard")
    assert res_dash.status_code == 302
    assert "/login" in res_dash.headers["Location"]
