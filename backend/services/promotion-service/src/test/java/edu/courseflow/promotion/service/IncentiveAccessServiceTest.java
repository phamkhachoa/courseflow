package edu.courseflow.promotion.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatNoException;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ErrorCodeCarrier;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.CreateApplicationClientBindingRequestDto;
import edu.courseflow.promotion.model.IncentiveApplication;
import edu.courseflow.promotion.model.IncentiveApplicationClientBinding;
import edu.courseflow.promotion.repository.IncentiveApplicationClientBindingRepository;
import edu.courseflow.promotion.repository.IncentiveApplicationRepository;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;

class IncentiveAccessServiceTest {

    private final IncentiveAccessService access = new IncentiveAccessService(
            null,
            null,
            null,
            new ObjectMapper().findAndRegisterModules());

    @Test
    void userActorCannotSubmitRuntimeFacts() {
        CurrentUser user = new CurrentUser(
                42L,
                "learner@example.com",
                "STUDENT",
                Set.of("STUDENT"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));

        assertThatThrownBy(() -> access.requireTrustedRuntimeCaller("tenant", "app", user, "evaluate"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("trusted application service");
    }

    @Test
    void serviceActorCanSubmitRuntimeFacts() {
        CurrentUser service = new CurrentUser(
                null,
                null,
                null,
                Set.of(),
                Set.of(),
                fakeInternalToken("checkout-service", "service"));

        assertThatNoException()
                .isThrownBy(() -> access.requireTrustedRuntimeCaller("tenant", "app", service, "evaluate"));
    }

    @Test
    void platformAdminCannotSubmitRuntimeEvaluateFacts() {
        CurrentUser admin = new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));

        assertThatThrownBy(() -> access.requireTrustedRuntimeCaller("tenant", "app", admin, "evaluate"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("trusted application service");
    }

    @Test
    void platformAdminCannotMutateRuntimeLedgerWithRawFacts() {
        CurrentUser admin = new CurrentUser(
                1L,
                "admin@example.com",
                "ADMIN",
                Set.of("ADMIN"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));

        assertThatThrownBy(() -> access.requireTrustedRuntimeCaller("tenant", "app", admin, "reserve"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("trusted application service");
    }

    @Test
    void exposesSourceClientAndActorTypeForAuditMetadata() {
        CurrentUser user = new CurrentUser(
                42L,
                "learner@example.com",
                "STUDENT",
                Set.of("STUDENT"),
                Set.of(),
                fakeInternalToken("api-gateway", "user"));

        assertThat(access.sourceClientId(user)).isEqualTo("api-gateway");
        assertThat(access.actorType(user)).isEqualTo("user");
    }

    @Test
    void emptyAllowedOperationsDenyAllServiceOperations() {
        Fixture fixture = fixture(new IncentiveApplicationClientBinding(
                "courseflow",
                "lms",
                "checkout-service",
                "ACTIVE",
                "[]",
                "admin"));

        assertThatThrownBy(() -> fixture.access().requireActiveApplication(
                "courseflow",
                "lms",
                serviceUser("checkout-service"),
                "reserve"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("no allowed operations");
    }

    @Test
    void explicitAllowedOperationPassesBindingGate() {
        Fixture fixture = fixture(new IncentiveApplicationClientBinding(
                "courseflow",
                "lms",
                "checkout-service",
                "ACTIVE",
                "[\"reserve\"]",
                "admin"));

        assertThatNoException()
                .isThrownBy(() -> fixture.access().requireActiveApplication(
                        "courseflow",
                        "lms",
                        serviceUser("checkout-service"),
                        "reserve"));
    }

    @Test
    void bindingDeniedWhenOperationNotExplicitlyAllowed() {
        Fixture fixture = fixture(new IncentiveApplicationClientBinding(
                "courseflow",
                "lms",
                "checkout-service",
                "ACTIVE",
                "[\"evaluate\"]",
                "admin"));

        assertThatThrownBy(() -> fixture.access().requireActiveApplication(
                "courseflow",
                "lms",
                serviceUser("checkout-service"),
                "reserve"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("not allowed to run operation: reserve");
    }

    @Test
    void bindingDeniedWhenServiceTokenMissingOperationScope() {
        Fixture fixture = fixture(new IncentiveApplicationClientBinding(
                "courseflow",
                "lms",
                "checkout-service",
                "ACTIVE",
                "[\"reserve\"]",
                "admin"));

        assertThatThrownBy(() -> fixture.access().requireActiveApplication(
                "courseflow",
                "lms",
                serviceUser("checkout-service", InternalScopes.SERVICE),
                "reserve"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("Missing internal promotion operation scope: "
                        + InternalScopes.PROMOTION_RESERVE);
    }

    @Test
    void bindingDeniedWhenServiceTokenHasWrongOperationScope() {
        Fixture fixture = fixture(new IncentiveApplicationClientBinding(
                "courseflow",
                "lms",
                "checkout-service",
                "ACTIVE",
                "[\"reserve\"]",
                "admin"));

        assertThatThrownBy(() -> fixture.access().requireActiveApplication(
                "courseflow",
                "lms",
                serviceUser("checkout-service", InternalScopes.PROMOTION_EVALUATE),
                "reserve"))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("Missing internal promotion operation scope: "
                        + InternalScopes.PROMOTION_RESERVE);
    }

    @Test
    void upsertClientBindingRejectsUnsupportedOperation() {
        IncentiveApplication application = new IncentiveApplication(
                "courseflow",
                "lms",
                "CourseFlow LMS",
                "ACTIVE",
                "admin");
        IncentiveApplicationRepository applications = mock(IncentiveApplicationRepository.class);
        IncentiveApplicationClientBindingRepository bindings = mock(IncentiveApplicationClientBindingRepository.class);
        IncentiveAuditEventRepository audits = mock(IncentiveAuditEventRepository.class);
        IncentiveAccessService scopedAccess = new IncentiveAccessService(
                applications,
                bindings,
                audits,
                new ObjectMapper().findAndRegisterModules());
        when(applications.findById(application.getId())).thenReturn(Optional.of(application));

        assertThatThrownBy(() -> scopedAccess.upsertClientBinding(
                application.getId(),
                new CreateApplicationClientBindingRequestDto(
                        "checkout-service",
                        "ACTIVE",
                        List.of("reserve", "refund-everything")),
                adminUser(),
                "corr-binding"))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("Unsupported incentive client operation");
    }

    @Test
    void couponImportManageAllowsScopedOperatorWithoutGrantingApplicationAdmin() {
        CurrentUser operator = scopedUser("INCENTIVE_OPERATOR", "APPLICATION", "courseflow:lms");

        assertThatNoException()
                .isThrownBy(() -> access.requireCouponImportManageAccess("courseflow", "lms", operator));
        assertThat(access.canCouponImportManageAccess("courseflow", "lms", operator)).isTrue();
        assertThat(access.canAdminAccess("courseflow", "lms", operator)).isFalse();
        assertThatThrownBy(() -> access.requireAdminAccess("courseflow", "lms", operator))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("Not allowed to manage incentive application");
    }

    @Test
    void couponImportReadAllowsReviewerButManageDoesNot() {
        CurrentUser reviewer = scopedUser("INCENTIVE_REVIEWER", "APPLICATION", "courseflow:lms");

        assertThatNoException()
                .isThrownBy(() -> access.requireCouponImportReadAccess("courseflow", "lms", reviewer));
        assertThat(access.canCouponImportReadAccess("courseflow", "lms", reviewer)).isTrue();
        assertThat(access.canCouponImportManageAccess("courseflow", "lms", reviewer)).isFalse();
        assertThatThrownBy(() -> access.requireCouponImportManageAccess("courseflow", "lms", reviewer))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("Not allowed to operate coupon import")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.COUPON_IMPORT_MANAGE_FORBIDDEN));
    }

    @Test
    void couponImportOperatorCannotReviewApprovalDecisions() {
        CurrentUser operator = scopedUser("INCENTIVE_OPERATOR", "APPLICATION", "courseflow:lms");

        assertThatThrownBy(() -> access.requireReviewAccess("courseflow", "lms", operator))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("Not allowed to review incentive campaign");

        assertThatThrownBy(() -> access.requireCouponImportReviewAccess("courseflow", "lms", operator))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("Not allowed to review coupon import approval")
                .satisfies(error -> assertThat(((ErrorCodeCarrier) error).errorCode())
                        .isEqualTo(PromotionErrorCodes.COUPON_IMPORT_REVIEW_FORBIDDEN));
    }

    private Fixture fixture(IncentiveApplicationClientBinding binding) {
        IncentiveApplicationRepository applications = mock(IncentiveApplicationRepository.class);
        IncentiveApplicationClientBindingRepository bindings = mock(IncentiveApplicationClientBindingRepository.class);
        IncentiveAuditEventRepository audits = mock(IncentiveAuditEventRepository.class);
        IncentiveAccessService scopedAccess = new IncentiveAccessService(
                applications,
                bindings,
                audits,
                new ObjectMapper().findAndRegisterModules());
        when(applications.findByTenantIdAndApplicationId("courseflow", "lms"))
                .thenReturn(Optional.of(new IncentiveApplication(
                        "courseflow",
                        "lms",
                        "CourseFlow LMS",
                        "ACTIVE",
                        "admin")));
        when(bindings.findByTenantIdAndApplicationIdAndClientId(
                "courseflow",
                "lms",
                binding.getClientId()))
                .thenReturn(Optional.of(binding));
        return new Fixture(scopedAccess);
    }

    private CurrentUser serviceUser(String clientId) {
        return serviceUser(clientId,
                InternalScopes.PROMOTION_EVALUATE,
                InternalScopes.PROMOTION_RESERVE,
                InternalScopes.PROMOTION_COMMIT,
                InternalScopes.PROMOTION_CANCEL,
                InternalScopes.PROMOTION_REVERSE,
                InternalScopes.PROMOTION_ADMIN);
    }

    private CurrentUser serviceUser(String clientId, String... scopes) {
        return new CurrentUser(
                null,
                null,
                null,
                Set.of(),
                Set.of(),
                fakeInternalToken(clientId, "service", scopes));
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

    private CurrentUser scopedUser(String role, String scopeType, String scopeId) {
        return new CurrentUser(
                2L,
                role.toLowerCase(Locale.ROOT) + "@example.com",
                role,
                Set.of(role),
                Set.of(new CurrentUser.RoleAssignment(role, scopeType, scopeId)),
                fakeInternalToken("api-gateway", "user"));
    }

    private static String fakeInternalToken(String clientId, String actorType) {
        return fakeInternalToken(clientId, actorType, new String[0]);
    }

    private static String fakeInternalToken(String clientId, String actorType, String... scopes) {
        String scopeClaim = scopes == null || scopes.length == 0
                ? ""
                : ",\"scope\":\"" + String.join(" ", scopes) + "\",\"scp\":[\""
                + String.join("\",\"", scopes) + "\"]";
        String payload = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(("{\"azp\":\"" + clientId + "\",\"actor_type\":\"" + actorType + "\""
                        + scopeClaim + "}")
                        .getBytes(StandardCharsets.UTF_8));
        return "test." + payload + ".signature";
    }

    private record Fixture(IncentiveAccessService access) {
    }
}
