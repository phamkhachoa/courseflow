package edu.courseflow.discussion.model;

import edu.courseflow.discussion.dto.DiscussionDtos.CreateCommentRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "discussion_comments")
public class DiscussionComment {

    @Id
    private UUID id;

    @Column(name = "thread_id", nullable = false)
    private UUID threadId;

    @Column(name = "author_id", nullable = false, length = 64)
    private String authorId;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String body;

    @Column(nullable = false)
    private boolean accepted;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected DiscussionComment() {
    }

    public DiscussionComment(UUID threadId, CreateCommentRequestDto request) {
        this.id = UUID.randomUUID();
        this.threadId = threadId;
        this.authorId = request.authorId();
        this.body = request.body();
    }

    public UUID getId() { return id; }
    public UUID getThreadId() { return threadId; }
    public String getAuthorId() { return authorId; }
    public String getBody() { return body; }
    public boolean isAccepted() { return accepted; }
    public Instant getCreatedAt() { return createdAt; }

    public void accept() {
        this.accepted = true;
    }
}
