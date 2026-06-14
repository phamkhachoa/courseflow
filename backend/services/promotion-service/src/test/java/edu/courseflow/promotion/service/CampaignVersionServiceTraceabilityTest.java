package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionTransitionRequestDto;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCampaignVersion;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignVersionRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CampaignVersionServiceTraceabilityTest {

    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveCampaignVersionRepository campaignVersions;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveAccessService access;
    @Mock
    IncentiveMetrics metrics;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private CampaignVersionService service;

    @BeforeEach
    void setUp() {
        IncentiveDecisionEngine decisions = new IncentiveDecisionEngine(objectMapper);
        service = new CampaignVersionService(
                campaigns,
                campaignVersions,
                auditEvents,
                access,
                decisions,
                objectMapper,
                metrics);
    }

    @Test
    void submitPersistsAuditTraceMetadata() {
        CurrentUser admin = user("admin@example.com");
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator@example.com");
        when(campaignVersions.findByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        when(access.sourceClientId(admin)).thenReturn("api-gateway");
        when(campaignVersions.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.submit(campaign.getId(), 1, new CampaignVersionTransitionRequestDto("ready"), admin, "corr-submit");

        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("campaign_version.submitted");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-submit");
        assertThat(audit.getSourceClientId()).isEqualTo("api-gateway");
        assertThat(audit.getActorId()).isEqualTo("1");
        verify(metrics).versionTransition("submitted", "success");
    }

    @Test
    void publishPersistsAuditTraceMetadata() {
        CurrentUser publisher = user("publisher@example.com");
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator@example.com");
        version.submit("creator@example.com", "ready");
        version.approve("reviewer@example.com", "approved");
        when(campaignVersions.lockByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        when(access.sourceClientId(publisher)).thenReturn("api-gateway");
        when(campaignVersions.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(campaigns.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

        service.publish(campaign.getId(), 1, new CampaignVersionTransitionRequestDto("ship"), publisher,
                "corr-publish");

        IncentiveAuditEvent audit = capturedAudit();
        assertThat(audit.getAction()).isEqualTo("campaign_version.published");
        assertThat(audit.getCorrelationId()).isEqualTo("corr-publish");
        assertThat(audit.getSourceClientId()).isEqualTo("api-gateway");
        assertThat(audit.getActorId()).isEqualTo("1");
        assertThat(version.getVersionStatus()).isEqualTo("PUBLISHED");
        verify(metrics).versionTransition("published", "success");
    }

    private IncentiveAuditEvent capturedAudit() {
        ArgumentCaptor<IncentiveAuditEvent> auditCaptor = ArgumentCaptor.forClass(IncentiveAuditEvent.class);
        verify(auditEvents).save(auditCaptor.capture());
        return auditCaptor.getValue();
    }

    private IncentiveCampaign campaign() {
        IncentiveDecisionEngine engine = new IncentiveDecisionEngine(objectMapper);
        return new IncentiveCampaign(
                "courseflow",
                "lms",
                "WELCOME10",
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
                engine.toRulesJson(List.of()),
                engine.toActionsJson(List.of(new ActionSpecDto(
                        "ORDER_FIXED_OFF",
                        1,
                        Map.of("amount", BigDecimal.TEN)))),
                100,
                1,
                "admin@example.com");
    }

    private CurrentUser user(String email) {
        return new CurrentUser(
                1L,
                email,
                "ADMIN",
                Set.of("ADMIN"),
                Set.of());
    }
}
