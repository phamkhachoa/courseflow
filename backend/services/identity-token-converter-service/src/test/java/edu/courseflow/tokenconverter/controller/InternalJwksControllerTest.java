package edu.courseflow.tokenconverter.controller;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import edu.courseflow.tokenconverter.service.TokenConverterMetrics;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class InternalJwksControllerTest {

    @Test
    void exposesRs256PublicKeyAsJwks() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        var pair = generator.generateKeyPair();
        TokenConverterProperties properties = new TokenConverterProperties(
                "https://sso.courseflow.example.com/realms/courseflow",
                "https://sso.courseflow.example.com/realms/courseflow/protocol/openid-connect/certs",
                "courseflow-api",
                "RS256",
                "",
                pem("PRIVATE KEY", pair.getPrivate()),
                pem("PUBLIC KEY", pair.getPublic()),
                "courseflow-token-converter",
                "courseflow-services",
                "courseflow-services",
                "",
                "api-gateway=sts-client-secret-that-is-at-least-32-bytes",
                "api-gateway",
                "internal:service,internal:user",
                "api-gateway=internal:service,internal:user",
                180,
                30);

        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        Map<String, Object> jwks = new InternalJwksController(properties, new TokenConverterMetrics(registry)).jwks();

        List<?> keys = (List<?>) jwks.get("keys");
        assertThat(keys).hasSize(1);
        Map<?, ?> key = (Map<?, ?>) keys.get(0);
        assertThat(key.get("kty")).isEqualTo("RSA");
        assertThat(key.get("alg")).isEqualTo("RS256");
        assertThat(key.get("kid")).isEqualTo(properties.internalJwtKeyId());
        assertThat(key.get("n")).isNotNull();
        assertThat(key.get("e")).isNotNull();
        assertThat(registry.find("courseflow.token_converter.jwks.requests")
                .tag("outcome", "success")
                .counter()
                .count()).isEqualTo(1.0);
    }

    private String pem(String label, PrivateKey key) {
        return pem(label, key.getEncoded());
    }

    private String pem(String label, PublicKey key) {
        return pem(label, key.getEncoded());
    }

    private String pem(String label, byte[] encoded) {
        return "-----BEGIN " + label + "-----\n"
                + Base64.getMimeEncoder(64, "\n".getBytes()).encodeToString(encoded)
                + "\n-----END " + label + "-----";
    }
}
