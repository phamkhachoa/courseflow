package edu.courseflow.chat.security;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class ChatJwtVerifier {

    private static final List<String> ROLE_RANK =
            List.of("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA", "STUDENT");
    private static final String TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange";
    private static final String ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token";

    private final RestClient tokenConverter;
    private final InternalJwtService internalJwt;
    private final String audience;
    private final String clientId;
    private final String clientSecret;

    public ChatJwtVerifier(
            RestClient.Builder restClientBuilder,
            InternalJwtService internalJwt,
            @Value("${courseflow.chat.token-converter-uri:${TOKEN_CONVERTER_URI:http://identity-token-converter-service:8080}}")
            String tokenConverterUri,
            @Value("${courseflow.chat.internal-jwt-audience:${COURSEFLOW_INTERNAL_JWT_AUDIENCE:courseflow-services}}")
            String audience,
            @Value("${courseflow.chat.token-converter-client-id:${spring.application.name:chat-service}}")
            String clientId,
            @Value("${courseflow.chat.token-converter-client-secret:${COURSEFLOW_STS_CLIENT_SECRET:}}")
            String clientSecret) {
        this.tokenConverter = restClientBuilder.clone()
                .baseUrl(tokenConverterUri == null || tokenConverterUri.isBlank()
                        ? "http://identity-token-converter-service:8080"
                        : tokenConverterUri.trim())
                .build();
        this.internalJwt = internalJwt;
        this.audience = audience == null || audience.isBlank() ? "courseflow-services" : audience.trim();
        this.clientId = clientId == null || clientId.isBlank() ? "chat-service" : clientId.trim();
        this.clientSecret = clientSecret == null ? "" : clientSecret.trim();
    }

    public ChatPrincipal verify(String authHeader) {
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            throw new JwtException("Missing bearer token");
        }
        String externalToken = authHeader.substring(7).trim();
        if (externalToken.isBlank()) {
            throw new JwtException("Missing bearer token");
        }
        Claims claims = internalJwt.verify(exchangeForInternalToken(externalToken));
        if (!"internal".equals(claims.get("token_use", String.class))) {
            throw new JwtException("Wrong token_use for chat websocket");
        }
        Long userId = Long.valueOf(requireClaim(claims, "uid"));
        String email = claims.get("email", String.class);
        Set<String> roles = extractRoleCodes(claims);
        if (roles.isEmpty()) {
            throw new JwtException("Internal token carries no roles");
        }
        return new ChatPrincipal(
                userId,
                email,
                primaryRole(roles),
                roles,
                extractRoleAssignments(claims));
    }

    private String exchangeForInternalToken(String externalToken) {
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", TOKEN_EXCHANGE_GRANT);
        form.add("subject_token_type", ACCESS_TOKEN_TYPE);
        form.add("subject_token", externalToken);
        form.add("audience", audience);
        form.add("client_id", clientId);
        form.add("client_secret", clientSecret);
        try {
            TokenExchangeResponse response = tokenConverter.post()
                    .uri("/oauth/token")
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(form)
                    .retrieve()
                    .body(TokenExchangeResponse.class);
            if (response == null || response.access_token() == null || response.access_token().isBlank()) {
                throw new JwtException("Token converter returned an empty internal token");
            }
            return response.access_token();
        } catch (RestClientException ex) {
            throw new JwtException("Token converter rejected chat websocket token", ex);
        }
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
        Set<String> codes = new LinkedHashSet<>();
        Object rawRoles = claims.get("roles");
        if (rawRoles instanceof List<?> roles) {
            addRoleCodes(codes, roles);
        }
        Object rawAssignments = claims.get("role_assignments");
        if (rawAssignments instanceof List<?> assignments) {
            addRoleCodes(codes, assignments);
        }
        return codes;
    }

    @SuppressWarnings("unchecked")
    private void addRoleCodes(Set<String> codes, List<?> list) {
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
    }

    @SuppressWarnings("unchecked")
    private Set<CurrentUser.RoleAssignment> extractRoleAssignments(Claims claims) {
        Object rawAssignments = claims.get("role_assignments");
        if (!(rawAssignments instanceof List<?> assignments)) {
            return Set.of();
        }
        Set<CurrentUser.RoleAssignment> result = new LinkedHashSet<>();
        for (Object element : assignments) {
            if (!(element instanceof Map<?, ?> raw)) {
                continue;
            }
            Map<String, Object> assignment = (Map<String, Object>) raw;
            Object code = assignment.get("code");
            if (code == null || code.toString().isBlank()) {
                continue;
            }
            Object scopeType = assignment.get("scopeType");
            Object scopeId = assignment.get("scopeId");
            result.add(new CurrentUser.RoleAssignment(
                    code.toString(),
                    scopeType == null ? "PLATFORM" : scopeType.toString(),
                    scopeId == null ? null : scopeId.toString()));
        }
        return Set.copyOf(result);
    }

    private String primaryRole(Set<String> roleCodes) {
        return ROLE_RANK.stream()
                .filter(roleCodes::contains)
                .findFirst()
                .orElse(roleCodes.iterator().next());
    }

    private record TokenExchangeResponse(String access_token) {
    }
}
