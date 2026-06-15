-- liquibase formatted sql

-- changeset courseflow:outbox-relay-004-dead-letter-governance
ALTER TABLE relay_dead_letters
    ADD COLUMN IF NOT EXISTS topic VARCHAR(255),
    ADD COLUMN IF NOT EXISTS kafka_partition INT,
    ADD COLUMN IF NOT EXISTS kafka_offset BIGINT,
    ADD COLUMN IF NOT EXISTS error_class VARCHAR(255);

UPDATE relay_dead_letters
SET topic = COALESCE(topic, event_type)
WHERE topic IS NULL;

CREATE INDEX IF NOT EXISTS idx_relay_dead_letters_payload_hash
    ON relay_dead_letters (payload_hash);

CREATE INDEX IF NOT EXISTS idx_relay_dead_letters_topic_status
    ON relay_dead_letters (topic, status);
