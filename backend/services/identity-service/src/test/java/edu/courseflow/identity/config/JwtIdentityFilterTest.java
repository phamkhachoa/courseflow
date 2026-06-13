package edu.courseflow.identity.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import edu.courseflow.identity.service.AccessTokenRevocationService;
import io.jsonwebtoken.Jwts;
import jakarta.servlet.http.HttpServletRequest;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class JwtIdentityFilterTest {

    private static final String SECRET = "identity-test-secret-with-at-least-32-bytes";

    private JwtProperties jwtProperties;
    private AccessTokenRevocationService revocations;
    private JwtIdentityFilter filter;

    @BeforeEach
    void setUp() {
        jwtProperties = new JwtProperties(SECRET, 900, "courseflow-identity", 60);
        revocations = mock(AccessTokenRevocationService.class);
        when(revocations.isAccepted(anyLong(), anyString(), any())).thenReturn(true);
        filter = new JwtIdentityFilter(jwtProperties, revocations);
    }

    @Test
    void percentEncodedAdminPathStillRequiresAdmin() throws Exception {
        MockHttpServletRequest request = request("POST", "/internal/users/42/%61ssignments",
                token("operator@example.com", 7L, "TA", true, "courseflow-identity"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(403);
        assertThat(response.getContentAsString()).contains("ADMIN");
    }

    @Test
    void adminCanReachDecodedAdminPath() throws Exception {
        MockHttpServletRequest request = request("POST", "/internal/users/42/%61ssignments",
                token("admin@example.com", 1L, "ADMIN", true, "courseflow-identity"));
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isNotNull();
        HttpServletRequest wrapped = (HttpServletRequest) chain.getRequest();
        assertThat(wrapped.getHeader("X-User-Id")).isEqualTo("1");
        assertThat(wrapped.getAttribute(JwtIdentityFilter.ACCESS_TOKEN_JTI_ATTRIBUTE)).isNotNull();
    }

    @Test
    void revokedAccessTokenIsRejected() throws Exception {
        when(revocations.isAccepted(anyLong(), anyString(), any())).thenReturn(false);
        MockHttpServletRequest request = request("GET", "/backoffice/users",
                token("admin@example.com", 1L, "ADMIN", true, "courseflow-identity"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).contains("revoked");
    }

    @Test
    void privacyExportRequiresAdminEvenThoughItIsReadOnly() throws Exception {
        MockHttpServletRequest request = request("GET", "/backoffice/users/42/privacy-export",
                token("operator@example.com", 7L, "TA", true, "courseflow-identity"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(403);
        assertThat(response.getContentAsString()).contains("ADMIN");
    }

    @Test
    void wrongIssuerIsRejected() throws Exception {
        MockHttpServletRequest request = request("GET", "/backoffice/users",
                token("admin@example.com", 1L, "ADMIN", true, "wrong-issuer"));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void prometheusActuatorEndpointIsPublicForScraping() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/actuator/prometheus");
        request.setRequestURI("/actuator/prometheus");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isNotNull();
    }

    @Test
    void emailVerificationEndpointIsPublic() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/auth/email/verify");
        request.setRequestURI("/auth/email/verify");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isNotNull();
    }

    private MockHttpServletRequest request(String method, String uri, String token) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, uri);
        request.setRequestURI(uri);
        request.addHeader("Authorization", "Bearer " + token);
        return request;
    }

    private String token(String email, Long userId, String roleCode, boolean operator, String issuer) {
        Instant now = Instant.now();
        return Jwts.builder()
                .id(UUID.randomUUID().toString())
                .issuer(issuer)
                .subject(email)
                .claim("uid", userId)
                .claim("roles", List.of(Map.of(
                        "code", roleCode,
                        "rank", "ADMIN".equals(roleCode) ? 100 : 30,
                        "isOperator", operator)))
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(900)))
                .signWith(jwtProperties.secretKey())
                .compact();
    }
}
