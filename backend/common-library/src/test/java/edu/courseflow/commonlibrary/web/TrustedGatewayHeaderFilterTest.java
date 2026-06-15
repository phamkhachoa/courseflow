package edu.courseflow.commonlibrary.web;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import jakarta.servlet.ServletException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class TrustedGatewayHeaderFilterTest {

    private static final String INTERNAL_SECRET = "internal-jwt-secret-that-is-at-least-32-bytes";

    @Test
    void allowsPublicRequestWithoutIdentityHeadersWhenSecretIsNotConfigured() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter("");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/public/courses");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsInternalEndpointWithoutInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/courses");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).contains("Trusted gateway internal token is required");
    }

    @Test
    void recordsMissingInternalJwtRejectionMetric() throws ServletException, IOException {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET, meterRegistry);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/courses");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(meterRegistry
                        .get("courseflow.internal_jwt.rejections")
                        .tag("reason", "missing")
                        .tag("request_type", "internal_endpoint")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void rejectsBackofficeEndpointWithoutInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/backoffice/admin-users");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void recordsBackofficeInternalJwtRejectionMetric() throws ServletException, IOException {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET, meterRegistry);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/backoffice/admin-users");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(meterRegistry
                        .get("courseflow.internal_jwt.rejections")
                        .tag("reason", "missing")
                        .tag("request_type", "backoffice_endpoint")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void rejectsIdentityHeadersWithoutInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void recordsIdentityMismatchRejectionMetric() throws ServletException, IOException {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET, meterRegistry);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("99"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(meterRegistry
                        .get("courseflow.internal_jwt.rejections")
                        .tag("reason", "identity_mismatch")
                        .tag("request_type", "internal_endpoint")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void allowsInternalEndpointWithServiceInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/courses");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken());
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void allowsBackofficeEndpointWithServiceInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/backoffice/admin-users");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.BACKOFFICE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsSensitiveInternalEndpointWhenServiceScopeIsTooBroad() throws ServletException, IOException {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET, meterRegistry);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/authz/check");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken());
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(meterRegistry
                        .get("courseflow.internal_jwt.rejections")
                        .tag("reason", "insufficient_scope")
                        .tag("request_type", "internal_endpoint")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void allowsSensitiveInternalEndpointWithRequiredServiceScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/authz/check");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.AUTHZ_CHECK));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsPromotionEvaluateWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/incentives/evaluate");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsPromotionEvaluateWithEvaluateScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/incentives/evaluate");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_EVALUATE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsAnalyticsFunnelIngestWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/marketing/funnel/events");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsAnalyticsFunnelIngestWithFunnelWriteScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/marketing/funnel/events");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.ANALYTICS_FUNNEL_WRITE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsAnalyticsWarehouseExportWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/warehouse/exports");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsAnalyticsWarehouseExportWithExportReadScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/warehouse/exports");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.ANALYTICS_EXPORT_READ));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsAnalyticsRecommendationEventWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/recommendations/events");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsAnalyticsRecommendationEventWithEventWriteScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/recommendations/events");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.ANALYTICS_EVENT_WRITE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsAnalyticsRecommendationModelBatchWhenServiceOnlyHasGenericScope()
            throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/recommendations/batch/related-course-pairs/active-model/materialize");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsAnalyticsRecommendationModelBatchWithModelWriteScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/analytics/recommendations/batch/related-course-pairs/active-model/materialize");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.ANALYTICS_MODEL_WRITE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsRecommendationMlTrainingWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/recommendation-ml/related-courses:train");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsRecommendationMlTrainingWithTrainScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/recommendation-ml/related-courses:train");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.RECOMMENDATION_ML_TRAIN));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsRecommendationMlOpsRouteWithTrainScopeOnly() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "GET",
                "/internal/recommendation-ml/models");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.RECOMMENDATION_ML_TRAIN));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsRecommendationMlOpsRouteWithOpsScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "GET",
                "/internal/recommendation-ml/models");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.RECOMMENDATION_ML_OPS));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void allowsRecommendationMlInferenceWithInferScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "GET",
                "/internal/recommendation-ml/models/active");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.RECOMMENDATION_ML_INFER));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsPromotionReservationCommitWithReserveScopeOnly() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/incentives/reservations/00000000-0000-0000-0000-000000000001/commit");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_RESERVE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsPromotionReservationCreateWithReserveScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/incentives/reservations");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_RESERVE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void allowsPromotionReservationCommitWithCommitScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/incentives/reservations/00000000-0000-0000-0000-000000000001/commit");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_COMMIT));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void allowsPromotionReservationCancelWithCancelScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/incentives/reservations/00000000-0000-0000-0000-000000000001/cancel");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_CANCEL));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void allowsPromotionRedemptionReverseWithReverseScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/incentives/redemptions/00000000-0000-0000-0000-000000000001/reverse");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_REVERSE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void allowsPromotionAdminEndpointWithPromotionAdminScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/incentives/campaigns");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.PROMOTION_ADMIN));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsLoyaltyEarnWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/loyalty/points:earn");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsLoyaltyEarnWithEarnScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/loyalty/points:earn");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.LOYALTY_EARN));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsLoyaltyBurnWhenOnlyEarnScopeIsGranted() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/loyalty/points:burn");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.LOYALTY_EARN));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsLoyaltyReadWithReadScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/loyalty/ledger");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.LOYALTY_READ));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsUserInternalJwtOnServiceOnlyInternalEndpointEvenWhenIdentityHeadersMatch()
            throws ServletException, IOException {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET, meterRegistry);
        MockHttpServletRequest request = requestWithIdentityHeaders("POST", "/internal/authz/check");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(meterRegistry
                        .get("courseflow.internal_jwt.rejections")
                        .tag("reason", "wrong_actor_type")
                        .tag("request_type", "internal_endpoint")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void rejectsUserInternalJwtOnCourseVerifiedProgressEndpointEvenWhenIdentityHeadersMatch()
            throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders(
                "POST",
                "/internal/courses/30000000-0000-0000-0000-000000000001/modules/30000000-0000-0000-0000-000000001001/items/30000000-0000-0000-0000-000000002001/progress/verified");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void rejectsUserInternalJwtOnCourseInternalProgressEndpointEvenWhenIdentityHeadersMatch()
            throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders(
                "GET",
                "/internal/courses/30000000-0000-0000-0000-000000000001/modules/progress/internal");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsCourseVerifiedProgressEndpointWithServiceInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest(
                "POST",
                "/internal/courses/30000000-0000-0000-0000-000000000001/modules/items/progress/verified");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsUserInternalJwtOnEnrollmentServiceOnlyEndpointEvenWhenIdentityHeadersMatch()
            throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders("GET", "/internal/enrollments/access");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void rejectsUserInternalJwtOnEnrollmentPaymentServiceOnlyEndpointEvenWhenIdentityHeadersMatch()
            throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders(
                "POST",
                "/internal/enrollments/orders/30000000-0000-0000-0000-000000000001:record-payment");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsEnrollmentServiceOnlyEndpointWithServiceInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/learner-memberships");
        request.addParameter("studentId", "42");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsRolePolicyReadWhenServiceOnlyHasGenericScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/roles");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.SERVICE));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsRolePolicyReadWithRoleManagementScope() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/permissions");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + serviceInternalToken(
                InternalScopes.ROLE_MANAGEMENT_READ));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsUserInternalJwtWithoutGatewayIdentityHeaders() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/courses");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsIdentityHeadersWhenInternalJwtMatchesGatewayHeaders() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsIdentityHeadersWhenInternalJwtSubjectDoesNotMatchHeaders() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("99"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void rejectsIdentityHeadersWhenPrimaryRoleIsNotInInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.removeHeader(GatewayHeaders.USER_ROLE);
        request.addHeader(GatewayHeaders.USER_ROLE, "ADMIN");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void rejectsIdentityHeadersWhenInternalJwtActorTypeIsMissing() throws ServletException, IOException {
        SimpleMeterRegistry meterRegistry = new SimpleMeterRegistry();
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET, meterRegistry);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalTokenWithoutActorType("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(meterRegistry
                        .get("courseflow.internal_jwt.rejections")
                        .tag("reason", "wrong_actor_type")
                        .tag("request_type", "internal_endpoint")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void rejectsIdentityHeadersWhenRoleSetDoesNotMatchInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.USER_ROLES, "STUDENT,ADMIN");
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken("42"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsIdentityHeadersWhenRoleScopesMatchInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.USER_ROLES, "STUDENT");
        request.addHeader(GatewayHeaders.USER_ROLE_SCOPES, roleScope("STUDENT", "COURSE", "course-1"));
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken(
                "42", List.of(Map.of("code", "STUDENT", "scopeType", "COURSE", "scopeId", "course-1"))));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsIdentityHeadersWhenRoleScopesDoNotMatchInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.USER_ROLES, "STUDENT");
        request.addHeader(GatewayHeaders.USER_ROLE_SCOPES, roleScope("STUDENT", "COURSE", "course-2"));
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer " + userInternalToken(
                "42", List.of(Map.of("code", "STUDENT", "scopeType", "COURSE", "scopeId", "course-1"))));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    private TrustedGatewayHeaderFilter filter(String secret) {
        return filter(secret, null);
    }

    private TrustedGatewayHeaderFilter filter(String secret, SimpleMeterRegistry meterRegistry) {
        InternalJwtProperties properties = new InternalJwtProperties(
                secret,
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "test-service");
        return new TrustedGatewayHeaderFilter(new InternalJwtService(properties), meterRegistry);
    }

    private MockHttpServletRequest requestWithIdentityHeaders() {
        return requestWithIdentityHeaders("GET", "/internal/courses");
    }

    private MockHttpServletRequest requestWithIdentityHeaders(String method, String path) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, path);
        request.addHeader(GatewayHeaders.USER_ID, "42");
        request.addHeader(GatewayHeaders.USER_EMAIL, "learner@courseflow.local");
        request.addHeader(GatewayHeaders.USER_ROLE, "STUDENT");
        return request;
    }

    private String userInternalToken(String userId) {
        return userInternalToken(userId, List.of(Map.of("code", "STUDENT", "scopeType", "PLATFORM")));
    }

    private String userInternalToken(String userId, List<Map<String, Object>> roleAssignments) {
        return userInternalToken(userId, roleAssignments, true);
    }

    private String userInternalTokenWithoutActorType(String userId) {
        return userInternalToken(userId, List.of(Map.of("code", "STUDENT", "scopeType", "PLATFORM")), false);
    }

    private String userInternalToken(String userId, List<Map<String, Object>> roleAssignments, boolean includeActorType) {
        Instant now = Instant.now();
        var builder = Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject(userId)
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("uid", userId)
                .claim("email", "learner@courseflow.local")
                .claim("roles", List.of("STUDENT"))
                .claim("role_assignments", roleAssignments)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)));
        if (includeActorType) {
            builder.claim("actor_type", "user");
        }
        return builder.signWith(Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8))).compact();
    }

    private String roleScope(String code, String scopeType, String scopeId) {
        return encode(code) + "." + encode(scopeType) + "." + encode(scopeId);
    }

    private String encode(String value) {
        if (value == null || value.isBlank()) {
            return "";
        }
        return Base64.getUrlEncoder().withoutPadding()
                .encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    private String serviceInternalToken(String... scopes) {
        Instant now = Instant.now();
        List<String> grantedScopes = scopes == null || scopes.length == 0
                ? List.of(InternalScopes.SERVICE)
                : List.of(scopes);
        return Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject("service:test-service")
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("actor_type", "service")
                .claim("scope", String.join(" ", grantedScopes))
                .claim("scp", grantedScopes)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)))
                .signWith(Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}
