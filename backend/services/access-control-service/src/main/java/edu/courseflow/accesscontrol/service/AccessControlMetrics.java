package edu.courseflow.accesscontrol.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.Locale;
import org.springframework.stereotype.Component;

@Component
public class AccessControlMetrics {

    private static final String AUTHZ_CHECKS = "courseflow.access_control.authz.checks";

    private final MeterRegistry registry;

    public AccessControlMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    private AccessControlMetrics() {
        this.registry = null;
    }

    public static AccessControlMetrics noop() {
        return new AccessControlMetrics();
    }

    public void authzCheck(boolean allowed, String reason, String scopeType) {
        if (registry == null) {
            return;
        }
        Counter.builder(AUTHZ_CHECKS)
                .tag("result", allowed ? "allowed" : "denied")
                .tag("reason", tag(reason, "unknown"))
                .tag("scope_type", tag(scopeType, "platform"))
                .register(registry)
                .increment();
    }

    private String tag(String value, String fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        return value.trim()
                .toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9_:-]+", "_");
    }
}
