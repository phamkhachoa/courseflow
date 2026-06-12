package edu.courseflow.deadline.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.deadline.dto.DeadlineDtos.CreateReminderPolicyRequestDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ScheduleReminderRequestDto;
import edu.courseflow.deadline.repository.DeadlineRepository;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DeadlineService {

    private final DeadlineRepository deadlines;
    private final ObjectMapper objectMapper;

    public DeadlineService(DeadlineRepository deadlines, ObjectMapper objectMapper) {
        this.deadlines = deadlines;
        this.objectMapper = objectMapper;
    }

    public List<ReminderPolicyDto> listPolicies(Optional<UUID> courseId) {
        return deadlines.listPolicies(courseId.orElse(null));
    }

    @Transactional
    public ReminderPolicyDto createPolicy(CreateReminderPolicyRequestDto request) {
        return deadlines.createPolicy(request);
    }

    @Transactional
    public ReminderRunDto schedule(ScheduleReminderRequestDto request) {
        return deadlines.schedule(request);
    }

    public List<ReminderRunDto> dueRuns() {
        return deadlines.dueRuns();
    }

    @Transactional
    public ReminderRunDto dispatch(UUID reminderRunId) {
        ReminderRunDto run = deadlines.lockDuePending(reminderRunId)
                .orElseThrow(() -> new IllegalArgumentException("Reminder run is not due: " + reminderRunId));
        deadlines.markStatus(reminderRunId, "DISPATCHED");
        deadlines.outbox(reminderRunId, "deadline.reminder.due", toJson(Map.of(
                "eventId", UUID.randomUUID().toString(),
                "reminderId", reminderRunId.toString(),
                "assignmentId", run.assignmentId(),
                "studentId", run.studentId(),
                "reminderAt", run.reminderAt().toString())));
        return new ReminderRunDto(run.id(), run.assignmentId(), run.studentId(), run.reminderPolicyId(), run.reminderAt(), "DISPATCHED");
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
