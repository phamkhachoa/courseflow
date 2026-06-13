package edu.courseflow.chat.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class ChatJwtVerifierTest {

    private static final String INTERNAL_SECRET = "internal-jwt-secret-that-is-at-least-32-bytes";

    @Test
    void exchangesExternalTokenAndBuildsPrincipalFromInternalJwt() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        String internalToken = internalToken();
        server.expect(once(), requestTo("http://token-converter/oauth/token"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("client_id=chat-service")))
                .andExpect(content().string(org.hamcrest.Matchers.containsString("client_secret=chat-secret")))
                .andRespond(withSuccess(
                        "{\"access_token\":\"" + internalToken + "\",\"token_type\":\"Bearer\"}",
                        MediaType.APPLICATION_JSON));

        ChatJwtVerifier verifier = new ChatJwtVerifier(
                builder,
                internalJwt(),
                "http://token-converter",
                "courseflow-services",
                "chat-service",
                "chat-secret");

        ChatPrincipal principal = verifier.verify("Bearer external-keycloak-token");

        assertThat(principal.id()).isEqualTo(42L);
        assertThat(principal.email()).isEqualTo("learner@example.com");
        assertThat(principal.role()).isEqualTo("STUDENT");
        assertThat(principal.roles()).containsExactly("STUDENT");
        assertThat(principal.roleAssignments()).containsExactly(new CurrentUser.RoleAssignment(
                "STUDENT",
                "COURSE",
                "course-1"));
        server.verify();
    }

    @Test
    void rejectsWhenTokenConverterCannotIssueInternalToken() {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(once(), requestTo("http://token-converter/oauth/token"))
                .andRespond(withServerError());
        ChatJwtVerifier verifier = new ChatJwtVerifier(
                builder,
                internalJwt(),
                "http://token-converter",
                "courseflow-services",
                "chat-service",
                "chat-secret");

        assertThatThrownBy(() -> verifier.verify("Bearer external-keycloak-token"))
                .isInstanceOf(JwtException.class)
                .hasMessageContaining("Token converter rejected");
        server.verify();
    }

    private InternalJwtService internalJwt() {
        return new InternalJwtService(new InternalJwtProperties(
                INTERNAL_SECRET,
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "chat-service"));
    }

    private String internalToken() {
        Instant now = Instant.now();
        return Jwts.builder()
                .issuer("courseflow-token-converter")
                .subject("42")
                .claim("aud", List.of("courseflow-services"))
                .claim("token_use", "internal")
                .claim("uid", "42")
                .claim("email", "learner@example.com")
                .claim("roles", List.of("STUDENT"))
                .claim("role_assignments", List.of(Map.of(
                        "code", "STUDENT",
                        "scopeType", "COURSE",
                        "scopeId", "course-1")))
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)))
                .signWith(Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }
}
