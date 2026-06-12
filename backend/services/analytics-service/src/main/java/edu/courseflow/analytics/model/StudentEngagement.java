package edu.courseflow.analytics.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "student_engagement")
public class StudentEngagement {

    @Id
    private UUID id;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "engagement_score", nullable = false)
    private BigDecimal engagementScore = BigDecimal.ZERO;

    @Column(name = "login_count_7d", nullable = false)
    private int loginCount7d;

    @Column(name = "time_spent_7d", nullable = false)
    private int timeSpent7d;

    @Column(name = "submissions_7d", nullable = false)
    private int submissions7d;

    @Column(name = "posts_7d", nullable = false)
    private int posts7d;

    @Column(name = "last_activity_at")
    private Instant lastActivityAt;

    @Column(name = "risk_level", nullable = false, length = 20)
    private String riskLevel = "LOW";

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected StudentEngagement() {
    }

    public StudentEngagement(String studentId, UUID courseId) {
        this.id = UUID.randomUUID();
        this.studentId = studentId;
        this.courseId = courseId;
    }

    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public BigDecimal getEngagementScore() { return engagementScore; }
    public int getLoginCount7d() { return loginCount7d; }
    public int getTimeSpent7d() { return timeSpent7d; }
    public int getSubmissions7d() { return submissions7d; }
    public int getPosts7d() { return posts7d; }
    public Instant getLastActivityAt() { return lastActivityAt; }
    public String getRiskLevel() { return riskLevel; }
    public Instant getUpdatedAt() { return updatedAt; }

    public void update(double score, int logins, int timeSpent, int submissions,
            int posts, Instant lastActivity, String risk) {
        this.engagementScore = BigDecimal.valueOf(score);
        this.loginCount7d = logins;
        this.timeSpent7d = timeSpent;
        this.submissions7d = submissions;
        this.posts7d = posts;
        this.lastActivityAt = lastActivity;
        this.riskLevel = risk;
        this.updatedAt = Instant.now();
    }
}
