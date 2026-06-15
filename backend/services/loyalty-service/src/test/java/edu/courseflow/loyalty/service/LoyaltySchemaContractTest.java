package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class LoyaltySchemaContractTest {

    @Test
    void changelogAllowsZeroPointFulfillmentApprovalsOnlyForFulfillmentOverride() {
        String changelog = resource("db/changelog/db.changelog.xml");
        String migration = resource("db/changelog/changes/011-approval-zero-delta-fulfillment.sql");

        assertThat(changelog).contains("011-approval-zero-delta-fulfillment.sql");
        assertThat(migration)
                .contains("DROP CONSTRAINT IF EXISTS chk_loyalty_adjustment_approval_delta")
                .contains("points_delta <> 0")
                .contains("metadata_json ->> 'operationType'")
                .contains("REWARD_FULFILLMENT_OVERRIDE");
    }

    private String resource(String path) {
        try (var stream = Thread.currentThread().getContextClassLoader().getResourceAsStream(path)) {
            assertThat(stream).as("resource %s", path).isNotNull();
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException ex) {
            throw new UncheckedIOException(ex);
        }
    }
}
