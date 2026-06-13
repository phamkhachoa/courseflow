-- liquibase formatted sql
-- changeset courseflow:access-control-002-access-user-sequence splitStatements:false

CREATE SEQUENCE IF NOT EXISTS access_user_id_seq START WITH 100000 INCREMENT BY 50;
