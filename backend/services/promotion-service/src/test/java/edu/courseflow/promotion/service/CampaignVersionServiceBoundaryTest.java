package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.web.CurrentUser.RoleAssignment;
import edu.courseflow.promotion.dto.PromotionDtos.ActionSpecDto;
import edu.courseflow.promotion.dto.PromotionDtos.CampaignVersionTransitionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.RollbackCampaignVersionRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateCampaignVersionDraftRequestDto;
import edu.courseflow.promotion.model.IncentiveApplication;
import edu.courseflow.promotion.model.IncentiveApplicationClientBinding;
import edu.courseflow.promotion.model.IncentiveCampaign;
import edu.courseflow.promotion.model.IncentiveCampaignVersion;
import edu.courseflow.promotion.repository.IncentiveApplicationClientBindingRepository;
import edu.courseflow.promotion.repository.IncentiveApplicationRepository;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignRepository;
import edu.courseflow.promotion.repository.IncentiveCampaignVersionRepository;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CampaignVersionServiceBoundaryTest {

    @Mock
    IncentiveCampaignRepository campaigns;
    @Mock
    IncentiveCampaignVersionRepository campaignVersions;
    @Mock
    IncentiveAuditEventRepository auditEvents;
    @Mock
    IncentiveApplicationRepository applications;
    @Mock
    IncentiveApplicationClientBindingRepository clientBindings;
    @Mock
    IncentiveMetrics metrics;
    @Mock
    PromotionLoyaltyReadinessClient loyaltyReadiness;

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();
    private CampaignVersionService service;

    @BeforeEach
    void setUp() {
        IncentiveAccessService access = new IncentiveAccessService(
                applications,
                clientBindings,
                auditEvents,
                objectMapper);
        service = new CampaignVersionService(
                campaigns,
                campaignVersions,
                auditEvents,
                access,
                new IncentiveDecisionEngine(objectMapper),
                loyaltyReadiness,
                objectMapper,
                metrics);
    }

    @Test
    void emptyAdminBindingCannotCreateDraftVersion() {
        IncentiveCampaign campaign = campaign();
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        stubClientBinding("[]");

        assertDenied(() -> service.createDraftVersion(campaign.getId(), adminUser(), "corr-draft"));
    }

    @Test
    void emptyAdminBindingCannotUpdateDraftVersion() {
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        when(campaignVersions.lockByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        stubClientBinding("[]");

        assertDenied(() -> service.updateDraft(
                campaign.getId(),
                1,
                new UpdateCampaignVersionDraftRequestDto(
                        null,
                        "Welcome Updated",
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
                        null),
                adminUser(),
                "corr-update-draft"));
    }

    @Test
    void emptyAdminBindingCannotSubmitVersion() {
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        when(campaignVersions.findByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        stubClientBinding("[]");

        assertDenied(() -> service.submit(
                campaign.getId(),
                1,
                new CampaignVersionTransitionRequestDto("ready"),
                adminUser(),
                "corr-submit"));
    }

    @Test
    void emptyAdminBindingCannotApproveVersion() {
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        when(campaignVersions.findByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        stubClientBinding("[]");

        assertDenied(() -> service.approve(
                campaign.getId(),
                1,
                new CampaignVersionTransitionRequestDto("approved"),
                reviewerUser(),
                "corr-approve"));
    }

    @Test
    void emptyAdminBindingCannotRejectVersion() {
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        when(campaignVersions.findByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        stubClientBinding("[]");

        assertDenied(() -> service.reject(
                campaign.getId(),
                1,
                new CampaignVersionTransitionRequestDto("needs work"),
                reviewerUser(),
                "corr-reject"));
    }

    @Test
    void emptyAdminBindingCannotPublishVersion() {
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        when(campaignVersions.lockByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        when(campaigns.findById(campaign.getId())).thenReturn(Optional.of(campaign));
        stubClientBinding("[]");

        assertDenied(() -> service.publish(
                campaign.getId(),
                1,
                new CampaignVersionTransitionRequestDto("publish"),
                adminUser(),
                "corr-publish"));
    }

    @Test
    void emptyAdminBindingCannotRollbackVersion() {
        IncentiveCampaign campaign = campaign();
        IncentiveCampaignVersion version = new IncentiveCampaignVersion(campaign, 1, "creator");
        when(campaignVersions.findByCampaignIdAndVersionNumber(campaign.getId(), 1))
                .thenReturn(Optional.of(version));
        stubClientBinding("[]");

        assertDenied(() -> service.rollback(
                campaign.getId(),
                1,
                new RollbackCampaignVersionRequestDto("rollback"),
                adminUser(),
                "corr-rollback"));
    }

    private void assertDenied(Runnable operation) {
        assertThatThrownBy(operation::run)
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("no allowed operations");
    }

    private void stubClientBinding(String allowedOperations) {
        when(applications.findByTenantIdAndApplicationId("courseflow", "lms"))
                .thenReturn(Optional.of(new IncentiveApplication(
                        "courseflow",
                        "lms",
                        "CourseFlow LMS",
                        "ACTIVE",
                        "admin")));
        when(clientBindings.findByTenantIdAndApplicationIdAndClientId("courseflow", "lms", "api-gateway"))
                .thenReturn(Optional.of(new IncentiveApplicationClientBinding(
                        "courseflow",
                        "lms",
                        "api-gateway",
                        "ACTIVE",
                        allowedOperations,
                        "admin")));
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

    private CurrentUser adminUser() {
        return new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));
    }

    private CurrentUser reviewerUser() {
        return new CurrentUser(
                2L,
                "reviewer@example.com",
                "INCENTIVE_REVIEWER",
                Set.of(),
                Set.of(new RoleAssignment("INCENTIVE_REVIEWER", "APPLICATION", "courseflow:lms")),
                fakeInternalToken("api-gateway", "user"));
    }

    private static String fakeInternalToken(String clientId, String actorType) {
        String payload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(("{\"azp\":\"" + clientId + "\",\"actor_type\":\"" + actorType + "\"}")
                        .getBytes(StandardCharsets.UTF_8));
        return "test." + payload + ".signature";
    }
}
