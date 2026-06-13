package edu.courseflow.usermanagement.service;

import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.server.ResponseStatusException;

@Component
public class HttpKeycloakAdminClient implements KeycloakAdminClient {

    private final RestClient client;
    private final KeycloakAdminProperties properties;
    private TokenCache tokenCache;

    public HttpKeycloakAdminClient(RestClient.Builder restClientBuilder, KeycloakAdminProperties properties) {
        this.properties = properties;
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(properties.timeoutMs());
        requestFactory.setReadTimeout(properties.timeoutMs());
        this.client = restClientBuilder.clone()
                .baseUrl(properties.baseUrl())
                .requestFactory(requestFactory)
                .build();
    }

    @Override
    public String issuer() {
        return properties.issuer();
    }

    @Override
    public KeycloakUser createUser(String email, String fullName) {
        Map<String, Object> user = new LinkedHashMap<>();
        NameParts name = splitName(fullName);
        user.put("username", email);
        user.put("email", email);
        user.put("enabled", true);
        user.put("emailVerified", false);
        user.put("firstName", name.firstName());
        user.put("lastName", name.lastName());
        user.put("requiredActions", List.of("VERIFY_EMAIL", "UPDATE_PASSWORD"));
        try {
            var response = client.post()
                    .uri("/admin/realms/{realm}/users", properties.realm())
                    .headers(this::authorize)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(user)
                    .retrieve()
                    .toBodilessEntity();
            URI location = response.getHeaders().getLocation();
            String id = extractUserId(location);
            return getUser(id);
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak user creation failed");
        }
    }

    @Override
    public void setCourseFlowUserId(String keycloakUserId, String courseflowUserId) {
        Map<String, Object> user = getUserRepresentation(keycloakUserId);
        Map<String, List<String>> attributes = attributes(user.get("attributes"));
        attributes.put("courseflow_user_id", List.of(courseflowUserId));
        user.put("attributes", attributes);
        updateUser(keycloakUserId, user);
    }

    @Override
    public void sendSetupEmail(String keycloakUserId) {
        try {
            client.put()
                    .uri(builder -> {
                        var path = builder.path("/admin/realms/{realm}/users/{userId}/execute-actions-email")
                                .queryParam("client_id", properties.setupEmailClientId())
                                .queryParam("lifespan", properties.setupEmailLifespanSeconds());
                        if (!properties.setupEmailRedirectUri().isBlank()) {
                            path.queryParam("redirect_uri", properties.setupEmailRedirectUri());
                        }
                        return path.build(properties.realm(), keycloakUserId);
                    })
                    .headers(this::authorize)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(List.of("VERIFY_EMAIL", "UPDATE_PASSWORD"))
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak setup email failed");
        }
    }

    @Override
    public KeycloakUser getUser(String keycloakUserId) {
        return toUser(getUserRepresentation(keycloakUserId));
    }

    @Override
    public void disableUser(String keycloakUserId) {
        Map<String, Object> user = getUserRepresentation(keycloakUserId);
        user.put("enabled", false);
        updateUser(keycloakUserId, user);
    }

    @Override
    public void logoutUser(String keycloakUserId) {
        try {
            client.post()
                    .uri("/admin/realms/{realm}/users/{userId}/logout", properties.realm(), keycloakUserId)
                    .headers(this::authorize)
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak user logout failed");
        }
    }

    @Override
    public void deleteUser(String keycloakUserId) {
        try {
            client.delete()
                    .uri("/admin/realms/{realm}/users/{userId}", properties.realm(), keycloakUserId)
                    .headers(this::authorize)
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak user cleanup failed");
        }
    }

