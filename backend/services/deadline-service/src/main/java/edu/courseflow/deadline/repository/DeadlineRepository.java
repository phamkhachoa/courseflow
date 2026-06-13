package edu.courseflow.deadline.repository;

import edu.courseflow.deadline.dto.DeadlineDtos.CreateReminderPolicyRequestDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderPolicyDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ReminderRunDto;
import edu.courseflow.deadline.dto.DeadlineDtos.ScheduleReminderRequestDto;
import edu.courseflow.deadline.mapper.DeadlineMapper;
import edu.courseflow.deadline.model.OutboxEvent;
import edu.courseflow.deadline.model.ReminderPolicy;
import edu.courseflow.deadline.model.ReminderRun;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class DeadlineRepository {

    private final ReminderPolicyJpaRepository policies;
    private final ReminderRunJpaRepository runs;
    private final OutboxEventRepository outboxEvents;
    private final DeadlineMapper mapper;

    public DeadlineRepository(ReminderPolicyJpaRepository policies,
            ReminderRunJpaRepository runs,
            OutboxEventRepository outboxEvents,
            DeadlineMapper mapper) {
        this.policies = policies;
        this.runs = runs;
        this.outboxEvents = outboxEvents;
        this.mapper = mapper;
    }

    public List<ReminderPolicyDto> listPolicies(UUID courseId) {
        List<ReminderPolicy> rows = courseId == null
                ? policies.findAllByOrderByNameAsc()
                : policies.findByCourseIdOrderByNameAsc(courseId);
        return rows.stream().map(mapper::toDto).toList();
    }

    public Optional<ReminderPolicyDto> findPolicy(UUID policyId) {
        return policies.findById(policyId).map(mapper::toDto);
    }

    public ReminderPolicyDto createPolicy(CreateReminderPolicyRequestDto request) {
        return mapper.toDto(policies.save(new ReminderPolicy(request)));
    }

    public ReminderRunDto schedule(ScheduleReminderRequestDto request) {
        UUID assignmentId = UUID.fromString(request.assignmentId());
        UUID policyId = UUID.fromString(request.reminderPolicyId());
        ReminderRun run = runs.findByAssignmentIdAndStudentIdAndReminderPolicyId(
                        assignmentId, request.studentId(), policyId)
                .orElseGet(() -> new ReminderRun(request));
        run.updateSchedule(request.reminderAt());
        return mapper.toDto(runs.save(run));
    }

    public List<ReminderRunDto> dueRuns() {
        return runs.findByStatusAndReminderAtLessThanEqualOrderByReminderAtAsc("PENDING", Instant.now())
                .stream()
                .map(mapper::toDto)
                .toList();
    }

    public void markStatus(UUID reminderRunId, String status) {
        runs.findById(reminderRunId).ifPresent(run -> {
            run.markStatus(status);
            runs.save(run);
        });
    }

    public java.util.Optional<ReminderRunDto> lockDuePending(UUID reminderRunId) {
        return runs.lockDuePending(reminderRunId, Instant.now()).map(mapper::toDto);
    }

    public Optional<ReminderRunDto> findRun(UUID reminderRunId) {
        return runs.findById(reminderRunId).map(mapper::toDto);
    }

    public void outbox(UUID aggregateId, String eventType, String payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "deadline-reminder", eventType, payload));
    }

}
