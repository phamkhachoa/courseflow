package edu.courseflow.deadline.model;

import edu.courseflow.deadline.dto.DeadlineDtos.CreateReminderPolicyRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "reminder_policies")
public class ReminderPolicy {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private String name;

    @Column(name = "offset_minutes", nullable = false)
    private int offsetMinutes;

    @Column(nullable = false, length = 40)
    private String channel;

    @Column(nullable = false)
    private boolean enabled = true;

    protected ReminderPolicy() {
    }

    public ReminderPolicy(CreateReminderPolicyRequestDto request) {
        this.id = UUID.randomUUID();
        this.courseId = UUID.fromString(request.courseId());
        this.name = request.name();
        this.offsetMinutes = request.offsetMinutes();
        this.channel = request.channel();
        this.enabled = true;
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getName() { return name; }
    public int getOffsetMinutes() { return offsetMinutes; }
    public String getChannel() { return channel; }
    public boolean isEnabled() { return enabled; }
}
