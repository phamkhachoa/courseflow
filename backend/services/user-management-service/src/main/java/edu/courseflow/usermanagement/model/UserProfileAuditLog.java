package edu.courseflow.usermanagement.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "user_profile_audit_logs")
public class UserProfileAuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private UserProfile profile;

    @Column(name = "actor_id", length = 80)
    private String actorId;

    @Column(nullable = false, length = 80)
    private String action;

    @Column(length = 255)
    private String detail;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected UserProfileAuditLog() {
    }

    public UserProfileAuditLog(UserProfile profile, String actorId, String action, String detail) {
        this.profile = profile;
        this.actorId = actorId;
        this.action = action;
        this.detail = detail;
        this.createdAt = Instant.now();
    }
}
