-- ============================================================================
-- HOME RENTAL MANAGEMENT SYSTEM - COMPLETE SUPABASE POSTGRESQL SCHEMA
-- ============================================================================

-- Enable pgcrypto extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ----------------------------------------------------------------------------
-- 1. USERS TABLE (Supports Tenant & Owner)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id UUID,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(30),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'owner', 'rental', 'admin')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ----------------------------------------------------------------------------
-- 2. HOMES / PROPERTIES TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    property_type VARCHAR(60) NOT NULL DEFAULT 'Apartment',
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    locality VARCHAR(120),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    monthly_rent NUMERIC(12, 2) NOT NULL CHECK (monthly_rent >= 0),
    security_deposit NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (security_deposit >= 0),
    bedrooms INT NOT NULL DEFAULT 1 CHECK (bedrooms >= 0),
    bathrooms INT NOT NULL DEFAULT 1 CHECK (bathrooms >= 0),
    balconies INT NOT NULL DEFAULT 0 CHECK (balconies >= 0),
    area_sqft INT NOT NULL CHECK (area_sqft > 0),
    furnishing_status VARCHAR(40) NOT NULL DEFAULT 'Unfurnished' CHECK (furnishing_status IN ('Furnished', 'Semi-Furnished', 'Unfurnished')),
    parking_available BOOLEAN NOT NULL DEFAULT false,
    water_available VARCHAR(60) NOT NULL DEFAULT '24 Hours',
    amenities JSONB DEFAULT '[]'::jsonb,
    description TEXT,
    contact_phone VARCHAR(30),
    approval_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_id);
CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_properties_approval ON properties(approval_status);
CREATE INDEX IF NOT EXISTS idx_properties_is_active ON properties(is_active);
CREATE INDEX IF NOT EXISTS idx_properties_rent ON properties(monthly_rent);

-- ----------------------------------------------------------------------------
-- 3. PROPERTY IMAGES TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS property_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    image_url TEXT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_property_images_property ON property_images(property_id);

-- ----------------------------------------------------------------------------
-- 4. ROOMS TABLE (Per-Room Rentals)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    room_type VARCHAR(60) NOT NULL DEFAULT 'Bedroom',
    size VARCHAR(60) NOT NULL DEFAULT '12 x 10 ft',
    price NUMERIC(12, 2) NOT NULL DEFAULT 0,
    availability VARCHAR(30) NOT NULL DEFAULT 'Available' CHECK (availability IN ('Available', 'Booked', 'Under Maintenance')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_rooms_property ON rooms(property_id);

-- ----------------------------------------------------------------------------
-- 5. FAVOURITES TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS favourites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_customer_property_favourite UNIQUE (customer_id, property_id)
);

CREATE INDEX IF NOT EXISTS idx_favourites_customer ON favourites(customer_id);

-- ----------------------------------------------------------------------------
-- 6. RENTAL ENQUIRIES / BOOKINGS TABLE
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rental_enquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    room_id UUID REFERENCES rooms(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'contacted', 'approved', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_rental_enquiries_owner ON rental_enquiries(owner_id);
CREATE INDEX IF NOT EXISTS idx_rental_enquiries_customer ON rental_enquiries(customer_id);

-- ----------------------------------------------------------------------------
-- 7. ADMIN AUDIT LOGS
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_admin_logs_created ON admin_logs(created_at DESC);

-- ----------------------------------------------------------------------------
-- 8. ROW LEVEL SECURITY (RLS) POLICIES
-- ----------------------------------------------------------------------------
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE favourites ENABLE ROW LEVEL SECURITY;
ALTER TABLE rental_enquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_logs ENABLE ROW LEVEL SECURITY;

-- Allow Backend (service_role or anon key with backend session protection)
DROP POLICY IF EXISTS "Backend access users" ON users;
CREATE POLICY "Backend access users" ON users FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Backend access properties" ON properties;
CREATE POLICY "Backend access properties" ON properties FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Backend access images" ON property_images;
CREATE POLICY "Backend access images" ON property_images FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Backend access rooms" ON rooms;
CREATE POLICY "Backend access rooms" ON rooms FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Backend access favourites" ON favourites;
CREATE POLICY "Backend access favourites" ON favourites FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Backend access enquiries" ON rental_enquiries;
CREATE POLICY "Backend access enquiries" ON rental_enquiries FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Backend access admin_logs" ON admin_logs;
CREATE POLICY "Backend access admin_logs" ON admin_logs FOR ALL USING (true) WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- 9. SUPABASE STORAGE BUCKET
-- ----------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('property-images', 'property-images', true)
ON CONFLICT (id) DO NOTHING;

DROP POLICY IF EXISTS "Public Access to Property Images" ON storage.objects;
CREATE POLICY "Public Access to Property Images" ON storage.objects FOR SELECT USING (bucket_id = 'property-images');

DROP POLICY IF EXISTS "Public Upload to Property Images" ON storage.objects;
CREATE POLICY "Public Upload to Property Images" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'property-images');

DROP POLICY IF EXISTS "Public Delete from Property Images" ON storage.objects;
CREATE POLICY "Public Delete from Property Images" ON storage.objects FOR DELETE USING (bucket_id = 'property-images');

-- ----------------------------------------------------------------------------
-- 10. DEFAULT SAMPLE ADMIN ACCOUNT
-- Email: admin@homerental.com
-- Password: Admin@12345
-- ----------------------------------------------------------------------------
INSERT INTO users (id, name, email, phone, password_hash, role, status)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'System Administrator',
    'admin@homerental.com',
    '+1 800-555-0199',
    'scrypt:32768:8:1$hU6r9O0kY8q2t5Jg$6f6880df8f49896791ef60ad4f1be1df7d4f9bf7b4aebda39ec67f73db2f6f71d5084920b72186985a6a02da8c80ee91ad9bf5a7ff8b1399bcffba73a84ec0fc',
    'admin',
    'active'
)
ON CONFLICT (email) DO NOTHING;
