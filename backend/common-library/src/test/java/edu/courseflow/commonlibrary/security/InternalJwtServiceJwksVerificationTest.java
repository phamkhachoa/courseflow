package edu.courseflow.commonlibrary.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import io.jsonwebtoken.Jwts;
import java.math.BigInteger;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPublicKey;
import java.time.Instant;
import java.util.Base64;
import java.util.Date;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class InternalJwtServiceJwksVerificationTest {

    @Test
    void verifiesRs256TokensWithRemoteJwksAndRefreshesWhenKidChanges() throws Exception {
        KeyPair first = keyPair();
        KeyPair rotated = keyPair();
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://token-converter/oauth/jwks"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(jwks("kid-1", first), MediaType.APPLICATION_JSON));
        server.expect(requestTo("http://token-converter/oauth/jwks"))
                .andExpect(method(HttpMethod.GET))
                .andRespond(withSuccess(jwks("kid-2", rotated), MediaType.APPLICATION_JSON));
        InternalJwtProperties properties = new InternalJwtProperties(
                "RS256",
                "",
                "",
                "",
                "jwks",
                "http://token-converter/oauth/jwks",
                300,
                "local",
                "",
                "",
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "course-service");
        InternalJwtService service = new InternalJwtService(properties, provider(builder));

        assertThat(service.verify(token("kid-1", first)).getSubject()).isEqualTo("service:course-service");
        assertThat(service.verify(token("kid-2", rotated)).getSubject()).isEqualTo("service:course-service");
        server.verify();
    }

    private String token(String kid, KeyPair pair) {
        Instant now = Instant.now();
        return Jwts.builder()
                .header()
                .keyId(kid)
                .and()
                .issuer("courseflow-token-converter")
                .subject("service:course-service")
                .claim("aud", "courseflow-services")
                .claim("token_use", "internal")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plusSeconds(180)))
                .signWith(pair.getPrivate())
                .compact();
    }

    private String jwks(String kid, KeyPair pair) {
        RSAPublicKey publicKey = (RSAPublicKey) pair.getPublic();
        return """
                {"keys":[{"kty":"RSA","use":"sig","alg":"RS256","kid":"%s","n":"%s","e":"%s"}]}
                """.formatted(kid, encode(publicKey.getModulus()), encode(publicKey.getPublicExponent()));
    }

    private String encode(BigInteger value) {
        byte[] bytes = value.toByteArray();
        if (bytes.length > 1 && bytes[0] == 0) {
            bytes = java.util.Arrays.copyOfRange(bytes, 1, bytes.length);
        }
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private KeyPair keyPair() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        return generator.generateKeyPair();
    }

    private ObjectProvider<RestClient.Builder> provider(RestClient.Builder builder) {
        return new ObjectProvider<>() {
            @Override
            public RestClient.Builder getObject(Object... args) {
                return builder;
            }

            @Override
            public RestClient.Builder getIfAvailable() {
                return builder;
            }

            @Override
            public RestClient.Builder getIfUnique() {
                return builder;
            }

            @Override
            public RestClient.Builder getObject() {
                return builder;
            }
        };
    }
}
