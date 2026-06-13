package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Defense-in-depth for gateway-propagated identity headers.
 *
 * <p>The API gateway is still the primary trust boundary: it strips client-supplied identity headers,
 * verifies JWTs, then injects {@code X-User-*}. This filter closes the direct-service access gap by
 * requiring the shared service token whenever a downstream service receives any identity header.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class TrustedGatewayHeaderFilter extends OncePerRequestFilter {

    private static final List<String> IDENTITY_HEADERS = List.of(
            GatewayHeaders.USER_ID,
            GatewayHeaders.USER_ROLE,
            GatewayHeaders.USER_ROLES,
            GatewayHeaders.USER_ROLE_SCOPES,
            GatewayHeaders.USER_EMAIL);

    private final String serviceToken;

    public TrustedGatewayHeaderFilter(@Value("${courseflow.security.service-token:}") String serviceToken) {
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if (!hasIdentityHeaders(request)) {
            filterChain.doFilter(request, response);
            return;
        }

        String presented = request.getHeader(GatewayHeaders.SERVICE_TOKEN);
        if (serviceToken.isBlank() || presented == null || !constantTimeEquals(serviceToken, presented.trim())) {
            deny(response);
            return;
        }

        filterChain.doFilter(request, response);
    }

    private boolean hasIdentityHeaders(HttpServletRequest request) {
        return IDENTITY_HEADERS.stream().anyMatch(header -> request.getHeader(header) != null);
    }

    private boolean constantTimeEquals(String expected, String actual) {
        byte[] left = expected.getBytes(StandardCharsets.UTF_8);
        byte[] right = actual.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(left, right);
    }

    private void deny(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"statusCode\":\"401 UNAUTHORIZED\",\"title\":\"Unauthorized\","
                + "\"detail\":\"Trusted gateway service token is required\"}");
    }
}
