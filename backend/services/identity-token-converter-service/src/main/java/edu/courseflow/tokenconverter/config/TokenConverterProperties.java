package edu.courseflow.tokenconverter.config;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class TokenConverterProperties {

    private static final int MIN_SECRET_BYTES = 32;

    private final String externalJwtSecret;
    private final String externalJwtIssuer;
    private final String internalJwtSecret;
    private final String internalJwtIssuer;
    private final String defaultAudience;
    private final Set<String> allowedAudiences;
    private final long ttlSeconds;
    private final long clockSkewSeconds;

    public TokenConverterProperties(
            @Value("${courseflow.security.external-jwt.secret:}") String externalJwtSecret,
            @Value("${courseflow.security.external-jwt.issuer:courseflow-identity}") String externalJwtIssuer,
            @Value("${courseflow.security.internal-jwt.secret:}") String internalJwtSecret,
            @Value("${courseflow.security.internal-jwt.issuer:courseflow-token-converter}") String internalJwtIssuer,
            @Value("${courseflow.security.internal-jwt.audience:courseflow-services}") String defaultAudience,
            @Value("${courseflow.security.internal-jwt.allowed-audiences:courseflow-services}")
            String allowedAudiences,
            @Value("${courseflow.security.internal-jwt.ttl-seconds:180}") long ttlSeconds,
            @Value("${courseflow.security.internal-jwt.clock-skew-seconds:30}") long clockSkewSeconds) {
        this.externalJwtSecret = validateSecret(externalJwtSecret, "COURSEFLOW_JWT_SECRET");
        this.externalJwtIssuer = trimToDefault(externalJwtIssuer, "courseflow-identity");
        this.internalJwtSecret = validateSecret(internalJwtSecret, "COURSEFLOW_INTERNAL_JWT_SECRET");
        this.internalJwtIssuer = trimToDefault(internalJwtIssuer, "courseflow-token-converter");
        this.defaultAudience = trimToDefault(defaultAudience, "courseflow-services");
        this.allowedAudiences = parseAudiences(allowedAudiences, this.defaultAudience);
        this.ttlSeconds = Math.max(30, Math.min(ttlSeconds, 900));
        this.clockSkewSeconds = Math.max(0, Math.min(clockSkewSeconds, 120));
    }

    public SecretKey externalJwtKey() {
        return Keys.hmacShaKeyFor(externalJwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    public String externalJwtIssuer() {
        return externalJwtIssuer;
    }

    public SecretKey internalJwtKey() {
        return Keys.hmacShaKeyFor(internalJwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    public String internalJwtIssuer() {
        return internalJwtIssuer;
    }

    public String defaultAudience() {
        return defaultAudience;
    }

    public Set<String> allowedAudiences() {
        return allowedAudiences;
    }

    public long ttlSeconds() {
        return ttlSeconds;
    }

    public long clockSkewSeconds() {
        return clockSkewSeconds;
    }

    private String requireNonBlank(String value, String envName) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(envName + " is required for identity-token-converter-service");
        }
        return value.trim();
    }

    private String validateSecret(String value, String envName) {
        String secret = requireNonBlank(value, envName);
        if (secret.getBytes(StandardCharsets.UTF_8).length < MIN_SECRET_BYTES) {
            throw new IllegalStateException(envName + " must be at least " + MIN_SECRET_BYTES + " bytes");
        }
        return secret;
    }

    private String trimToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private Set<String> parseAudiences(String raw, String fallback) {
        Set<String> audiences = new LinkedHashSet<>();
        if (raw != null && !raw.isBlank()) {
            Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(audiences::add);
        }
        if (audiences.isEmpty()) {
            audiences.add(fallback);
        }
        return Set.copyOf(audiences);
    }
}
