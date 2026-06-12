package edu.courseflow.deadline.model;

import edu.courseflow.deadline.dto.DeadlineDtos.ScheduleReminderRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "reminder_runs")
public class ReminderRun {

    @Id
    private UUID id;

    @Column(name = "assignment_id", nullable = false)
    private UUID assignmentId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "reminder_policy_id", nullable = false)
    private UUID reminderPolicyId;

    @Column(name = "reminder_at", nullable = false)
    private Instant reminderAt;

    @Column(nullable = false, length = 40)
    private String status = "PENDING";

    @Version
    @Column(nullable = false)
    private long version;

    protected ReminderRun() {
    }

    public ReminderRun(ScheduleReminderRequestDto request) {
        this.id = UUID.randomUUID();
        this.assignmentId = UUID.fromString(request.assignmentId());
        this.studentId = request.studentId();
        this.reminderPolicyId = UUID.fromString(request.reminderPolicyId());
        updateSchedule(request.reminderAt());
    }

    public UUID getId() { return id; }
    public UUID getAssignmentId() { return assignmentId; }
    public String getStudentId() { return studentId; }
    public UUID getReminderPolicyId() { return reminderPolicyId; }
    public Instant getReminderAt() { return reminderAt; }
    public String getStatus() { return status; }

    public void updateSchedule(Instant reminderAt) {
        this.reminderAt = reminderAt;
        this.status = "PENDING";
    }

    public void markStatus(String status) {
        this.status = status;
    }
}
