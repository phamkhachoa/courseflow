package edu.courseflow.tokenconverter.config;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class AccessControlProperties {

    private final String uri;
    private final String mode;
    private final Duration timeout;

    public AccessControlProperties(
            @Value("${courseflow.security.access-control.uri:${ACCESS_CONTROL_SERVICE_URI:http://access-control-service:8080}}")
            String uri,
            @Value("${courseflow.security.access-control.mode:${ACCESS_CONTROL_RESOLUTION_MODE:required}}")
            String mode,
            @Value("${courseflow.security.access-control.timeout-ms:${ACCESS_CONTROL_TIMEOUT_MS:800}}")
            long timeoutMs) {
        this.uri = uri == null ? "" : uri.trim();
        this.mode = mode == null || mode.isBlank() ? "required" : mode.trim().toLowerCase();
        this.timeout = Duration.ofMillis(Math.max(100, Math.min(timeoutMs, 5000)));
    }

    public String uri() {
        return uri;
    }

    public boolean enabled() {
        return !"disabled".equals(mode) && !uri.isBlank();
    }

    public boolean required() {
        return "required".equals(mode);
    }

    public Duration timeout() {
        return timeout;
    }
}
