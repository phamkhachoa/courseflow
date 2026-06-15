package edu.courseflow.tokenconverter.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.sun.net.httpserver.HttpServer;
import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import io.jsonwebtoken.Jwts;
import java.math.BigInteger;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPublicKey;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

class ExternalTokenVerifierOidcTest {

    private static final String KID = "courseflow-token-converter-test-kid";
    private static final String INTERNAL_SECRET = "internal-jwt-secret-that-is-at-least-32-bytes";
    private static final String STS_SECRET = "api-gateway-sts-secret-that-is-at-least-32-bytes";

    private HttpServer jwksServer;
    private KeyPair keyPair;
    private String issuer;
    private String jwksUri;

    @BeforeEach
    void startJwksServer() throws Exception {
        keyPair = keyPair();
        jwksServer = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        jwksServer.createContext("/realms/courseflow/protocol/openid-connect/certs", exchange -> {
            byte[] body = jwks().getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        jwksServer.start();
        issuer = "http://127.0.0.1:" + jwksServer.getAddress().getPort() + "/realms/courseflow";
        jwksUri = issuer + "/protocol/openid-connect/certs";
    }

    @AfterEach
    void stopJwksServer() {
        if (jwksServer != null) {
            jwksServer.stop(0);
        }
    }

    @Test
    void acceptsOidcAccessTokenWithExpectedIssuerAudienceAndJwksSignature() {
        ExternalTokenVerifier verifier = new ExternalTokenVerifier(properties("courseflow-api"));

        ExternalTokenClaims claims = verifier.verify(token(issuer, List.of("courseflow-api")));

        assertThat(claims.issuer()).isEqualTo(issuer);
        assertThat(claims.subject()).isEqualTo("keycloak-user-subject");
    }

    @Test
    void rejectsOidcAccessTokenWithWrongIssuer() {
        ExternalTokenVerifier verifier = new ExternalTokenVerifier(properties("courseflow-api"));

        assertThatThrownBy(() -> verifier.verify(token("https://other-issuer.example.com", List.of("courseflow-api"))))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Invalid external token");
    }

    @Test
    void rejectsOidcAccessTokenWithWrongAudience() {
        ExternalTokenVerifier verifier = new ExternalTokenVerifier(properties("courseflow-api"));

        assertThatThrownBy(() -> verifier.verify(token(issuer, List.of("other-api"))))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Invalid external token");
    }

    @Test
    void rejectsOidcAccessTokenWithoutSubject() {
        ExternalTokenVerifier verifier = new ExternalTokenVerifier(properties("courseflow-api"));

        assertThatThrownBy(() -> verifier.verify(tokenWithoutSubject(issuer, List.of("courseflow-api"))))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Invalid external token");
    }

    private TokenConverterProperties properties(String audiences) {
        return new TokenConverterProperties(
                issuer,
                jwksUri,
                audiences,
                "HS256",
                INTERNAL_SECRET,
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                "api-gateway=" + STS_SECRET,
                "api-gateway",
                "internal:service,internal:token-exchange",
                "api-gateway=internal:service,internal:token-exchange",
                180,
                30);
    }

    private String token(String tokenIssuer, List<String> audiences) {
        Instant now = Instant.now();
        return Jwts.builder()
                .header()
                .keyId(KID)
                .and()
                .issuer(tokenIssuer)
                .subject("keycloak-user-subject")
                .claim("aud", audiences)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(300)))
                .signWith(keyPair.getPrivate())
                .compact();
    }

    private String tokenWithoutSubject(String tokenIssuer, List<String> audiences) {
        Instant now = Instant.now();
        return Jwts.builder()
                .header()
                .keyId(KID)
                .and()
                .issuer(tokenIssuer)
                .claim("aud", audiences)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(300)))
                .signWith(keyPair.getPrivate())
                .compact();
    }

    private String jwks() {
        RSAPublicKey publicKey = (RSAPublicKey) keyPair.getPublic();
        return """
                {"keys":[{"kty":"RSA","use":"sig","alg":"RS256","kid":"%s","n":"%s","e":"%s"}]}
                """.formatted(KID, encode(publicKey.getModulus()), encode(publicKey.getPublicExponent()));
    }

    private static String encode(BigInteger value) {
        byte[] bytes = value.toByteArray();
        if (bytes.length > 1 && bytes[0] == 0) {
            bytes = java.util.Arrays.copyOfRange(bytes, 1, bytes.length);
        }
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private static KeyPair keyPair() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        return generator.generateKeyPair();
    }
}
