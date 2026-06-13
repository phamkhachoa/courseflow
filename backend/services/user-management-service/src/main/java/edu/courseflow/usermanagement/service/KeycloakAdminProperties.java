package edu.courseflow.usermanagement.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class KeycloakAdminProperties {

    private final String baseUrl;
    private final String realm;
    private final String clientId;
    private final String clientSecret;
    private final String setupEmailClientId;
    private final String setupEmailRedirectUri;
    private final int setupEmailLifespanSeconds;
    private final int timeoutMs;

    public KeycloakAdminProperties(
            @Value("${courseflow.user-management.keycloak.base-url:${KEYCLOAK_BASE_URL:http://localhost:18080}}")
            String baseUrl,
            @Value("${courseflow.user-management.keycloak.realm:${KEYCLOAK_REALM:courseflow}}")
            String realm,
            @Value("${courseflow.user-management.keycloak.admin-client-id:${KEYCLOAK_ADMIN_CLIENT_ID:keycloak-user-lifecycle}}")
            String clientId,
            @Value("${courseflow.user-management.keycloak.admin-client-secret:${KEYCLOAK_ADMIN_CLIENT_SECRET:}}")
            String clientSecret,
            @Value("${courseflow.user-management.keycloak.setup-email-client-id:${KEYCLOAK_SETUP_EMAIL_CLIENT_ID:courseflow-admin-web}}")
            String setupEmailClientId,
            @Value("${courseflow.user-management.keycloak.setup-email-redirect-uri:${KEYCLOAK_SETUP_EMAIL_REDIRECT_URI:}}")
            String setupEmailRedirectUri,
            @Value("${courseflow.user-management.keycloak.setup-email-lifespan-seconds:${KEYCLOAK_SETUP_EMAIL_LIFESPAN_SECONDS:43200}}")
            int setupEmailLifespanSeconds,
            @Value("${courseflow.user-management.keycloak.timeout-ms:${KEYCLOAK_ADMIN_TIMEOUT_MS:3000}}")
            int timeoutMs) {
        this.baseUrl = trimTrailingSlash(baseUrl);
        this.realm = trimToDefault(realm, "courseflow");
        this.clientId = trimToDefault(clientId, "keycloak-user-lifecycle");
        this.clientSecret = clientSecret == null ? "" : clientSecret.trim();
        this.setupEmailClientId = trimToDefault(setupEmailClientId, "courseflow-admin-web");
        this.setupEmailRedirectUri = setupEmailRedirectUri == null ? "" : setupEmailRedirectUri.trim();
        this.setupEmailLifespanSeconds = Math.max(300, Math.min(setupEmailLifespanSeconds, 604800));
        this.timeoutMs = Math.max(250, Math.min(timeoutMs, 10000));
    }

    public String baseUrl() {
        return baseUrl;
    }

    public String realm() {
        return realm;
    }

    public String issuer() {
        return baseUrl + "/realms/" + realm;
    }

    public String clientId() {
        return clientId;
    }

    public String clientSecret() {
        return clientSecret;
    }

    public String setupEmailClientId() {
        return setupEmailClientId;
    }

    public String setupEmailRedirectUri() {
        return setupEmailRedirectUri;
    }

    public int setupEmailLifespanSeconds() {
        return setupEmailLifespanSeconds;
    }

    public int timeoutMs() {
        return timeoutMs;
    }

    private String trimTrailingSlash(String raw) {
        String value = trimToDefault(raw, "http://localhost:18080");
        while (value.endsWith("/")) {
            value = value.substring(0, value.length() - 1);
        }
        return value;
    }

    private String trimToDefault(String raw, String fallback) {
        return raw == null || raw.isBlank() ? fallback : raw.trim();
    }
}
