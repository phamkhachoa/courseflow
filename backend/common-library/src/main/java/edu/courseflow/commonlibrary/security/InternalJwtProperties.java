package edu.courseflow.commonlibrary.security;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class InternalJwtProperties {

    private static final int MIN_SECRET_BYTES = 32;

    private final String secret;
    private final String issuer;
    private final Set<String> audiences;
    private final long ttlSeconds;
    private final long clockSkewSeconds;
    private final String serviceName;

    public InternalJwtProperties(
            @Value("${courseflow.security.internal-jwt.secret:${COURSEFLOW_INTERNAL_JWT_SECRET:}}") String secret,
            @Value("${courseflow.security.internal-jwt.issuer:${COURSEFLOW_INTERNAL_JWT_ISSUER:courseflow-token-converter}}")
            String issuer,
            @Value("${courseflow.security.internal-jwt.audience:${COURSEFLOW_INTERNAL_JWT_AUDIENCE:courseflow-services}}")
            String audience,
            @Value("${courseflow.security.internal-jwt.ttl-seconds:${COURSEFLOW_INTERNAL_JWT_TTL_SECONDS:180}}")
            long ttlSeconds,
            @Value("${courseflow.security.internal-jwt.clock-skew-seconds:${COURSEFLOW_INTERNAL_JWT_CLOCK_SKEW_SECONDS:30}}")
            long clockSkewSeconds,
            @Value("${spring.application.name:courseflow-service}") String serviceName) {
        this.secret = secret == null ? "" : secret.trim();
        this.issuer = issuer == null || issuer.isBlank() ? "courseflow-token-converter" : issuer.trim();
        this.audiences = parseAudiences(audience);
        this.ttlSeconds = Math.max(30, Math.min(ttlSeconds, 900));
        this.clockSkewSeconds = Math.max(0, Math.min(clockSkewSeconds, 120));
        this.serviceName = serviceName == null || serviceName.isBlank() ? "courseflow-service" : serviceName.trim();
    }

    public boolean configured() {
        return secret.getBytes(StandardCharsets.UTF_8).length >= MIN_SECRET_BYTES;
    }

    public SecretKey signingKey() {
        if (!configured()) {
            throw new IllegalStateException("COURSEFLOW_INTERNAL_JWT_SECRET must be at least "
                    + MIN_SECRET_BYTES + " bytes");
        }
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String issuer() {
        return issuer;
    }

    public Set<String> audiences() {
        return audiences;
    }

    public String primaryAudience() {
        return audiences.iterator().next();
    }

    public long ttlSeconds() {
        return ttlSeconds;
    }

    public long clockSkewSeconds() {
        return clockSkewSeconds;
    }

    public String serviceName() {
        return serviceName;
    }

    private Set<String> parseAudiences(String raw) {
        Set<String> parsed = new LinkedHashSet<>();
        if (raw != null && !raw.isBlank()) {
            Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(parsed::add);
        }
        if (parsed.isEmpty()) {
            parsed.add("courseflow-services");
        }
        return Set.copyOf(parsed);
    }
}
