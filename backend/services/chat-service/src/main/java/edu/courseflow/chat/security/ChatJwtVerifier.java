package edu.courseflow.chat.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ChatJwtVerifier {

    private static final List<String> ROLE_RANK =
            List.of("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA", "STUDENT");

    private final SecretKey secretKey;
    private final String issuer;

    public ChatJwtVerifier(@Value("${courseflow.security.jwt.secret:}") String secret,
                           @Value("${courseflow.security.jwt.issuer:courseflow-identity}") String issuer) {
        String normalized = secret == null ? "" : secret.trim();
        if (normalized.length() < 32) {
            throw new IllegalStateException("COURSEFLOW_JWT_SECRET must be configured and at least 32 characters");
        }
        this.secretKey = Keys.hmacShaKeyFor(normalized.getBytes(StandardCharsets.UTF_8));
        this.issuer = issuer;
    }

    public ChatPrincipal verify(String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            throw new JwtException("Missing bearer token");
        }
        Claims claims = Jwts.parser()
                .verifyWith(secretKey)
                .requireIssuer(issuer)
                .build()
                .parseSignedClaims(authHeader.substring(7))
                .getPayload();

        Long userId = Long.valueOf(requireClaim(claims, "uid"));
        String email = claims.getSubject();
        if (email == null || email.isBlank()) {
            throw new JwtException("Token subject is missing");
        }
        Set<String> roles = extractRoleCodes(claims);
        if (roles.isEmpty()) {
            throw new JwtException("Token carries no roles");
        }
        return new ChatPrincipal(userId, email, primaryRole(roles), roles);
    }

    private String requireClaim(Claims claims, String name) {
        Object value = claims.get(name);
        if (value == null || value.toString().isBlank()) {
            throw new JwtException("Missing JWT claim: " + name);
        }
        return value.toString();
    }

    @SuppressWarnings("unchecked")
    private Set<String> extractRoleCodes(Claims claims) {
        Object raw = claims.get("roles");
        if (!(raw instanceof List<?> list)) {
            return Set.of();
        }
        Set<String> codes = new LinkedHashSet<>();
        for (Object element : list) {
            if (element instanceof Map<?, ?> map) {
                Object code = ((Map<String, Object>) map).get("code");
                if (code != null && !code.toString().isBlank()) {
                    codes.add(code.toString());
                }
            } else if (element != null && !element.toString().isBlank()) {
                codes.add(element.toString());
            }
        }
        return codes;
    }

    private String primaryRole(Set<String> roleCodes) {
        return ROLE_RANK.stream()
                .filter(roleCodes::contains)
                .findFirst()
                .orElse(roleCodes.iterator().next());
    }
}
