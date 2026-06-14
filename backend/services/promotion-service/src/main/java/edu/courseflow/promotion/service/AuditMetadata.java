package edu.courseflow.promotion.service;

import edu.courseflow.commonlibrary.web.CurrentUser;
import java.util.UUID;

record AuditMetadata(String correlationId, String sourceClientId) {

    private static final int CORRELATION_ID_MAX_LENGTH = 120;
    private static final int SOURCE_CLIENT_ID_MAX_LENGTH = 160;

    AuditMetadata {
        correlationId = normalize(correlationId, CORRELATION_ID_MAX_LENGTH);
        sourceClientId = normalize(sourceClientId, SOURCE_CLIENT_ID_MAX_LENGTH);
    }

    static AuditMetadata from(CurrentUser user, IncentiveAccessService access, String correlationId) {
        return new AuditMetadata(correlationId, access.sourceClientId(user));
    }

    static AuditMetadata system(String sourceClientId, String correlationPrefix) {
        String prefix = correlationPrefix == null || correlationPrefix.isBlank()
                ? "promotion-system"
                : correlationPrefix.trim();
        return new AuditMetadata(prefix + "-" + UUID.randomUUID(), sourceClientId);
    }

    private static String normalize(String value, int maxLength) {
        if (value == null || value.isBlank()) {
            return null;
        }
        String normalized = value.trim();
        return normalized.length() <= maxLength ? normalized : normalized.substring(0, maxLength);
    }
}
