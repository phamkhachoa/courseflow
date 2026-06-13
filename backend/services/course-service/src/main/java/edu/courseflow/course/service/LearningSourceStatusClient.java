package edu.courseflow.course.service;

import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.course.dto.LearningDtos.LearningSourceStatusDto;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Component
public class LearningSourceStatusClient {

    private static final Logger log = LoggerFactory.getLogger(LearningSourceStatusClient.class);
    private static final ParameterizedTypeReference<List<LearningSourceStatusDto>> STATUS_LIST =
            new ParameterizedTypeReference<>() {
            };

    private final RestClient quizClient;
    private final RestClient assignmentClient;
    private final InternalJwtService internalJwt;

    public LearningSourceStatusClient(RestClient.Builder restClientBuilder,
            @Value("${courseflow.content.quiz-service-url:http://quiz-service:8080}") String quizServiceUrl,
            @Value("${courseflow.content.assignment-service-url:http://assignment-service:8080}") String assignmentServiceUrl,
            @Value("${courseflow.content.source-status-timeout-ms:1500}") long sourceStatusTimeoutMs,
            InternalJwtService internalJwt) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int timeoutMs = (int) Math.max(250, Math.min(sourceStatusTimeoutMs, 5000));
        requestFactory.setConnectTimeout(timeoutMs);
        requestFactory.setReadTimeout(timeoutMs);
        this.quizClient = restClientBuilder.clone().baseUrl(quizServiceUrl).requestFactory(requestFactory).build();
        this.assignmentClient = restClientBuilder.clone().baseUrl(assignmentServiceUrl).requestFactory(requestFactory).build();
        this.internalJwt = internalJwt;
    }

    public Map<SourceKey, LearningSourceStatusDto> loadStatuses(UUID courseId, String studentId,
                                                                List<SourceRef> sourceRefs) {
        if (courseId == null || isBlank(studentId) || sourceRefs == null || sourceRefs.isEmpty()) {
            return Map.of();
        }
        Set<String> quizIds = sourceIds(sourceRefs, "QUIZ");
        Set<String> assignmentIds = sourceIds(sourceRefs, "ASSIGNMENT");
        Map<SourceKey, LearningSourceStatusDto> statuses = unavailableStatuses(courseId, quizIds, assignmentIds);
        if (!quizIds.isEmpty()) {
            putStatuses(statuses, courseId, "QUIZ", fetchStatuses(
                    "quiz",
                    () -> quizClient.get()
                            .uri(builder -> builder
                                    .path("/internal/quizzes/status")
                                    .queryParam("courseId", courseId)
                                    .queryParam("studentId", studentId)
                                    .queryParam("sourceIds", quizIds.toArray())
                                    .build())
                            .headers(internalJwt::applyServiceToken)
                            .retrieve()
                            .body(STATUS_LIST)));
        }
        if (!assignmentIds.isEmpty()) {
            putStatuses(statuses, courseId, "ASSIGNMENT", fetchStatuses(
                    "assignment",
                    () -> assignmentClient.get()
                            .uri(builder -> builder
                                    .path("/internal/assignments/status")
                                    .queryParam("courseId", courseId)
                                    .queryParam("studentId", studentId)
                                    .queryParam("sourceIds", assignmentIds.toArray())
                                    .build())
                            .headers(internalJwt::applyServiceToken)
                            .retrieve()
                            .body(STATUS_LIST)));
        }
        return Map.copyOf(statuses);
    }

    private Set<String> sourceIds(List<SourceRef> sourceRefs, String sourceType) {
        Set<String> ids = new LinkedHashSet<>();
        for (SourceRef ref : sourceRefs) {
            if (ref != null && sourceType.equals(ref.sourceType()) && !isBlank(ref.sourceId())) {
                ids.add(ref.sourceId());
            }
        }
        return ids;
    }

    private Map<SourceKey, LearningSourceStatusDto> unavailableStatuses(UUID courseId,
                                                                        Set<String> quizIds,
                                                                        Set<String> assignmentIds) {
        Map<SourceKey, LearningSourceStatusDto> result = new HashMap<>();
        quizIds.forEach(sourceId -> result.put(
                new SourceKey("QUIZ", sourceId),
                unavailableStatus(courseId, "QUIZ", sourceId)));
        assignmentIds.forEach(sourceId -> result.put(
                new SourceKey("ASSIGNMENT", sourceId),
                unavailableStatus(courseId, "ASSIGNMENT", sourceId)));
        return result;
    }

    private LearningSourceStatusDto unavailableStatus(UUID courseId, String sourceType, String sourceId) {
        return new LearningSourceStatusDto(
                sourceType,
                sourceId,
                courseId.toString(),
                null,
                "SOURCE_STATUS_UNAVAILABLE",
                null,
                null,
                null,
                null,
                null,
                0,
                null,
                false,
                false);
    }

    private List<LearningSourceStatusDto> fetchStatuses(String label, SourceStatusRequest request) {
        try {
            List<LearningSourceStatusDto> response = request.fetch();
            return response == null ? List.of() : response;
        } catch (RestClientException ex) {
            log.warn("Learning {} status enrichment failed", label, ex);
            return List.of();
        }
    }

    private void putStatuses(Map<SourceKey, LearningSourceStatusDto> result, UUID courseId, String expectedSourceType,
                             List<LearningSourceStatusDto> statuses) {
        for (LearningSourceStatusDto status : statuses) {
            if (status == null || isBlank(status.sourceId())) {
                continue;
            }
            if (!isBlank(status.courseId()) && !courseId.toString().equals(status.courseId())) {
                continue;
            }
            String sourceType = normalize(status.sourceType());
            if (!expectedSourceType.equals(sourceType)) {
                continue;
            }
            result.put(new SourceKey(sourceType, status.sourceId().trim()), status);
        }
    }

    private static String normalize(String value) {
        return value == null || value.isBlank() ? "" : value.trim().toUpperCase();
    }

    private static boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    @FunctionalInterface
    private interface SourceStatusRequest {
        List<LearningSourceStatusDto> fetch();
    }

    public record SourceRef(String sourceType, String sourceId) {
        public SourceRef {
            sourceType = normalize(sourceType);
            sourceId = sourceId == null ? "" : sourceId.trim();
        }
    }

    public record SourceKey(String sourceType, String sourceId) {
        public SourceKey {
            sourceType = normalize(sourceType);
            sourceId = sourceId == null ? "" : sourceId.trim();
        }
    }
}
