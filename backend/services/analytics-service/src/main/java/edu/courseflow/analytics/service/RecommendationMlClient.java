package edu.courseflow.analytics.service;

import edu.courseflow.analytics.repository.RecommendationTrackingEventRepository.TrainingInteractionProjection;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import io.micrometer.core.instrument.MeterRegistry;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

@Component
public class RecommendationMlClient {

    private static final String REQUESTS_METRIC = "courseflow.analytics.recommendation_ml.client.requests";

    private final RestClient client;
    private final InternalJwtService internalJwt;
    private final MeterRegistry meterRegistry;
    private final boolean enabled;
    private final int maxTrainingEvents;

    public RecommendationMlClient(
            RestClient.Builder restClientBuilder,
            InternalJwtService internalJwt,
            MeterRegistry meterRegistry,
            @Value("${courseflow.analytics.recommendation-ml.service-url:http://recommendation-ml-service:8080}")
            String serviceUrl,
            @Value("${courseflow.analytics.recommendation-ml.timeout-ms:2500}") long timeoutMs,
            @Value("${courseflow.analytics.recommendation-ml.enabled:true}") boolean enabled,
            @Value("${courseflow.analytics.recommendation-ml.max-training-events:250000}") int maxTrainingEvents) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        int safeTimeoutMs = (int) Math.max(250, Math.min(timeoutMs, 10_000));
        requestFactory.setConnectTimeout(safeTimeoutMs);
        requestFactory.setReadTimeout(safeTimeoutMs);
        this.client = restClientBuilder.clone()
                .baseUrl(serviceUrl)
                .requestFactory(requestFactory)
                .build();
        this.internalJwt = internalJwt;
        this.meterRegistry = meterRegistry;
        this.enabled = enabled;
        this.maxTrainingEvents = Math.max(100, Math.min(maxTrainingEvents, 1_000_000));
    }

    public TrainingOutcome trainRelatedCourses(UUID trainingRunId,
                                               String requestedModelVersion,
                                               int limitPerCourse,
                                               List<TrainingInteractionProjection> interactions) {
        TrainingRequest request = trainingRequest(trainingRunId, requestedModelVersion, limitPerCourse, interactions);
        if (request == null) {
            return recordOutcome("train", TrainingOutcome.fallback(interactionsFallbackReason()));
        }
        try {
            TrainingResponse response = client.post()
                    .uri("/internal/recommendation-ml/related-courses:train")
                    .headers(headers -> internalJwt.applyServiceToken(
                            headers,
                            List.of(InternalScopes.RECOMMENDATION_ML_TRAIN)))
                    .body(request)
                    .retrieve()
                    .body(TrainingResponse.class);
            return recordOutcome("train", activeOutcome(response));
        } catch (RestClientResponseException ex) {
            return recordOutcome("train", TrainingOutcome.fallback(
                    "RECOMMENDATION_ML_REJECTED_" + ex.getStatusCode().value()));
        } catch (RestClientException ex) {
            return recordOutcome("train", TrainingOutcome.fallback("RECOMMENDATION_ML_UNAVAILABLE"));
        }
    }

    public TrainingOutcome enqueueRelatedCourses(UUID trainingRunId,
                                                 String requestedModelVersion,
                                                 int limitPerCourse,
                                                 List<TrainingInteractionProjection> interactions) {
        TrainingRequest request = trainingRequest(trainingRunId, requestedModelVersion, limitPerCourse, interactions);
        if (request == null) {
            return recordOutcome("enqueue", TrainingOutcome.fallback(interactionsFallbackReason()));
        }
        try {
            TrainingResponse response = client.post()
                    .uri("/internal/recommendation-ml/related-courses:enqueue")
                    .headers(headers -> internalJwt.applyServiceToken(
                            headers,
                            List.of(InternalScopes.RECOMMENDATION_ML_TRAIN)))
                    .body(request)
                    .retrieve()
                    .body(TrainingResponse.class);
            if (response == null) {
                return recordOutcome("enqueue", TrainingOutcome.fallback("RECOMMENDATION_ML_EMPTY_RESPONSE"));
            }
            return recordOutcome("enqueue", TrainingOutcome.accepted(response));
        } catch (RestClientResponseException ex) {
            return recordOutcome("enqueue", TrainingOutcome.fallback(
                    "RECOMMENDATION_ML_REJECTED_" + ex.getStatusCode().value()));
        } catch (RestClientException ex) {
            return recordOutcome("enqueue", TrainingOutcome.fallback("RECOMMENDATION_ML_UNAVAILABLE"));
        }
    }

    public TrainingOutcome trainingRun(UUID trainingRunId) {
        if (!enabled) {
            return recordOutcome("training_run", TrainingOutcome.fallback("RECOMMENDATION_ML_DISABLED"));
        }
        try {
            TrainingResponse response = client.get()
                    .uri("/internal/recommendation-ml/training-runs/{trainingRunId}", trainingRunId)
                    .headers(headers -> internalJwt.applyServiceToken(
                            headers,
                            List.of(InternalScopes.RECOMMENDATION_ML_TRAIN)))
                    .retrieve()
                    .body(TrainingResponse.class);
            if (response == null) {
                return recordOutcome("training_run", TrainingOutcome.fallback("RECOMMENDATION_ML_EMPTY_RESPONSE"));
            }
            if ("ACTIVE".equalsIgnoreCase(response.status())) {
                return recordOutcome("training_run", activeOutcome(response));
            }
            return recordOutcome("training_run", TrainingOutcome.accepted(response));
        } catch (RestClientResponseException ex) {
            return recordOutcome("training_run", TrainingOutcome.fallback(
                    "RECOMMENDATION_ML_REJECTED_" + ex.getStatusCode().value()));
        } catch (RestClientException ex) {
            return recordOutcome("training_run", TrainingOutcome.fallback("RECOMMENDATION_ML_UNAVAILABLE"));
        }
    }

    public ActiveModelOutcome activeModel() {
        if (!enabled) {
            return recordOutcome("active_model", ActiveModelOutcome.fallback("RECOMMENDATION_ML_DISABLED"));
        }
        try {
            ActiveModelResponse response = client.get()
                    .uri("/internal/recommendation-ml/models/active")
                    .headers(headers -> internalJwt.applyServiceToken(
                            headers,
                            List.of(InternalScopes.RECOMMENDATION_ML_INFER)))
                    .retrieve()
                    .body(ActiveModelResponse.class);
            if (response == null) {
                return recordOutcome("active_model", ActiveModelOutcome.fallback("RECOMMENDATION_ML_EMPTY_RESPONSE"));
            }
            if (response.trainingRunId() == null
                    || response.modelVersion() == null
                    || response.modelVersion().isBlank()) {
                return recordOutcome(
                        "active_model",
                        ActiveModelOutcome.fallback("RECOMMENDATION_ML_ACTIVE_MODEL_INCOMPLETE"));
            }
            if (!"ACTIVE".equalsIgnoreCase(response.status())) {
                return recordOutcome(
                        "active_model",
                        ActiveModelOutcome.fallback("RECOMMENDATION_ML_" + response.status()));
            }
            return recordOutcome("active_model", ActiveModelOutcome.available(response));
        } catch (RestClientResponseException ex) {
            return recordOutcome("active_model", ActiveModelOutcome.fallback(
                    "RECOMMENDATION_ML_REJECTED_" + ex.getStatusCode().value()));
        } catch (RestClientException ex) {
            return recordOutcome("active_model", ActiveModelOutcome.fallback("RECOMMENDATION_ML_UNAVAILABLE"));
        }
    }

    public int maxTrainingEvents() {
        return maxTrainingEvents;
    }

    private TrainingInteraction toTrainingInteraction(TrainingInteractionProjection projection) {
        return new TrainingInteraction(
                hashPrincipal(projection.getPrincipalId()),
                projection.getCourseId(),
                projection.getEventType(),
                projection.getOccurredAt(),
                null);
    }

    private TrainingRequest trainingRequest(UUID trainingRunId,
                                            String requestedModelVersion,
                                            int limitPerCourse,
                                            List<TrainingInteractionProjection> interactions) {
        if (!enabled) {
            return null;
        }
        if (interactions == null || interactions.isEmpty()) {
            return null;
        }
        return new TrainingRequest(
                trainingRunId,
                requestedModelVersion,
                1,
                limitPerCourse,
                interactions.stream()
                        .limit(maxTrainingEvents)
                        .map(this::toTrainingInteraction)
                        .toList());
    }

    private String interactionsFallbackReason() {
        return enabled ? "RECOMMENDATION_ML_NO_TRAINING_EVENTS" : "RECOMMENDATION_ML_DISABLED";
    }

    private TrainingOutcome activeOutcome(TrainingResponse response) {
        if (response == null) {
            return TrainingOutcome.fallback("RECOMMENDATION_ML_EMPTY_RESPONSE");
        }
        if (!"ACTIVE".equalsIgnoreCase(response.status()) || response.recommendations() == null
                || response.recommendations().isEmpty()) {
            return TrainingOutcome.fallback("RECOMMENDATION_ML_" + response.status());
        }
        return TrainingOutcome.active(response);
    }

    private TrainingOutcome recordOutcome(String operation, TrainingOutcome outcome) {
        String result = outcome.active() ? "active" : outcome.accepted() ? "accepted" : "fallback";
        recordClientRequest(operation, result, outcome.fallbackReason());
        return outcome;
    }

    private ActiveModelOutcome recordOutcome(String operation, ActiveModelOutcome outcome) {
        String result = outcome.available() ? "available" : "fallback";
        recordClientRequest(operation, result, outcome.fallbackReason());
        return outcome;
    }

    private void recordClientRequest(String operation, String result, String reason) {
        meterRegistry.counter(
                        REQUESTS_METRIC,
                        "operation", operation,
                        "result", result,
                        "reason", metricReason(reason))
                .increment();
    }

    private String metricReason(String reason) {
        if (reason == null || reason.isBlank()) {
            return "none";
        }
        String normalized = reason.trim()
                .toLowerCase(Locale.ROOT)
                .replaceAll("[^a-z0-9_]", "_");
        return normalized.length() > 96 ? normalized.substring(0, 96) : normalized;
    }

    private String hashPrincipal(String principalId) {
        return "sha256:" + sha256(principalId == null ? "" : principalId);
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is required", ex);
        }
    }

    public record TrainingOutcome(
            boolean active,
            boolean accepted,
            TrainingResponse response,
            String fallbackReason
    ) {
        static TrainingOutcome active(TrainingResponse response) {
            return new TrainingOutcome(true, true, response, null);
        }

        static TrainingOutcome accepted(TrainingResponse response) {
            return new TrainingOutcome(false, true, response, null);
        }

        static TrainingOutcome fallback(String reason) {
            return new TrainingOutcome(false, false, null, reason);
        }
    }

    public record ActiveModelOutcome(
            boolean available,
            ActiveModelResponse response,
            String fallbackReason
    ) {
        static ActiveModelOutcome available(ActiveModelResponse response) {
            return new ActiveModelOutcome(true, response, null);
        }

        static ActiveModelOutcome fallback(String reason) {
            return new ActiveModelOutcome(false, null, reason);
        }
    }

    public record TrainingRequest(
            UUID trainingRunId,
            String requestedModelVersion,
            Integer minSupport,
            Integer maxRelatedPerCourse,
            List<TrainingInteraction> interactions
    ) {
    }

    public record TrainingInteraction(
            String principalId,
            UUID courseId,
            String eventType,
            Instant occurredAt,
            Double weight
    ) {
    }

    public record TrainingResponse(
            UUID trainingRunId,
            String modelVersion,
            String status,
            String algorithm,
            int eventCount,
            int principalCount,
            int courseCount,
            int pairCount,
            double qualityScore,
            Instant generatedAt,
            String message,
            List<ScoredRecommendation> recommendations
    ) {
    }

    public record ScoredRecommendation(
            UUID courseId,
            UUID relatedCourseId,
            int rank,
            double score,
            double similarity,
            int supportCount,
            String reasonCode,
            String modelVersion
    ) {
    }

    public record ActiveModelResponse(
            UUID trainingRunId,
            String modelVersion,
            String algorithm,
            String status,
            int eventCount,
            int principalCount,
            int courseCount,
            int pairCount,
            double qualityScore,
            Instant trainedAt,
            Instant activatedAt
    ) {
    }
}
