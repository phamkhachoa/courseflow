package edu.courseflow.discussion.model;

import edu.courseflow.discussion.dto.DiscussionDtos.CreateThreadRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "discussion_threads")
public class DiscussionThread {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "assignment_id")
    private UUID assignmentId;

    @Column(name = "author_id", nullable = false, length = 64)
    private String authorId;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, length = 40)
    private String status = "OPEN";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected DiscussionThread() {
    }

    public DiscussionThread(CreateThreadRequestDto request) {
        this.id = UUID.randomUUID();
        this.courseId = UUID.fromString(request.courseId());
        this.assignmentId = request.assignmentId() == null || request.assignmentId().isBlank()
                ? null
                : UUID.fromString(request.assignmentId());
        this.authorId = request.authorId();
        this.title = request.title();
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public UUID getAssignmentId() { return assignmentId; }
    public String getAuthorId() { return authorId; }
    public String getTitle() { return title; }
    public String getStatus() { return status; }
    public Instant getCreatedAt() { return createdAt; }
}
