package edu.courseflow.gateway;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
class TokenConverterProperties {

    enum Mode {
        REQUIRED
    }

    private final String uri;
    private final Mode mode;
    private final String audience;
    private final long timeoutMs;
    private final String clientId;
    private final String clientSecret;

    TokenConverterProperties(
            @Value("${courseflow.security.token-converter.uri:http://identity-token-converter-service:8080}") String uri,
            @Value("${courseflow.security.token-converter.mode:required}") String mode,
            @Value("${courseflow.security.token-converter.audience:courseflow-services}") String audience,
            @Value("${courseflow.security.token-converter.timeout-ms:800}") long timeoutMs,
            @Value("${courseflow.security.token-converter.client-id:${spring.application.name:api-gateway}}")
            String clientId,
            @Value("${courseflow.security.token-converter.client-secret:${COURSEFLOW_STS_CLIENT_SECRET:}}")
            String clientSecret) {
        this.uri = trimToDefault(uri, "http://identity-token-converter-service:8080");
        this.mode = parseMode(mode);
        this.audience = trimToDefault(audience, "courseflow-services");
        this.timeoutMs = Math.max(100, Math.min(timeoutMs, 5000));
        this.clientId = trimToDefault(clientId, "api-gateway");
        this.clientSecret = clientSecret == null ? "" : clientSecret.trim();
    }

    String uri() {
        return uri;
    }

    Mode mode() {
        return mode;
    }

    String audience() {
        return audience;
    }

    long timeoutMs() {
        return timeoutMs;
    }

    String clientId() {
        return clientId;
    }

    String clientSecret() {
        return clientSecret;
    }

    private Mode parseMode(String raw) {
        if (raw == null || raw.isBlank()) {
            return Mode.REQUIRED;
        }
        return switch (raw.trim().toUpperCase()) {
            case "REQUIRED" -> Mode.REQUIRED;
            default -> throw new IllegalStateException(
                    "Unsupported token converter mode: " + raw + ". Legacy token converter modes have been removed.");
        };
    }

    private String trimToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }
}
