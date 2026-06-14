package edu.courseflow.commonlibrary.web;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.context.request.ServletWebRequest;

class CurrentUserArgumentResolverTest {

    private final CurrentUserArgumentResolver resolver = new CurrentUserArgumentResolver();

    @Test
    void resolvesInternalTokenFromInternalAuthorizationHeaderFirst() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "Bearer internal-token");
        request.addHeader(HttpHeaders.AUTHORIZATION, "Bearer fallback-token");

        CurrentUser user = (CurrentUser) resolver.resolveArgument(
                null, null, new ServletWebRequest(request), null);

        assertThat(user.internalToken()).isEqualTo("internal-token");
    }

    @Test
    void fallsBackToAuthorizationHeaderForDirectInternalCalls() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(HttpHeaders.AUTHORIZATION, "Bearer direct-service-token");

        CurrentUser user = (CurrentUser) resolver.resolveArgument(
                null, null, new ServletWebRequest(request), null);

        assertThat(user.internalToken()).isEqualTo("direct-service-token");
    }

    @Test
    void ignoresMalformedInternalAuthorizationAndUsesVerifiedBearerCandidate() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(GatewayHeaders.INTERNAL_AUTHORIZATION, "fake.jwt.payload");
        request.addHeader(HttpHeaders.AUTHORIZATION, "Bearer verified-service-token");

        CurrentUser user = (CurrentUser) resolver.resolveArgument(
                null, null, new ServletWebRequest(request), null);

        assertThat(user.internalToken()).isEqualTo("verified-service-token");
    }

    @Test
    void doesNotResolveNonBearerAuthorizationAsInternalToken() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(HttpHeaders.AUTHORIZATION, "Basic abc123");

        CurrentUser user = (CurrentUser) resolver.resolveArgument(
                null, null, new ServletWebRequest(request), null);

        assertThat(user.internalToken()).isNull();
    }
}
