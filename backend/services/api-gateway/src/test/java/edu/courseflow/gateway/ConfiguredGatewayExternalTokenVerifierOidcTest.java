package edu.courseflow.gateway;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.sun.net.httpserver.HttpServer;
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

class ConfiguredGatewayExternalTokenVerifierOidcTest {

    private static final String KID = "courseflow-test-kid";

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
    void acceptsTokenWithExpectedIssuerAudienceAndJwksSignature() {
        ConfiguredGatewayExternalTokenVerifier verifier = verifier("courseflow-api");

        assertThatCode(() -> verifier.verify(token(issuer, List.of("courseflow-api"))).block())
                .doesNotThrowAnyException();
    }

    @Test
    void rejectsTokenWithWrongIssuer() {
        ConfiguredGatewayExternalTokenVerifier verifier = verifier("courseflow-api");

        assertThatThrownBy(() -> verifier.verify(token("https://other-issuer.example.com", List.of("courseflow-api")))
                .block())
                .hasMessageContaining("The iss claim is not valid");
    }

    @Test
    void rejectsTokenWithWrongAudience() {
        ConfiguredGatewayExternalTokenVerifier verifier = verifier("courseflow-api");

        assertThatThrownBy(() -> verifier.verify(token(issuer, List.of("other-api"))).block())
                .hasMessageContaining("Token audience is not accepted by CourseFlow");
    }

    @Test
    void rejectsTokenWithoutSubject() {
        ConfiguredGatewayExternalTokenVerifier verifier = verifier("courseflow-api");

        assertThatThrownBy(() -> verifier.verify(tokenWithoutSubject(issuer, List.of("courseflow-api"))).block())
                .hasMessageContaining("Token subject is required by CourseFlow");
    }

    private ConfiguredGatewayExternalTokenVerifier verifier(String audiences) {
        ExternalTokenProperties properties = new ExternalTokenProperties(
                issuer,
                jwksUri,
                audiences);
        return new ConfiguredGatewayExternalTokenVerifier(properties);
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
