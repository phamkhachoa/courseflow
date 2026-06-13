package edu.courseflow.deadline.service;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class DeadlineReminderSchedulerTest {

    private static final UUID FIRST_ID = UUID.fromString("61000000-0000-0000-0000-000000000001");
    private static final UUID SECOND_ID = UUID.fromString("61000000-0000-0000-0000-000000000002");

    @Mock
    private DeadlineService deadlines;

    private DeadlineReminderScheduler scheduler;

    @BeforeEach
    void setUp() {
        scheduler = new DeadlineReminderScheduler(deadlines);
    }

    @Test
    void dispatchDueRemindersContinuesAfterStaleClaim() {
        when(deadlines.dueRuns()).thenReturn(List.of(run(FIRST_ID), run(SECOND_ID)));
        when(deadlines.dispatch(FIRST_ID)).thenThrow(new IllegalArgumentException("already claimed"));

        scheduler.dispatchDueReminders();

        verify(deadlines).dispatch(FIRST_ID);
        verify(deadlines).dispatch(SECOND_ID);
    }

    private ReminderRunDto run(UUID id) {
        return new ReminderRunDto(
                id.toString(),
                "63000000-0000-0000-0000-000000000001",
                "4",
                "62000000-0000-0000-0000-000000000001",
                Instant.parse("2026-07-01T00:00:00Z"),
                "PENDING");
    }
}
