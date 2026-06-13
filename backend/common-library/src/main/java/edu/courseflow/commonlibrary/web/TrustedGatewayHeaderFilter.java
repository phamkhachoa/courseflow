package edu.courseflow.commonlibrary.web;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Defense-in-depth for gateway-propagated identity headers.
 *
 * <p>The API gateway is still the primary trust boundary: it strips client-supplied identity headers,
 * verifies JWTs, then injects {@code X-User-*}. This filter closes the direct-service access gap:
 * downstream services only accept propagated identity headers and {@code /internal/**} endpoints
 * when the request carries a valid short-lived internal JWT.
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

    private final InternalJwtService internalJwtService;

    public TrustedGatewayHeaderFilter(InternalJwtService internalJwtService) {
        this.internalJwtService = internalJwtService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        if (!requiresInternalJwt(request)) {
            filterChain.doFilter(request, response);
            return;
        }

        if (validInternalJwt(request)) {
            filterChain.doFilter(request, response);
            return;
        }

        deny(response);
    }

    private boolean hasIdentityHeaders(HttpServletRequest request) {
        return IDENTITY_HEADERS.stream().anyMatch(header -> request.getHeader(header) != null);
    }

    private boolean requiresInternalJwt(HttpServletRequest request) {
        return request.getRequestURI().startsWith("/internal/") || hasIdentityHeaders(request);
    }

    private boolean validInternalJwt(HttpServletRequest request) {
        String header = firstBearerHeader(request);
        if (header == null) {
            return false;
        }
        try {
            Claims claims = internalJwtService.verify(header);
            if (!"internal".equals(claims.get("token_use", String.class))) {
                return false;
            }
            return !hasIdentityHeaders(request) || identityClaimsMatchHeaders(claims, request);
        } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
            return false;
        }
    }

    private String firstBearerHeader(HttpServletRequest request) {
        String internal = request.getHeader(GatewayHeaders.INTERNAL_AUTHORIZATION);
        if (isBearer(internal)) {
            return internal;
        }
        String authorization = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (isBearer(authorization)) {
            return authorization;
        }
        return null;
    }

    private boolean isBearer(String header) {
        return header != null && header.regionMatches(true, 0, "Bearer ", 0, 7);
    }

    private boolean identityClaimsMatchHeaders(Claims claims, HttpServletRequest request) {
        String uid = claims.get("uid", String.class);
        String userIdHeader = request.getHeader(GatewayHeaders.USER_ID);
        if (uid == null || userIdHeader == null || !uid.equals(userIdHeader)) {
            return false;
        }
        String emailHeader = request.getHeader(GatewayHeaders.USER_EMAIL);
        String emailClaim = claims.get("email", String.class);
        return emailHeader == null || emailClaim == null || emailClaim.equals(emailHeader);
    }

    private void deny(HttpServletResponse response) throws IOException {
        response.setStatus(HttpStatus.UNAUTHORIZED.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"statusCode\":\"401 UNAUTHORIZED\",\"title\":\"Unauthorized\","
                + "\"detail\":\"Trusted gateway internal token is required\"}");
    }
}
