package edu.courseflow.announcement.model;

import edu.courseflow.announcement.dto.AnnouncementDtos.CreateAnnouncementRequestDto;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "announcements")
public class Announcement {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "author_id", nullable = false, length = 64)
    private String authorId;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String body;

    @Column(nullable = false, length = 40)
    private String audience = "ENROLLED";

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "publish_at")
    private Instant publishAt;

    @Column(name = "published_at")
    private Instant publishedAt;

    protected Announcement() {
    }

    public Announcement(CreateAnnouncementRequestDto request) {
        this.id = UUID.randomUUID();
        this.courseId = UUID.fromString(request.courseId());
        this.authorId = request.authorId();
        this.title = request.title();
        this.body = request.body();
        this.audience = request.audience();
        this.publishAt = request.publishAt();
        this.status = "DRAFT";
    }

    public UUID getId() { return id; }
    public UUID getCourseId() { return courseId; }
    public String getAuthorId() { return authorId; }
    public String getTitle() { return title; }
    public String getBody() { return body; }
    public String getAudience() { return audience; }
    public String getStatus() { return status; }
    public Instant getPublishAt() { return publishAt; }
    public Instant getPublishedAt() { return publishedAt; }

    public void publish() {
        this.status = "PUBLISHED";
        this.publishedAt = Instant.now();
    }
}
