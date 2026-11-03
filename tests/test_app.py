import pytest
from app import app
from config import Config
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            yield client


def test_first_open_redirects_to_signup(client):
    """Verify visiting root URL / directly opens/redirects to the Sign Up page."""
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Create Tenant Account" in response.data


def test_home_page(client):
    """Verify home page loads successfully with 200 OK status."""
    response = client.get("/home")
    assert response.status_code == 200
    assert b"Home" in response.data
    assert b"Rental" in response.data
    assert b"Find Your Perfect Home" in response.data


def test_browse_properties_page(client):
    """Verify properties browse page loads successfully."""
    response = client.get("/properties")
    assert response.status_code == 200
    assert b"Search Rental Properties" in response.data


def test_login_page(client):
    """Verify clean unified login page loads with 200 OK."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome Back" in response.data
    assert b"Sign In" in response.data


def test_legacy_login_routes_redirect_to_unified_login(client):
    """Verify legacy role login routes redirect directly to clean unified login."""
    res_owner = client.get("/owner/login")
    assert res_owner.status_code == 302
    assert "/login" in res_owner.headers["Location"]

    res_tenant = client.get("/tenant/login")
    assert res_tenant.status_code == 302
    assert "/login" in res_tenant.headers["Location"]


def test_register_page_loads(client):
    """Verify registration page renders strictly for Tenant registration without Owner option."""
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create Tenant Account" in response.data
    assert b"Tenant" in response.data
    assert b"Owner" not in response.data


def test_tenant_register_page(client):
    """Verify dedicated Tenant registration page loads cleanly."""
    response = client.get("/tenant/register")
    assert response.status_code == 200
    assert b"Create Tenant Account" in response.data
    assert b"Register as Tenant" in response.data


def test_owner_register_page(client):
    """Verify dedicated Owner registration page loads cleanly."""
    response = client.get("/owner/register")
    assert response.status_code == 200
    assert b"Create Owner Account" in response.data
    assert b"Register as Owner" in response.data


def test_protected_routes_redirect_unauthenticated(client):
    """Ensure dashboards redirect unauthenticated visitors to login."""
    res_owner = client.get("/owner/dashboard")
    assert res_owner.status_code == 302
    assert "/login" in res_owner.headers["Location"]

    res_customer = client.get("/customer/dashboard")
    assert res_customer.status_code == 302
    assert "/login" in res_customer.headers["Location"]

    res_admin = client.get("/admin/dashboard")
    assert res_admin.status_code == 302
    assert "/login" in res_admin.headers["Location"]


def test_404_page(client):
    """Verify unknown route triggers custom 404 page."""
    response = client.get("/non-existent-page-url")
    assert response.status_code == 404
    assert b"404" in response.data


def test_logout_redirects_to_login(client):
    """Verify logout clears session and redirects directly to login page."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-tenant-id"
        sess["user_name"] = "Test Tenant"
        sess["user_role"] = "customer"

    response = client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    # Verify session is cleared
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_admin_logout_redirects_to_admin_login(client):
    """Verify admin logout clears session and redirects directly to admin login page."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-admin-id"
        sess["user_name"] = "Test Admin"
        sess["user_role"] = "admin"

    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")

    # Verify session is cleared
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_admin_registration_redirects_to_login(client):
    """Verify public administrator registration is disabled."""
    response = client.get("/admin/register")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/login")


def test_admin_login_has_no_register_link(client):
    """Verify admin login page does not offer public registration."""
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert b"Register as Admin" not in response.data
    assert Config.ADMIN_EMAIL.encode() in response.data


def test_admin_login_rejects_non_allowlisted_email(client, monkeypatch):
    """Reject other email addresses before querying the user database."""
    def unexpected_user_lookup(_email):
        pytest.fail("Non-allowlisted admin email reached the database")

    monkeypatch.setattr("app.db.get_user_by_email", unexpected_user_lookup)
    with client.session_transaction() as sess:
        sess["csrf_token"] = "test-csrf-token"

    response = client.post("/admin/login", data={
        "csrf_token": "test-csrf-token",
        "email": "other@example.com",
        "password": "anything",
    })

    assert response.status_code == 200
    assert b"Invalid administrator credentials" in response.data


def post_admin_login(client, email, password):
    client.get("/admin/login")
    with client.session_transaction() as sess:
        csrf_token = sess["csrf_token"]

    return client.post("/admin/login", data={
        "csrf_token": csrf_token,
        "email": email,
        "password": password,
    })


def test_admin_login_success_redirects_to_dashboard(client, monkeypatch):
    """A valid allowlisted admin account signs in and reaches its dashboard."""
    test_password = "UnitTest-Only-Password-42!"
    admin_user = {
        "id": "test-admin-id",
        "name": "Test Admin",
        "email": Config.ADMIN_EMAIL,
        "role": Config.ROLE_ADMIN,
        "password_hash": generate_password_hash(test_password),
    }
    monkeypatch.setattr("app.db.get_user_by_email", lambda _email: admin_user)
    monkeypatch.setattr("app.db.log_admin_action", lambda *_args: None)

    response = post_admin_login(client, Config.ADMIN_EMAIL, test_password)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")
    with client.session_transaction() as sess:
        assert sess["user_role"] == Config.ROLE_ADMIN
        assert sess["user_email"] == Config.ADMIN_EMAIL


def test_admin_login_rejects_incorrect_password(client, monkeypatch):
    """A valid admin email with a wrong password is rejected."""
    admin_user = {
        "id": "test-admin-id",
        "name": "Test Admin",
        "email": Config.ADMIN_EMAIL,
        "role": Config.ROLE_ADMIN,
        "password_hash": generate_password_hash("Correct-Test-Password-42!"),
    }
    monkeypatch.setattr("app.db.get_user_by_email", lambda _email: admin_user)

    response = post_admin_login(client, Config.ADMIN_EMAIL, "incorrect-test-password")

    assert response.status_code == 200
    assert b"Invalid administrator credentials" in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_admin_login_rejects_missing_account(client, monkeypatch):
    """An absent admin account is rejected without creating a session."""
    monkeypatch.setattr("app.db.get_user_by_email", lambda _email: None)

    response = post_admin_login(client, Config.ADMIN_EMAIL, "any-test-password")

    assert response.status_code == 200
    assert b"Invalid administrator credentials" in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_admin_login_rejects_non_admin_role(client, monkeypatch):
    """A matching password does not let a customer access the admin portal."""
    customer_user = {
        "id": "test-customer-id",
        "name": "Test Customer",
        "email": Config.ADMIN_EMAIL,
        "role": Config.ROLE_CUSTOMER,
        "password_hash": generate_password_hash("Customer-Test-Password-42!"),
    }
    monkeypatch.setattr("app.db.get_user_by_email", lambda _email: customer_user)

    response = post_admin_login(client, Config.ADMIN_EMAIL, "Customer-Test-Password-42!")

    assert response.status_code == 200
    assert b"Invalid administrator credentials" in response.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_non_allowlisted_admin_session_is_denied(client):
    """Reject admin-role sessions that do not use the authorized admin email."""
    with client.session_transaction() as sess:
        sess["user_id"] = "unauthorized-admin-id"
        sess["user_name"] = "Unauthorized Admin"
        sess["user_role"] = Config.ROLE_ADMIN
        sess["user_email"] = "other@example.com"

    response = client.get("/admin/dashboard")
    assert response.status_code == 403


def test_admin_can_access_add_property_page(client):
    """Verify admin can access /properties/add page."""
    with client.session_transaction() as sess:
        sess["user_id"] = "admin-test-id"
        sess["user_name"] = "Admin User"
        sess["user_role"] = "admin"
        sess["user_email"] = Config.ADMIN_EMAIL

    response = client.get("/properties/add")
    assert response.status_code == 200
    assert b"Add Home" in response.data
    assert b"Publish Home Listing" in response.data or b"Add Home" in response.data


def test_admin_dashboard_has_add_home_button(client):
    """Verify admin dashboard has Add Home Listing buttons."""
    with client.session_transaction() as sess:
        sess["user_id"] = "admin-test-id"
        sess["user_name"] = "Admin User"
        sess["user_role"] = "admin"
        sess["user_email"] = Config.ADMIN_EMAIL

    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Add Home Listing" in response.data
    assert b"View on Tenant Web" in response.data


def test_tenant_dashboard_separation(client):
    """Verify tenant has dedicated dashboard and cannot access admin dashboard or add home."""
    with client.session_transaction() as sess:
        sess["user_id"] = "tenant-test-id"
        sess["user_name"] = "Tenant User"
        sess["user_role"] = "customer"

    # Tenant dashboard loads cleanly
    res_tenant = client.get("/tenant/dashboard")
    assert res_tenant.status_code == 200
    assert b"Tenant Portal" in res_tenant.data
    assert b"Tenant Dashboard" in res_tenant.data

    # Tenant cannot access admin dashboard
    res_admin = client.get("/admin/dashboard")
    assert res_admin.status_code == 403

    # Tenant cannot access add home
    res_add = client.get("/properties/add")
    assert res_add.status_code == 403


def test_admin_cannot_access_tenant_dashboard(client):
    """Verify admin is blocked from accessing the tenant dashboard."""
    with client.session_transaction() as sess:
        sess["user_id"] = "admin-test-id"
        sess["user_name"] = "Admin User"
        sess["user_role"] = "admin"

    res = client.get("/tenant/dashboard")
    assert res.status_code == 403
