package edu.courseflow.commonlibrary.security;

import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * Shared course-entitlement guard backed by enrollment-service.
 *
 * <p>Staff roles are allowed locally. Student access is checked through a service-to-service endpoint
 * using {@code X-Service-Token}; the gateway strips that header from public traffic, so clients cannot
 * spoof this trust path.
 */
@Component
@ConditionalOnClass(RestClient.class)
public class CourseAccessClient {

    public static final String SERVICE_TOKEN_HEADER = "X-Service-Token";

    private final RestClient enrollmentClient;
    private final String serviceToken;

    public CourseAccessClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.entitlement.enrollment-service-url:http://localhost:8084}") String enrollmentServiceUrl,
            @Value("${courseflow.security.service-token:}") String serviceToken) {
        this.enrollmentClient = restClientBuilder.baseUrl(enrollmentServiceUrl).build();
        this.serviceToken = serviceToken == null ? "" : serviceToken.trim();
    }

    public void requireCourseAccess(CurrentUser user, UUID courseId) {
        if (user == null || user.id() == null) {
            throw new UnauthorizedException("Authentication required");
        }
        if (isStaff(user)) {
            return;
        }
        requireStudentCourseAccess(String.valueOf(user.id()), courseId);
    }

    public void requireStudentCourseAccess(String studentId, UUID courseId) {
        if (!canStudentAccessCourse(studentId, courseId)) {
            throw new ForbiddenException("Student is not enrolled in this course");
        }
    }

    public boolean canStudentAccessCourse(String studentId, UUID courseId) {
        if (studentId == null || studentId.isBlank() || courseId == null) {
            return false;
        }
        if (serviceToken.isBlank()) {
            throw new ForbiddenException("Course entitlement service token is not configured");
        }
        CourseAccessResponse response = enrollmentClient.get()
                .uri(uri -> uri.path("/internal/enrollments/access")
                        .queryParam("courseId", courseId)
                        .queryParam("studentId", studentId)
                        .build())
                .header(SERVICE_TOKEN_HEADER, serviceToken)
                .retrieve()
                .body(CourseAccessResponse.class);
        return response != null && response.enrolled();
    }

    private boolean isStaff(CurrentUser user) {
        return user.hasAnyRole("ADMIN", "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA");
    }

    public record CourseAccessResponse(
            String courseId,
            String studentId,
            boolean enrolled,
            String status
    ) {
    }
}
