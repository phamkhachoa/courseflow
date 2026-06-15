-- liquibase formatted sql
-- changeset courseflow:enrollment-007-order-payment-reference-guards

CREATE UNIQUE INDEX IF NOT EXISTS uk_enrollment_orders_idempotency_key
    ON enrollment_orders (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uk_enrollment_orders_payment_reference
    ON enrollment_orders (lower(payment_provider), payment_reference)
    WHERE payment_provider IS NOT NULL
      AND payment_reference IS NOT NULL;
