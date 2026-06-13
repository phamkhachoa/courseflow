package edu.courseflow.commonlibrary.web;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.ServletException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.List;
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
    void rejectsIdentityHeadersWithoutInternalJwt() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = filter(INTERNAL_SECRET);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
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

    private TrustedGatewayHeaderFilter filter(String secret) {
        InternalJwtProperties properties = new InternalJwtProperties(
                secret,
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "test-service");
        return new TrustedGatewayHeaderFilter(new InternalJwtService(properties));
    }

    private MockHttpServletRequest requestWithIdentityHeaders() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/courses");
        request.addHeader(GatewayHeaders.USER_ID, "42");
        request.addHeader(GatewayHeaders.USER_EMAIL, "learner@courseflow.local");
        request.addHeader(GatewayHeaders.USER_ROLE, "STUDENT");
        return request;
    }

    private String userInternalToken(String userId) {
        Instant now = Instant.now();
        return Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject(userId)
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("uid", userId)
                .claim("email", "learner@courseflow.local")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)))
                .signWith(Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }

    private String serviceInternalToken() {
        Instant now = Instant.now();
        return Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject("service:test-service")
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("actor_type", "service")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)))
                .signWith(Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}