    private Map<String, Object> getUserRepresentation(String keycloakUserId) {
        try {
            return client.get()
                    .uri("/admin/realms/{realm}/users/{userId}", properties.realm(), keycloakUserId)
                    .headers(this::authorize)
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {
                    });
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak user lookup failed");
        }
    }

    private void updateUser(String keycloakUserId, Map<String, Object> user) {
        try {
            client.put()
                    .uri("/admin/realms/{realm}/users/{userId}", properties.realm(), keycloakUserId)
                    .headers(this::authorize)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(user)
                    .retrieve()
                    .toBodilessEntity();
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak user update failed");
        }
    }

    private void authorize(HttpHeaders headers) {
        headers.setBearerAuth(adminToken());
    }

    private synchronized String adminToken() {
        if (tokenCache != null && tokenCache.expiresAt().isAfter(Instant.now().plusSeconds(30))) {
            return tokenCache.accessToken();
        }
        if (properties.clientSecret().isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "KEYCLOAK_ADMIN_CLIENT_SECRET is required for user lifecycle operations");
        }
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "client_credentials");
        form.add("client_id", properties.clientId());
        form.add("client_secret", properties.clientSecret());
        try {
            TokenResponse token = client.post()
                    .uri("/realms/{realm}/protocol/openid-connect/token", properties.realm())
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(form)
                    .retrieve()
                    .body(TokenResponse.class);
            if (token == null || token.access_token() == null || token.access_token().isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Keycloak returned no admin token");
            }
            long ttl = Math.max(30, token.expires_in());
            tokenCache = new TokenCache(token.access_token(), Instant.now().plusSeconds(ttl));
            return tokenCache.accessToken();
        } catch (RestClientResponseException ex) {
            throw mapKeycloakException(ex, "Keycloak admin token request failed");
        }
    }

    private ResponseStatusException mapKeycloakException(RestClientResponseException ex, String message) {
        HttpStatus status = HttpStatus.resolve(ex.getStatusCode().value());
        if (status == null) {
            status = HttpStatus.BAD_GATEWAY;
        }
        if (status.is5xxServerError()) {
            status = HttpStatus.BAD_GATEWAY;
        }
        return new ResponseStatusException(status, message);
    }

    private String extractUserId(URI location) {
        if (location == null || location.getPath() == null || location.getPath().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Keycloak did not return created user id");
        }
        String path = location.getPath();
        int slash = path.lastIndexOf('/');
        return slash < 0 ? path : path.substring(slash + 1);
    }

    @SuppressWarnings("unchecked")
    private Map<String, List<String>> attributes(Object raw) {
        Map<String, List<String>> attributes = new LinkedHashMap<>();
        if (raw instanceof Map<?, ?> map) {
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (entry.getKey() == null) {
                    continue;
                }
                Object value = entry.getValue();
                if (value instanceof List<?> list) {
                    attributes.put(entry.getKey().toString(), list.stream()
                            .map(String::valueOf)
                            .toList());
                } else if (value != null) {
                    attributes.put(entry.getKey().toString(), List.of(value.toString()));
                }
            }
        }
        return attributes;
    }

    @SuppressWarnings("unchecked")
    private KeycloakUser toUser(Map<String, Object> raw) {
        return new KeycloakUser(
                string(raw.get("id")),
                string(raw.get("username")),
                string(raw.get("email")),
                string(raw.get("firstName")),
                string(raw.get("lastName")),
                booleanValue(raw.get("enabled")),
                booleanValue(raw.get("emailVerified")),
                raw.get("requiredActions") instanceof List<?> actions
                        ? actions.stream().map(String::valueOf).toList()
                        : List.of(),
                attributes(raw.get("attributes")));
    }

    private boolean booleanValue(Object value) {
        return value instanceof Boolean bool ? bool : Boolean.parseBoolean(String.valueOf(value));
    }

    private String string(Object value) {
        return value == null ? null : value.toString();
    }

    private NameParts splitName(String fullName) {
        String trimmed = fullName == null ? "" : fullName.trim();
        if (trimmed.isBlank()) {
            return new NameParts("", "");
        }
        List<String> parts = new ArrayList<>(List.of(trimmed.split("\\s+")));
        if (parts.size() == 1) {
            return new NameParts(parts.get(0), "");
        }
        String lastName = parts.remove(parts.size() - 1);
        return new NameParts(String.join(" ", parts), lastName);
    }

    private record TokenResponse(String access_token, long expires_in) {
    }

    private record TokenCache(String accessToken, Instant expiresAt) {
    }

    private record NameParts(String firstName, String lastName) {
    }
}
