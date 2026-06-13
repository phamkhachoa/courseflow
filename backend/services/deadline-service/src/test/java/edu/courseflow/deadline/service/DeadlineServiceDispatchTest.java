package edu.courseflow.deadline.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import edu.courseflow.deadline.repository.DeadlineRepository;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.junit.jupiter.api.extension.ExtendWith;

@ExtendWith(MockitoExtension.class)
class DeadlineServiceDispatchTest {

    private static final UUID REMINDER_ID = UUID.fromString("61000000-0000-0000-0000-000000000001");
    private static final UUID POLICY_ID = UUID.fromString("62000000-0000-0000-0000-000000000001");
    private static final String ASSIGNMENT_ID = "63000000-0000-0000-0000-000000000001";
    private static final String COURSE_ID = "30000000-0000-0000-0000-000000000001";

    @Mock
    private DeadlineRepository deadlines;

    private ObjectMapper objectMapper;
    private DeadlineService service;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper().findAndRegisterModules()
                .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        service = new DeadlineService(deadlines, objectMapper);
    }

    @Test
    void dispatchPublishesContractPayloadWithCourseAndDueAt() throws Exception {
        Instant reminderAt = Instant.parse("2026-07-01T00:00:00Z");
        ReminderRunDto run = new ReminderRunDto(
                REMINDER_ID.toString(), ASSIGNMENT_ID, "4", POLICY_ID.toString(), reminderAt, "PENDING");
        ReminderPolicyDto policy = new ReminderPolicyDto(
                POLICY_ID.toString(), COURSE_ID, "One day before", 1440, "IN_APP", true);
        when(deadlines.lockDuePending(REMINDER_ID)).thenReturn(Optional.of(run));
        when(deadlines.findPolicy(POLICY_ID)).thenReturn(Optional.of(policy));

        ReminderRunDto dispatched = service.dispatch(REMINDER_ID);

        assertThat(dispatched.status()).isEqualTo("DISPATCHED");
        verify(deadlines).markStatus(REMINDER_ID, "DISPATCHED");
        ArgumentCaptor<String> payloadCaptor = ArgumentCaptor.forClass(String.class);
        verify(deadlines).outbox(eq(REMINDER_ID), eq("deadline.reminder.due"), payloadCaptor.capture());
        var payload = objectMapper.readTree(payloadCaptor.getValue());
        assertThat(payload.path("reminderId").asText()).isEqualTo(REMINDER_ID.toString());
        assertThat(payload.path("assignmentId").asText()).isEqualTo(ASSIGNMENT_ID);
        assertThat(payload.path("courseId").asText()).isEqualTo(COURSE_ID);
        assertThat(payload.path("studentId").asText()).isEqualTo("4");
        assertThat(payload.path("dueAt").asText()).isEqualTo("2026-07-02T00:00:00Z");
        assertThat(payload.path("metadata").path("attributes").path("policyId").asText())
                .isEqualTo(POLICY_ID.toString());
    }
}
