package edu.courseflow.course.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.course.exception.ForbiddenException;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class EnrollmentMembershipClient {

    private static final Logger log = LoggerFactory.getLogger(EnrollmentMembershipClient.class);
    private static final Set<String> LEARNING_STATUSES = Set.of("ACTIVE", "ENROLLED", "COMPLETED");

    private final RestClient enrollmentClient;
    private final InternalJwtService internalJwt;

    @Autowired
    public EnrollmentMembershipClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.entitlement.enrollment-service-url:http://enrollment-service:8080}") String enrollmentServiceUrl,
            @Value("${courseflow.entitlement.membership-timeout-ms:1500}") long membershipTimeoutMs,
            InternalJwtService internalJwt) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int timeoutMs = (int) Math.max(250, Math.min(membershipTimeoutMs, 5000));
        requestFactory.setConnectTimeout(timeoutMs);
        requestFactory.setReadTimeout(timeoutMs);
        this.enrollmentClient = restClientBuilder.clone()
                .baseUrl(enrollmentServiceUrl)
                .requestFactory(requestFactory)
                .build();
        this.internalJwt = internalJwt;
    }

    EnrollmentMembershipClient(RestClient enrollmentClient, InternalJwtService internalJwt) {
        this.enrollmentClient = enrollmentClient;
        this.internalJwt = internalJwt;
    }

    public List<EnrollmentSummary> listLearnerEnrollments(CurrentUser user, int limit) {
        requireAuthenticated(user);
        List<EnrollmentSummary> rows;
        try {
            rows = enrollmentClient.get()
                    .uri(uri -> uri.path("/internal/learner-memberships")
                            .queryParam("studentId", String.valueOf(user.id()))
                            .build())
                    .headers(headers -> internalJwt.applyUserToken(headers, user))
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {
                    });
        } catch (RestClientException ex) {
            log.warn("Learner enrollment membership lookup failed for student {}: {}", user.id(), ex.getMessage());
            log.debug("Learner enrollment membership lookup failure details", ex);
            throw new EnrollmentMembershipUnavailableException("Enrollment membership lookup is unavailable", ex);
        }
        if (rows == null || rows.isEmpty()) {
            return List.of();
        }
        return rows.stream()
                .filter(row -> LEARNING_STATUSES.contains(normalize(row.status())))
                .limit(Math.max(0, limit))
                .toList();
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authentication required");
        }
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim().toUpperCase();
    }

    public record EnrollmentSummary(
            String id,
            String studentId,
            String courseId,
            String sectionId,
            String status,
            Instant enrolledAt,
            Instant droppedAt,
            Instant completedAt,
            String dropReason
    ) {
    }

    public static class EnrollmentMembershipUnavailableException extends RuntimeException {
        public EnrollmentMembershipUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
