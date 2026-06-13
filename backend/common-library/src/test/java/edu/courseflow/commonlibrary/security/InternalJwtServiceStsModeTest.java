package edu.courseflow.commonlibrary.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import java.security.KeyPairGenerator;
import java.security.PublicKey;
import java.util.Base64;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class InternalJwtServiceStsModeTest {

    private static final String STS_SECRET = "sts-client-secret-that-is-at-least-32-bytes";

    @Test
    void serviceTokenCanBeRequestedFromTokenConverter() throws Exception {
        RestClient.Builder builder = RestClient.builder();
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo("http://token-converter/oauth/token"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().string(containsString("grant_type=client_credentials")))
                .andExpect(content().string(containsString("client_id=course-service")))
                .andExpect(content().string(containsString("client_secret=" + STS_SECRET)))
                .andRespond(withSuccess("""
                        {"access_token":"sts-token","issued_token_type":"urn:ietf:params:oauth:token-type:access_token","token_type":"Bearer","expires_in":180,"scope":"internal:service"}
                        """, MediaType.APPLICATION_JSON));

        InternalJwtProperties properties = new InternalJwtProperties(
                "RS256",
                "",
                "",
                pem("PUBLIC KEY", publicKey()),
                "local",
                "",
                300,
                "sts",
                "http://token-converter",
                STS_SECRET,
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "course-service");
        InternalJwtService service = new InternalJwtService(properties, provider(builder));

        HttpHeaders headers = new HttpHeaders();
        service.applyServiceToken(headers);

        assertThat(headers.getFirst(GatewayHeaders.INTERNAL_AUTHORIZATION)).isEqualTo("Bearer sts-token");
        assertThat(headers.getFirst(HttpHeaders.AUTHORIZATION)).isEqualTo("Bearer sts-token");
        server.verify();
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

    private PublicKey publicKey() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        return generator.generateKeyPair().getPublic();
    }

    private String pem(String label, PublicKey key) {
        return "-----BEGIN " + label + "-----\n"
                + Base64.getMimeEncoder(64, "\n".getBytes()).encodeToString(key.getEncoded())
                + "\n-----END " + label + "-----";
    }
}
