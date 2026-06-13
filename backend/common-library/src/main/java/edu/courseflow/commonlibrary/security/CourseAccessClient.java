package edu.courseflow.commonlibrary.security;

import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
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
 * using the shared internal JWT helper, so service clients use the same downstream trust contract.
 */
@Component
@ConditionalOnClass(RestClient.class)
public class CourseAccessClient {

    private static final String STATUS_PUBLISHED = "PUBLISHED";
    private static final String STATUS_ARCHIVED = "ARCHIVED";

    private final RestClient enrollmentClient;
    private final RestClient courseClient;
    private final InternalJwtService internalJwt;

    public CourseAccessClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.entitlement.enrollment-service-url:http://enrollment-service:8080}") String enrollmentServiceUrl,
            @Value("${courseflow.entitlement.course-service-url:http://course-service:8080}") String courseServiceUrl,
            InternalJwtService internalJwt) {
        this.enrollmentClient = restClientBuilder.baseUrl(enrollmentServiceUrl).build();
        this.courseClient = restClientBuilder.baseUrl(courseServiceUrl).build();
        this.internalJwt = internalJwt;
    }

    /**
     * Read access to published course content. Staff must be scoped to the course (or be platform
     * ADMIN); students must be actively/completed enrolled.
     */
    public void requireCourseAccess(CurrentUser user, UUID courseId) {
        if (user == null || user.id() == null) {
            throw new UnauthorizedException("Authentication required");
        }
        CourseMetadataResponse course = requireCourseExists(courseId);
        if (!STATUS_PUBLISHED.equalsIgnoreCase(course.status())) {
            throw new ForbiddenException("Course is not published");
        }
        if (isStaffScopedToCourse(user, course)) {
            return;
        }
        requireStudentCourseAccess(String.valueOf(user.id()), courseId);
    }

    /** Staff-only access to course administration surfaces. */
    public void requireCourseStaffAccess(CurrentUser user, UUID courseId) {
        if (user == null || user.id() == null) {
            throw new UnauthorizedException("Authentication required");
        }
        CourseMetadataResponse course = requireCourseExists(courseId);
        if (!isStaffScopedToCourse(user, course)) {
            throw new ForbiddenException("Caller is not allowed to manage this course");
        }
    }

    public CourseMetadataResponse requirePublishedCourse(UUID courseId) {
        CourseMetadataResponse course = requireCourseExists(courseId);
        if (!STATUS_PUBLISHED.equalsIgnoreCase(course.status())) {
            throw new ForbiddenException("Course is not published");
        }
        return course;
    }

    public CourseMetadataResponse requireCourseExists(UUID courseId) {
        if (courseId == null) {
            throw new NotFoundException("Course not found");
        }
        CourseMetadataResponse response = courseClient.get()
                .uri("/internal/courses/{courseId}/metadata", courseId)
                .headers(internalJwt::applyServiceToken)
                .retrieve()
                .body(CourseMetadataResponse.class);
        if (response == null || response.id() == null) {
            throw new NotFoundException("Course not found: " + courseId);
        }
        return response;
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
        CourseAccessResponse response = enrollmentClient.get()
                .uri(uri -> uri.path("/internal/enrollments/access")
                        .queryParam("courseId", courseId)
                        .queryParam("studentId", studentId)
                        .build())
                .headers(internalJwt::applyServiceToken)
                .retrieve()
                .body(CourseAccessResponse.class);
        return response != null && response.enrolled();
    }

    public boolean canStaffManageCourse(CurrentUser user, UUID courseId) {
        if (user == null || user.id() == null || courseId == null || !isStaff(user)) {
            return false;
        }
        return isStaffScopedToCourse(user, requireCourseExists(courseId));
    }

    private boolean isStaffScopedToCourse(CurrentUser user, CourseMetadataResponse course) {
        if (!isStaff(user)) {
            return false;
        }
        if (user.hasPlatformRole("ADMIN")) {
            return true;
        }
        UUID courseId = UUID.fromString(course.id());
        if (user.hasAnyCourseRole(courseId, "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA")) {
            return true;
        }
        if (user.hasAnyDepartmentRole(course.departmentId(), "ORG_ADMIN", "INSTRUCTOR", "PROFESSOR", "TA")) {
            return true;
        }
        String callerId = String.valueOf(user.id());
        return course.ownerId() != null
                && course.ownerId().equals(callerId)
                && user.hasAnyRole("INSTRUCTOR", "PROFESSOR", "TA", "ORG_ADMIN");
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

    public record CourseMetadataResponse(
            String id,
            String status,
            String reviewState,
            String ownerId,
            String departmentId,
            String title,
            String slug
    ) {
        public boolean archived() {
            return STATUS_ARCHIVED.equalsIgnoreCase(status);
        }
    }
}
