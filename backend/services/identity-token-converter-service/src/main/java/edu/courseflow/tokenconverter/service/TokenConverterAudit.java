package edu.courseflow.tokenconverter.service;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class TokenConverterAudit {

    private static final Logger AUDIT_LOG = LoggerFactory.getLogger("courseflow.security.token_converter.audit");

    private final boolean enabled;

    public TokenConverterAudit() {
        this(true);
    }

    private TokenConverterAudit(boolean enabled) {
        this.enabled = enabled;
    }

    public static TokenConverterAudit noop() {
        return new TokenConverterAudit(false);
    }

    public void success(Event event) {
        write("success", event);
    }

    public void failure(Event event) {
        write("failure", event);
    }

    private void write(String outcome, Event event) {
        if (!enabled || event == null) {
            return;
        }
        AUDIT_LOG.info(
                "token_converter_audit outcome={} grant_type={} actor_type={} actor_id={} client_id={} audience={} scopes={} external_issuer={} external_subject={} status={} reason={}",
                outcome,
                safe(event.grantType()),
                safe(event.actorType()),
                safe(event.actorId()),
                safe(event.clientId()),
                safe(event.audience()),
                safe(String.join(" ", event.scopes())),
                safe(event.externalIssuer()),
                safe(event.externalSubject()),
                safe(event.status()),
                safe(event.reason()));
    }

    private String safe(String raw) {
        if (raw == null || raw.isBlank()) {
            return "-";
        }
        String normalized = raw.replaceAll("[\\r\\n\\t]+", "_").trim();
        return normalized.length() <= 200 ? normalized : normalized.substring(0, 200);
    }

    public record Event(
            String grantType,
            String actorType,
            String actorId,
            String clientId,
            String audience,
            List<String> scopes,
            String externalIssuer,
            String externalSubject,
            String status,
            String reason) {

        public Event {
            scopes = scopes == null ? List.of() : List.copyOf(scopes);
        }
    }
}
