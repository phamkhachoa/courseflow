package edu.courseflow.analytics.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import edu.courseflow.analytics.repository.RecommendationTrackingEventRepository.TrainingInteractionProjection;
import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.security.InternalJwtProperties;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.web.client.RestClient;

class RecommendationMlClientTest {

    private static final String INTERNAL_SECRET = "internal-jwt-secret-that-is-at-least-32-bytes";
    private static final String REQUESTS_METRIC = "courseflow.analytics.recommendation_ml.client.requests";
    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID RELATED_ID = UUID.fromString("30000000-0000-0000-0000-000000000002");

    @Test
    void disabledTrainingRecordsFallbackMetricWithoutCallingMlService() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        RecommendationMlClient client = client("http://127.0.0.1:9", registry, false);

        RecommendationMlClient.TrainingOutcome outcome = client.trainRelatedCourses(
                UUID.randomUUID(),
                "model-v1",
                5,
                List.of(interaction(COURSE_ID)));

        assertThat(outcome.accepted()).isFalse();
        assertThat(outcome.fallbackReason()).isEqualTo("RECOMMENDATION_ML_DISABLED");
        assertMetric(registry, "train", "fallback", "recommendation_ml_disabled", 1.0);
    }

    @Test
    void activeTrainingRecordsActiveMetricAndUsesInternalJwt() throws IOException {
        UUID trainingRunId = UUID.randomUUID();
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        AtomicReference<String> method = new AtomicReference<>();
        AtomicReference<String> authHeader = new AtomicReference<>();
        AtomicReference<String> internalAuthHeader = new AtomicReference<>();
        AtomicReference<String> requestBody = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/internal/recommendation-ml/related-courses:train", exchange -> {
            method.set(exchange.getRequestMethod());
            authHeader.set(exchange.getRequestHeaders().getFirst(HttpHeaders.AUTHORIZATION));
            internalAuthHeader.set(exchange.getRequestHeaders().getFirst(GatewayHeaders.INTERNAL_AUTHORIZATION));
            requestBody.set(new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            respondJson(exchange, 200, """
                    {
                      "trainingRunId": "%s",
                      "modelVersion": "model-v1",
                      "status": "ACTIVE",
                      "algorithm": "IMPLICIT_ITEM_CF_V1",
                      "eventCount": 2,
                      "principalCount": 1,
                      "courseCount": 2,
                      "pairCount": 1,
                      "qualityScore": 0.8,
                      "generatedAt": "2026-06-15T00:00:00Z",
                      "message": null,
                      "recommendations": [
                        {
                          "courseId": "%s",
                          "relatedCourseId": "%s",
                          "rank": 1,
                          "score": 0.9,
                          "similarity": 0.9,
                          "supportCount": 2,
                          "reasonCode": "ML_CO_ENROLLMENT",
                          "modelVersion": "model-v1"
                        }
                      ]
                    }
                    """.formatted(trainingRunId, COURSE_ID, RELATED_ID));
        });
        server.start();
        try {
            RecommendationMlClient client = client(baseUrl(server), registry, true);

            RecommendationMlClient.TrainingOutcome outcome = client.trainRelatedCourses(
                    trainingRunId,
                    "model-v1",
                    5,
                    List.of(interaction(COURSE_ID)));

            assertThat(outcome.active()).isTrue();
            assertThat(method.get()).isEqualTo("POST");
            assertThat(authHeader.get()).startsWith("Bearer ");
            assertThat(internalAuthHeader.get()).startsWith("Bearer ");
            assertThat(requestBody.get()).contains("\"principalId\":\"sha256:");
            assertMetric(registry, "train", "active", "none", 1.0);
        } finally {
            server.stop(0);
        }
    }

    @Test
    void activeModelReturnsTrainingRunIdAndRecordsAvailableMetric() throws IOException {
        UUID trainingRunId = UUID.randomUUID();
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        AtomicReference<String> method = new AtomicReference<>();
        AtomicReference<String> authHeader = new AtomicReference<>();
        AtomicReference<String> internalAuthHeader = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/internal/recommendation-ml/models/active", exchange -> {
            method.set(exchange.getRequestMethod());
            authHeader.set(exchange.getRequestHeaders().getFirst(HttpHeaders.AUTHORIZATION));
            internalAuthHeader.set(exchange.getRequestHeaders().getFirst(GatewayHeaders.INTERNAL_AUTHORIZATION));
            respondJson(exchange, 200, """
                    {
                      "trainingRunId": "%s",
                      "modelVersion": "model-v1",
                      "status": "ACTIVE",
                      "algorithm": "IMPLICIT_ITEM_CF_V1",
                      "eventCount": 20,
                      "principalCount": 10,
                      "courseCount": 4,
                      "pairCount": 8,
                      "qualityScore": 0.8,
                      "trainedAt": "2026-06-15T00:00:00Z",
                      "activatedAt": "2026-06-15T00:10:00Z"
                    }
                    """.formatted(trainingRunId));
        });
        server.start();
        try {
            RecommendationMlClient client = client(baseUrl(server), registry, true);

            RecommendationMlClient.ActiveModelOutcome outcome = client.activeModel();

            assertThat(outcome.available()).isTrue();
            assertThat(outcome.response().trainingRunId()).isEqualTo(trainingRunId);
            assertThat(outcome.response().modelVersion()).isEqualTo("model-v1");
            assertThat(method.get()).isEqualTo("GET");
            assertThat(authHeader.get()).startsWith("Bearer ");
            assertThat(internalAuthHeader.get()).startsWith("Bearer ");
            assertMetric(registry, "active_model", "available", "none", 1.0);
        } finally {
            server.stop(0);
        }
    }

    @Test
    void rejectedTrainingRunRecordsBoundedFallbackReason() throws IOException {
        UUID trainingRunId = UUID.randomUUID();
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/internal/recommendation-ml/training-runs/" + trainingRunId,
                exchange -> respondJson(exchange, 503, "{\"message\":\"warming up\"}"));
        server.start();
        try {
            RecommendationMlClient client = client(baseUrl(server), registry, true);

            RecommendationMlClient.TrainingOutcome outcome = client.trainingRun(trainingRunId);

            assertThat(outcome.accepted()).isFalse();
            assertThat(outcome.fallbackReason()).isEqualTo("RECOMMENDATION_ML_REJECTED_503");
            assertMetric(registry, "training_run", "fallback", "recommendation_ml_rejected_503", 1.0);
        } finally {
            server.stop(0);
        }
    }

    private RecommendationMlClient client(String serviceUrl, SimpleMeterRegistry registry, boolean enabled) {
        return new RecommendationMlClient(
                RestClient.builder(),
                internalJwt(),
                registry,
                serviceUrl,
                500,
                enabled,
                1000);
    }

    private InternalJwtService internalJwt() {
        return new InternalJwtService(new InternalJwtProperties(
                INTERNAL_SECRET,
                "courseflow-token-converter",
                "courseflow-services",
                180,
                30,
                "analytics-service"));
    }

    private TrainingInteractionProjection interaction(UUID courseId) {
        return new TrainingInteractionProjection() {
            @Override
            public String getPrincipalId() {
                return "student:1";
            }

            @Override
            public UUID getCourseId() {
                return courseId;
            }

            @Override
            public String getEventType() {
                return "ENROLLMENT";
            }

            @Override
            public Instant getOccurredAt() {
                return Instant.parse("2026-06-15T00:00:00Z");
            }
        };
    }

    private String baseUrl(HttpServer server) {
        return "http://127.0.0.1:" + server.getAddress().getPort();
    }

    private void assertMetric(SimpleMeterRegistry registry,
                              String operation,
                              String result,
                              String reason,
                              double expectedCount) {
        var counter = registry.find(REQUESTS_METRIC)
                .tags("operation", operation, "result", result, "reason", reason)
                .counter();
        assertThat(counter).isNotNull();
        assertThat(counter.count()).isEqualTo(expectedCount);
    }

    private void respondJson(HttpExchange exchange, int status, String body) throws IOException {
        try {
            byte[] response = body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add(HttpHeaders.CONTENT_TYPE, "application/json");
            exchange.sendResponseHeaders(status, response.length);
            exchange.getResponseBody().write(response);
        } finally {
            exchange.close();
        }
    }
}
