package edu.courseflow.tokenconverter.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import edu.courseflow.tokenconverter.dto.TokenExchangeResponse;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.crypto.SecretKey;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

class TokenExchangeServiceTest {

    private static final String EXTERNAL_SECRET = "external-jwt-secret-that-is-at-least-32-bytes";
    private static final String INTERNAL_SECRET = "internal-jwt-secret-that-is-at-least-32-bytes";

    private final TokenConverterProperties properties = new TokenConverterProperties(
            EXTERNAL_SECRET,
            "courseflow-identity",
            INTERNAL_SECRET,
            "courseflow-token-converter",
            "courseflow-services",
            "courseflow-services,course-service",
            180,
            30);
    private final TokenExchangeService service = new TokenExchangeService(
            new ExternalTokenVerifier(properties),
            new InternalTokenIssuer(properties, new ScopeMapper()),
            properties);

    @Test
    void exchangesExternalJwtForShortLivedInternalJwt() {
        TokenExchangeResponse response = service.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                "course:read learning:write admin:write");

        assertThat(response.token_type()).isEqualTo("Bearer");
        assertThat(response.expires_in()).isEqualTo(180);
        assertThat(response.scope()).contains("course:read").contains("learning:write");
        assertThat(response.scope()).doesNotContain("admin:write");

        Claims claims = Jwts.parser()
                .verifyWith(internalKey())
                .build()
                .parseSignedClaims(response.access_token())
                .getPayload();

        assertThat(claims.getIssuer()).isEqualTo("courseflow-token-converter");
        assertThat(claims.getSubject()).isEqualTo("4");
        assertThat(claims.get("uid")).isEqualTo("4");
        assertThat(claims.get("email")).isEqualTo("student@courseflow.local");
        assertThat(((Collection<?>) claims.get("aud")).stream().map(String::valueOf).toList())
                .contains("courseflow-services");
        assertThat(claims.get("roles", List.class)).contains("STUDENT");
        assertThat(claims.get("token_use")).isEqualTo("internal");
    }

    @Test
    void rejectsAudienceOutsideAllowlist() {
        assertThatThrownBy(() -> service.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalToken("student@courseflow.local", "4", "STUDENT"),
                "gradebook-service",
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    void rejectsExternalTokenFromUnexpectedIssuer() {
        assertThatThrownBy(() -> service.exchange(
                TokenExchangeService.TOKEN_EXCHANGE_GRANT,
                TokenExchangeService.ACCESS_TOKEN_TYPE,
                externalTokenWithIssuer("courseflow-other-issuer", "student@courseflow.local", "4", "STUDENT"),
                "courseflow-services",
                null))
                .isInstanceOf(ResponseStatusException.class)
                .extracting(ex -> ((ResponseStatusException) ex).getStatusCode())
                .isEqualTo(HttpStatus.UNAUTHORIZED);
    }

    private String externalToken(String subject, String userId, String... roleCodes) {
        return externalTokenWithIssuer("courseflow-identity", subject, userId, roleCodes);
    }

    private String externalTokenWithIssuer(String issuer, String subject, String userId, String... roleCodes) {
        Instant now = Instant.now();
        List<Map<String, Object>> roles = java.util.Arrays.stream(roleCodes)
                .map(code -> {
                    Map<String, Object> claim = new HashMap<>();
                    claim.put("code", code);
                    claim.put("scopeType", "PLATFORM");
                    claim.put("scopeId", null);
                    return claim;
                })
                .toList();
        return Jwts.builder()
                .issuer(issuer)
                .subject(subject)
                .claim("uid", userId)
                .claim("roles", roles)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(3600)))
                .signWith(Keys.hmacShaKeyFor(EXTERNAL_SECRET.getBytes(StandardCharsets.UTF_8)))
                .compact();
    }

    private SecretKey internalKey() {
        return Keys.hmacShaKeyFor(INTERNAL_SECRET.getBytes(StandardCharsets.UTF_8));
    }
}
