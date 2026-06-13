package edu.courseflow.commonlibrary.web;

import static org.assertj.core.api.Assertions.assertThat;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import jakarta.servlet.ServletException;
import java.io.IOException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class TrustedGatewayHeaderFilterTest {

    private static final String SERVICE_TOKEN = "trusted-gateway-to-service-token";

    @Test
    void allowsRequestWithoutIdentityHeadersWhenTokenIsNotConfigured() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = new TrustedGatewayHeaderFilter("");
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/public/courses");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    @Test
    void rejectsIdentityHeadersWhenServiceTokenIsNotConfigured() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = new TrustedGatewayHeaderFilter("");
        MockHttpServletRequest request = requestWithIdentityHeaders();
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(response.getContentAsString()).contains("Trusted gateway service token is required");
    }

    @Test
    void rejectsIdentityHeadersWhenServiceTokenDoesNotMatch() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = new TrustedGatewayHeaderFilter(SERVICE_TOKEN);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.SERVICE_TOKEN, "wrong-token");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(401);
    }

    @Test
    void allowsIdentityHeadersWhenGatewayServiceTokenMatches() throws ServletException, IOException {
        TrustedGatewayHeaderFilter filter = new TrustedGatewayHeaderFilter(SERVICE_TOKEN);
        MockHttpServletRequest request = requestWithIdentityHeaders();
        request.addHeader(GatewayHeaders.SERVICE_TOKEN, SERVICE_TOKEN);
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(chain.getRequest()).isSameAs(request);
    }

    private MockHttpServletRequest requestWithIdentityHeaders() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/internal/courses");
        request.addHeader(GatewayHeaders.USER_ID, "42");
        request.addHeader(GatewayHeaders.USER_EMAIL, "learner@courseflow.local");
        request.addHeader(GatewayHeaders.USER_ROLE, "STUDENT");
        return request;
    }
}
