package edu.courseflow.assignment.service;

import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import java.time.Instant;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class LearningAccessClient {

    private final RestClient courseClient;
    private final InternalJwtService internalJwt;

    public LearningAccessClient(RestClient.Builder restClientBuilder,
                                @Value("${courseflow.entitlement.course-service-url:http://course-service:8080}")
                                String courseServiceUrl,
                                InternalJwtService internalJwt) {
        this.courseClient = restClientBuilder.baseUrl(courseServiceUrl).build();
        this.internalJwt = internalJwt;
    }

    public void requireSourceAccess(UUID courseId, String studentId, String sourceType, UUID sourceId) {
        try {
            LearningAccessCheckDto access = courseClient.post()
                    .uri("/internal/courses/{courseId}/learning-access/check", courseId)
                    .headers(internalJwt::applyServiceToken)
                    .body(new LearningAccessCheckRequestDto(studentId, sourceType, sourceId.toString()))
                    .retrieve()
                    .body(LearningAccessCheckDto.class);
            if (access == null || !access.allowed()) {
                String code = access == null || access.reasonCode() == null
                        ? "LEARNING_ACCESS_DENIED"
                        : access.reasonCode();
                throw new ForbiddenException(code);
            }
        } catch (ForbiddenException ex) {
            throw ex;
        } catch (RestClientException ex) {
            throw new ForbiddenException("LEARNING_ACCESS_POLICY_UNAVAILABLE");
        }
    }

    private record LearningAccessCheckRequestDto(
            String studentId,
            String sourceType,
            String sourceId
    ) {
    }

    private record LearningAccessCheckDto(
            Instant generatedAt,
            String courseId,
            String studentId,
            String sourceType,
            String sourceId,
            boolean allowed,
            String reasonCode,
            String reasonText,
            String moduleId,
            String itemId
    ) {
    }
}
