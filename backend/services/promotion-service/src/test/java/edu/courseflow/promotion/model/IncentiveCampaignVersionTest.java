package edu.courseflow.promotion.model;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import org.junit.jupiter.api.Test;

class IncentiveCampaignVersionTest {

    @Test
    void creatorCannotApproveOwnCampaignVersion() {
        IncentiveCampaign campaign = campaign("WELCOME10");
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        version.submit("creator", "ready");

        assertThatThrownBy(() -> version.approve("creator", "approved"))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("creator cannot approve");
    }

    @Test
    void publishedCampaignVersionIsImmutableForDraftEdits() {
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign("WELCOME20"), 1, "creator");
        version.submit("creator", "ready");
        version.approve("reviewer", "approved");
        version.publish("publisher");

        assertThatThrownBy(() -> version.updateDraft(
                "WELCOME30",
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("draft or rejected");
    }

    @Test
    void rollbackDraftCopiesSourceSnapshotWithoutActivatingIt() {
        IncentiveCampaignVersion source = new IncentiveCampaignVersion(campaign("ROLLBACK10"), 2, "creator");
        source.submit("creator", "ready");
        source.approve("reviewer", "approved");
        source.publish("publisher");

        IncentiveCampaignVersion rollback = new IncentiveCampaignVersion(source, 3, "operator");

        assertThat(rollback.getVersionNumber()).isEqualTo(3);
        assertThat(rollback.getVersionStatus()).isEqualTo("DRAFT");
        assertThat(rollback.isActiveSnapshot()).isFalse();
        assertThat(rollback.getCode()).isEqualTo(source.getCode());
        assertThat(rollback.getActionsJson()).isEqualTo(source.getActionsJson());
        assertThat(rollback.getRollbackSourceVersion()).isEqualTo(2);
    }

    private IncentiveCampaign campaign(String code) {
        return new IncentiveCampaign(
                "courseflow",
                "lms",
                code,
                "Welcome",
                null,
                "PROMOTION",
                Instant.now().minusSeconds(60),
                Instant.now().plusSeconds(3600),
                100,
                false,
                true,
                false,
                "ALL",
                "USD",
                "[]",
                "[{\"schemaVersion\":1,\"type\":\"ORDER_FIXED_OFF\",\"parameters\":{\"amount\":10}}]",
                100,
                1,
                "creator");
    }
}
