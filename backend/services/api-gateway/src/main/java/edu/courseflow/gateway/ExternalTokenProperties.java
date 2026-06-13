package edu.courseflow.gateway;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class ExternalTokenProperties {

    private static final int MIN_SECRET_BYTES = 32;

    private final Mode mode;
    private final String legacySecret;
    private final String legacyIssuer;
    private final String oidcIssuer;
    private final String jwkSetUri;
    private final Set<String> audiences;

    public ExternalTokenProperties(
            @Value("${courseflow.security.external-token.mode:${EXTERNAL_TOKEN_MODE:oidc}}") String mode,
            @Value("${courseflow.security.jwt.secret:}") String legacySecret,
            @Value("${courseflow.security.jwt.issuer:${JWT_ISSUER:}}") String legacyIssuer,
            @Value("${courseflow.security.external-token.issuer:${KEYCLOAK_ISSUER_URI:}}") String oidcIssuer,
            @Value("${courseflow.security.external-token.jwk-set-uri:${KEYCLOAK_JWK_SET_URI:}}") String jwkSetUri,
            @Value("${courseflow.security.external-token.audiences:${KEYCLOAK_AUDIENCE:courseflow-api}}")
            String audiences) {
        this.mode = parseMode(mode);
        this.legacySecret = this.mode == Mode.LEGACY ? validateLegacySecret(legacySecret) : trimToDefault(legacySecret, "");
        this.legacyIssuer = trimToDefault(legacyIssuer, "");
        this.oidcIssuer = trimToDefault(oidcIssuer, this.legacyIssuer);
        this.jwkSetUri = trimToDefault(jwkSetUri, defaultKeycloakJwkSetUri(this.oidcIssuer));
        this.audiences = parseAudiences(audiences, "courseflow-api");
        if (this.mode == Mode.OIDC && this.oidcIssuer.isBlank()) {
            throw new IllegalStateException("KEYCLOAK_ISSUER_URI is required when EXTERNAL_TOKEN_MODE=oidc");
        }
    }

    public boolean legacyMode() {
        return mode == Mode.LEGACY;
    }

    public SecretKey legacySecretKey() {
        return Keys.hmacShaKeyFor(legacySecret.getBytes(StandardCharsets.UTF_8));
    }

    public String legacyIssuer() {
        return legacyIssuer;
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

    private String validateLegacySecret(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(
                    "COURSEFLOW_JWT_SECRET is not set. The gateway refuses to start without a legacy JWT signing secret "
                            + "unless EXTERNAL_TOKEN_MODE=oidc.");
        }
        if (JwtSecretProperties.FORBIDDEN_DEV_SECRET.equals(value)) {
            throw new IllegalStateException("COURSEFLOW_JWT_SECRET is still set to the insecure development value.");
        }
        if (value.getBytes(StandardCharsets.UTF_8).length < MIN_SECRET_BYTES) {
            throw new IllegalStateException("COURSEFLOW_JWT_SECRET is too short; HS256 requires at least "
                    + MIN_SECRET_BYTES + " bytes.");
        }
        return value;
    }

    private Mode parseMode(String raw) {
        if ("legacy".equalsIgnoreCase(raw == null ? "" : raw.trim())) {
            return Mode.LEGACY;
        }
        if (raw == null || raw.isBlank()
                || "oidc".equalsIgnoreCase(raw.trim()) || "keycloak".equalsIgnoreCase(raw.trim())) {
            return Mode.OIDC;
        }
        throw new IllegalStateException("Unsupported external token mode: " + raw);
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

    private enum Mode {
        LEGACY,
        OIDC
    }
}
