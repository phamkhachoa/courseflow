package edu.courseflow.analytics.service;

import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
        prefix = "courseflow.analytics.recommendation-ml.materialization",
        name = "enabled",
        havingValue = "true",
        matchIfMissing = true)
public class RecommendationMlMaterializationScheduler {

    private static final Logger log = LoggerFactory.getLogger(RecommendationMlMaterializationScheduler.class);

    private final RecommendationService recommendations;
    private final int batchSize;
    private final long minCheckIntervalMs;
    private final String workerId;
    private final long lockLeaseMs;

    public RecommendationMlMaterializationScheduler(
            RecommendationService recommendations,
            @Value("${courseflow.analytics.recommendation-ml.materialization.batch-size:25}") int batchSize,
            @Value("${courseflow.analytics.recommendation-ml.materialization.min-check-interval-ms:30000}")
            long minCheckIntervalMs,
            @Value("${courseflow.analytics.recommendation-ml.materialization.worker-id:analytics-service}")
            String workerId,
            @Value("${courseflow.analytics.recommendation-ml.materialization.lock-lease-ms:300000}")
            long lockLeaseMs) {
        this.recommendations = recommendations;
        this.batchSize = Math.max(1, Math.min(batchSize, 100));
        this.minCheckIntervalMs = Math.max(1000, minCheckIntervalMs);
        this.workerId = boundedWorkerId(workerId);
        this.lockLeaseMs = Math.max(10_000, lockLeaseMs);
    }

    @Scheduled(fixedDelayString = "${courseflow.analytics.recommendation-ml.materialization.fixed-delay-ms:30000}")
    public void materializeCompletedTrainingRuns() {
        for (UUID trainingRunId : recommendations.claimPendingMlTrainingRunIdsForMaterialization(
                batchSize,
                minCheckIntervalMs,
                workerId,
                lockLeaseMs)) {
            try {
                recommendations.materializeMlTrainingRun(trainingRunId);
            } catch (RuntimeException ex) {
                log.warn("Recommendation ML materialization failed for trainingRunId={}", trainingRunId, ex);
            }
        }
        try {
            recommendations.syncActiveMlModelReadModel();
        } catch (RuntimeException ex) {
            log.warn("Recommendation ML active model sync failed", ex);
        }
    }

    private static String boundedWorkerId(String configuredWorkerId) {
        String prefix = configuredWorkerId == null || configuredWorkerId.isBlank()
                ? "analytics-service"
                : configuredWorkerId.trim();
        String value = prefix + "-" + UUID.randomUUID();
        return value.length() <= 120 ? value : value.substring(0, 120);
    }
}
