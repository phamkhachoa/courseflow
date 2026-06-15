package edu.courseflow.analytics.service;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RecommendationMlMaterializationSchedulerTest {

    @Mock
    private RecommendationService recommendations;

    private RecommendationMlMaterializationScheduler scheduler;

    @BeforeEach
    void setUp() {
        scheduler = new RecommendationMlMaterializationScheduler(
                recommendations,
                25,
                30_000,
                "analytics-test",
                300_000);
    }

    @Test
    void materializesPendingTrainingRuns() {
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();
        when(recommendations.claimPendingMlTrainingRunIdsForMaterialization(eq(25), eq(30_000L), any(), eq(300_000L)))
                .thenReturn(List.of(first, second));

        scheduler.materializeCompletedTrainingRuns();

        verify(recommendations).claimPendingMlTrainingRunIdsForMaterialization(eq(25), eq(30_000L), any(), eq(300_000L));
        verify(recommendations).materializeMlTrainingRun(first);
        verify(recommendations).materializeMlTrainingRun(second);
        verify(recommendations).syncActiveMlModelReadModel();
    }
}
