package edu.courseflow.gateway;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExternalTokenProperties {

    private final String oidcIssuer;
    private final String jwkSetUri;
    private final Set<String> audiences;

    public ExternalTokenProperties(
            @Value("${courseflow.security.external-token.issuer:${KEYCLOAK_ISSUER_URI:}}") String oidcIssuer,
            @Value("${courseflow.security.external-token.jwk-set-uri:${KEYCLOAK_JWK_SET_URI:}}") String jwkSetUri,
            @Value("${courseflow.security.external-token.audiences:${KEYCLOAK_AUDIENCE:courseflow-api}}")
            String audiences) {
        this.oidcIssuer = trimToDefault(oidcIssuer, "");
        this.jwkSetUri = trimToDefault(jwkSetUri, defaultKeycloakJwkSetUri(this.oidcIssuer));
        this.audiences = parseAudiences(audiences, "courseflow-api");
        if (this.oidcIssuer.isBlank()) {
            throw new IllegalStateException("KEYCLOAK_ISSUER_URI is required");
        }
    }

    public String oidcIssuer() {
        return oidcIssuer;
    }

    public String jwkSetUri() {
        return jwkSetUri;
    }

    public Set<String> audiences() {
        return audiences;
    }

    private String trimToDefault(String raw, String fallback) {
        return raw == null || raw.isBlank() ? fallback : raw.trim();
    }

    private Set<String> parseAudiences(String raw, String fallback) {
        Set<String> values = new LinkedHashSet<>();
        if (raw != null && !raw.isBlank()) {
            Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(values::add);
        }
        if (values.isEmpty()) {
            values.add(fallback);
        }
        return Set.copyOf(values);
    }

    private String defaultKeycloakJwkSetUri(String issuer) {
        if (issuer == null || issuer.isBlank()) {
            return "";
        }
        String normalized = issuer.endsWith("/") ? issuer.substring(0, issuer.length() - 1) : issuer;
        return normalized + "/protocol/openid-connect/certs";
    }
}
