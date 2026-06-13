package edu.courseflow.commonlibrary.security;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import java.security.KeyPairGenerator;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;

class InternalJwtServiceRs256Test {

    @Test
    void serviceTokenCanBeSignedAndVerifiedWithRs256() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        var pair = generator.generateKeyPair();
        InternalJwtService service = new InternalJwtService(new InternalJwtProperties(
                "RS256",
                "",
                pem("PRIVATE KEY", pair.getPrivate()),
                pem("PUBLIC KEY", pair.getPublic()),
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "test-service"));

        HttpHeaders headers = new HttpHeaders();
        service.applyServiceToken(headers);

        var claims = service.verify(headers.getFirst(GatewayHeaders.INTERNAL_AUTHORIZATION));
        assertThat(claims.getIssuer()).isEqualTo("courseflow-token-converter");
        assertThat(claims.getSubject()).isEqualTo("service:test-service");
        assertThat(claims.get("token_use")).isEqualTo("internal");
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
