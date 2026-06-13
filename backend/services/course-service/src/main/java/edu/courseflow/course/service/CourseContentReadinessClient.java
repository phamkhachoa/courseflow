package edu.courseflow.course.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class CourseContentReadinessClient {

    private final RestClient mediaClient;
    private final RestClient quizClient;
    private final RestClient assignmentClient;
    private final InternalJwtService internalJwt;

    public CourseContentReadinessClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.content.media-service-url:http://media-service:8080}") String mediaServiceUrl,
            @Value("${courseflow.content.quiz-service-url:http://quiz-service:8080}") String quizServiceUrl,
            @Value("${courseflow.content.assignment-service-url:http://assignment-service:8080}") String assignmentServiceUrl,
            InternalJwtService internalJwt) {
        this.mediaClient = restClientBuilder.baseUrl(mediaServiceUrl).build();
        this.quizClient = restClientBuilder.baseUrl(quizServiceUrl).build();
        this.assignmentClient = restClientBuilder.baseUrl(assignmentServiceUrl).build();
        this.internalJwt = internalJwt;
    }

    public Optional<String> videoIssue(UUID videoId, UUID courseId) {
        if (videoId == null) {
            return Optional.of("video item without video media");
        }
        VideoReadinessResponse response = fetchReadiness(
                () -> mediaClient.get()
                        .uri("/internal/media/videos/{videoId}/readiness", videoId)
                        .headers(internalJwt::applyServiceToken)
                        .retrieve()
                        .body(VideoReadinessResponse.class),
                "video asset",
                courseId);
        if (response.usable() && "READY".equalsIgnoreCase(response.status())) {
            return Optional.empty();
        }
        return Optional.of("video asset " + videoId + " is not READY");
    }

    public Optional<String> quizIssue(UUID quizId, UUID courseId) {
        QuizReadinessResponse response = fetchReadiness(
                () -> quizClient.get()
                        .uri("/internal/quizzes/{quizId}/readiness", quizId)
                        .headers(internalJwt::applyServiceToken)
                        .retrieve()
                        .body(QuizReadinessResponse.class),
                "quiz",
                courseId);
        if ("PUBLISHED".equalsIgnoreCase(response.status())) {
            return Optional.empty();
        }
        return Optional.of("linked quiz " + quizId + " is not published");
    }

    public Optional<String> assignmentIssue(UUID assignmentId, UUID courseId) {
        AssignmentReadinessResponse response = fetchReadiness(
                () -> assignmentClient.get()
                        .uri("/internal/assignments/{assignmentId}/readiness", assignmentId)
                        .headers(internalJwt::applyServiceToken)
                        .retrieve()
                        .body(AssignmentReadinessResponse.class),
                "assignment",
                courseId);
        if (isPublishedOrActive(response.status())) {
            return Optional.empty();
        }
        return Optional.of("linked assignment " + assignmentId + " is not published");
    }

    private <T extends ContentReadinessResponse> T fetchReadiness(
            ReadinessRequest<T> request,
            String label,
            UUID courseId) {
        T response;
        try {
            response = request.fetch();
        } catch (RuntimeException ex) {
            throw new ContentReadinessException(label + " readiness check failed", ex);
        }
        if (response == null || isBlank(response.id())) {
            throw new ContentReadinessException(label + " does not exist");
        }
        if (courseId != null && !isBlank(response.courseId()) && !courseId.toString().equals(response.courseId())) {
            throw new ContentReadinessException(label + " belongs to another course");
        }
        return response;
    }

    private boolean isPublishedOrActive(String status) {
        return "PUBLISHED".equalsIgnoreCase(status) || "ACTIVE".equalsIgnoreCase(status);
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    @FunctionalInterface
    private interface ReadinessRequest<T> {
        T fetch();
    }

    private interface ContentReadinessResponse {
        String id();

        String courseId();
    }

    public static class ContentReadinessException extends RuntimeException {
        ContentReadinessException(String message) {
            super(message);
        }

        ContentReadinessException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    private record VideoReadinessResponse(String id, String courseId, String status, boolean usable)
            implements ContentReadinessResponse {
    }

    private record QuizReadinessResponse(String id, String courseId, String status)
            implements ContentReadinessResponse {
    }

    private record AssignmentReadinessResponse(String id, String courseId, String status)
            implements ContentReadinessResponse {
    }
}
