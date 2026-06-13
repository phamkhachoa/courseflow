package edu.courseflow.tokenconverter.service;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.util.Locale;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;

@Component
public class TokenConverterMetrics {

    private final MeterRegistry registry;

    public TokenConverterMetrics(MeterRegistry registry) {
        this.registry = registry;
    }

    private TokenConverterMetrics() {
        this.registry = null;
    }

    public static TokenConverterMetrics noop() {
        return new TokenConverterMetrics();
    }

    public void request(String grantType) {
        increment("courseflow.token_converter.requests", "grant_type", grantType(grantType));
    }

    public void success(String grantType, String actorType) {
        increment("courseflow.token_converter.success",
                "grant_type", grantType(grantType),
                "actor_type", tag(actorType, "unknown"));
    }

    public void failure(String grantType, String reason, String status) {
        increment("courseflow.token_converter.failure",
                "grant_type", grantType(grantType),
                "reason", tag(reason, "unknown"),
                "status", tag(status, "unknown"));
    }

    public void duration(String grantType, String outcome, long startedNanos) {
        if (registry == null) {
            return;
        }
        Timer.builder("courseflow.token_converter.duration")
                .tag("grant_type", grantType(grantType))
                .tag("outcome", tag(outcome, "unknown"))
                .register(registry)
                .record(System.nanoTime() - startedNanos, TimeUnit.NANOSECONDS);
    }

    public void jwks(String outcome) {
        increment("courseflow.token_converter.jwks.requests",
                "outcome", tag(outcome, "unknown"));
    }

    private void increment(String name, String... tags) {
        if (registry == null) {
            return;
        }
        io.micrometer.core.instrument.Counter.builder(name).tags(tags).register(registry).increment();
    }

    private String grantType(String grantType) {
        if (TokenExchangeService.TOKEN_EXCHANGE_GRANT.equals(grantType)) {
            return "token_exchange";
        }
        if (TokenExchangeService.CLIENT_CREDENTIALS_GRANT.equals(grantType)) {
            return "client_credentials";
        }
        if (TokenExchangeService.TRUSTED_USER_GRANT.equals(grantType)) {
            return "trusted_user";
        }
        if (grantType == null || grantType.isBlank()) {
            return "missing";
        }
        return "unsupported";
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
