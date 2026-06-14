-- liquibase formatted sql

-- changeset courseflow:loyalty-002-client-bindings
CREATE TABLE IF NOT EXISTS loyalty_program_client_bindings (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(80) NOT NULL,
    application_id VARCHAR(80) NOT NULL,
    program_id VARCHAR(120) NOT NULL,
    client_id VARCHAR(120) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'ACTIVE',
    allowed_operations JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by VARCHAR(160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uk_loyalty_program_client_binding UNIQUE (tenant_id, application_id, program_id, client_id),
    CONSTRAINT chk_loyalty_program_client_binding_status CHECK (status IN ('ACTIVE', 'SUSPENDED')),
    CONSTRAINT fk_loyalty_program_client_binding_program
        FOREIGN KEY (tenant_id, application_id, program_id)
        REFERENCES loyalty_programs (tenant_id, application_id, program_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_loyalty_program_client_binding_client
    ON loyalty_program_client_bindings (client_id, status);
