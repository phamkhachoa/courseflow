-- liquibase formatted sql

-- changeset courseflow:course-008-course-pricing
ALTER TABLE courses ADD COLUMN IF NOT EXISTS list_price NUMERIC(12, 2);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS currency VARCHAR(3);
ALTER TABLE courses ADD COLUMN IF NOT EXISTS price_status VARCHAR(40) NOT NULL DEFAULT 'NOT_CONFIGURED';

ALTER TABLE courses
    ADD CONSTRAINT chk_courses_list_price_non_negative
    CHECK (list_price IS NULL OR list_price >= 0) NOT VALID;

ALTER TABLE courses
    ADD CONSTRAINT chk_courses_currency_iso3
    CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$') NOT VALID;

ALTER TABLE courses
    ADD CONSTRAINT chk_courses_price_status
    CHECK (price_status IN ('NOT_CONFIGURED', 'ACTIVE', 'FREE', 'SUSPENDED')) NOT VALID;

UPDATE courses
SET list_price = 100.00,
    currency = 'USD',
    price_status = 'ACTIVE'
WHERE id = '30000000-0000-0000-0000-000000000001'
  AND price_status = 'NOT_CONFIGURED';
