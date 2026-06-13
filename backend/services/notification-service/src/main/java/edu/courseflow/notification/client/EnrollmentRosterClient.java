package edu.courseflow.notification.client;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import java.util.List;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * Reads a course roster from enrollment-service so announcement notifications can be fanned out to
 * the real recipients. notification-service has no enrollment data of its own (separate DB), so it
 * must ask the owning service. Calls hit the internal endpoint directly (service-to-service traffic
 * does not traverse the gateway); this is a read-only roster lookup so no acting identity is forwarded.
 */
@Component
public class EnrollmentRosterClient {

    private final RestClient restClient;
    private final InternalJwtService internalJwt;

    public EnrollmentRosterClient(RestClient.Builder builder,
                                  @Value("${courseflow.enrollment.base-url:http://enrollment-service:8080}") String baseUrl,
                                  InternalJwtService internalJwt) {
        this.restClient = builder.baseUrl(baseUrl).build();
        this.internalJwt = internalJwt;
    }

    /** Minimal projection of an enrollment row; only the fields the fan-out needs. */
    public record EnrollmentView(String studentId, String status) {}

    /**
     * Return the student ids that are ACTIVE in the given course. A genuinely empty roster returns an
     * empty list. A <em>fetch failure</em> (enrollment-service down, timeout, 5xx) is propagated as an
     * exception on purpose: the caller runs inside a transaction that also records dedup, so swallowing
     * the error here would commit "processed" and silently lose the fan-out forever. Letting it throw
     * lets the Kafka error handler retry and, past the budget, route the event to the DLT.
     */
    public List<String> activeStudentIds(String courseId) {
        List<EnrollmentView> rows = restClient.get()
                .uri(uriBuilder -> uriBuilder.path("/internal/enrollments/roster")
                        .queryParam("courseId", courseId)
                        .build())
                .headers(internalJwt::applyServiceToken)
                .retrieve()
                .body(new org.springframework.core.ParameterizedTypeReference<List<EnrollmentView>>() {});
        if (rows == null) {
            return List.of();
        }
        return rows.stream()
                .filter(r -> r.studentId() != null && "ACTIVE".equalsIgnoreCase(r.status()))
                .map(EnrollmentView::studentId)
                .distinct()
                .toList();
    }

}
