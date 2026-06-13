package edu.courseflow.deadline.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.events.common.EventMetadata;
import edu.courseflow.events.deadline.DeadlineReminderDueEvent;
import edu.courseflow.deadline.dto.DeadlineDtos.CreateReminderPolicyRequestDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ScheduleReminderRequestDto;
import edu.courseflow.deadline.repository.DeadlineRepository;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.time.Duration;
import java.util.List;
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

    public UUID courseIdForPolicy(UUID policyId) {
        ReminderPolicyDto policy = deadlines.findPolicy(policyId)
                .orElseThrow(() -> new NotFoundException("Reminder policy not found: " + policyId));
        return UUID.fromString(policy.courseId());
    }

    public UUID courseIdForReminderRun(UUID reminderRunId) {
        ReminderRunDto run = deadlines.findRun(reminderRunId)
                .orElseThrow(() -> new NotFoundException("Reminder run not found: " + reminderRunId));
        return courseIdForPolicy(UUID.fromString(run.reminderPolicyId()));
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
        ReminderPolicyDto policy = deadlines.findPolicy(UUID.fromString(run.reminderPolicyId()))
                .orElseThrow(() -> new NotFoundException("Reminder policy not found: " + run.reminderPolicyId()));
        var dueAt = run.reminderAt().plus(Duration.ofMinutes(policy.offsetMinutes()));
        var event = new DeadlineReminderDueEvent(
                UUID.randomUUID().toString(),
                reminderRunId.toString(),
                run.assignmentId(),
                policy.courseId(),
                run.studentId(),
                dueAt,
                run.reminderAt(),
                new EventMetadata(null, null, "deadline-service", java.util.Map.of(
                        "policyId", policy.id(),
                        "channel", policy.channel())));
        deadlines.markStatus(reminderRunId, "DISPATCHED");
        deadlines.outbox(reminderRunId, event.eventType(), toJson(event));
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
