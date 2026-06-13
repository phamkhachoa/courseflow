package edu.courseflow.accesscontrol.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.SequenceGenerator;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "access_users")
public class AccessUser {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "access_user_id_seq")
    @SequenceGenerator(name = "access_user_id_seq", sequenceName = "access_user_id_seq", allocationSize = 50)
    private Long id;

    @Column(length = 255)
    private String email;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "tokens_valid_after")
    private Instant tokensValidAfter;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected AccessUser() {
    }

    public AccessUser(Long id, String email) {
        this.id = id;
        this.email = email;
        this.status = "ACTIVE";
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public AccessUser(String email) {
        this.email = email;
        this.status = "ACTIVE";
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public Long getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public String getStatus() {
        return status;
    }

    public Instant getTokensValidAfter() {
        return tokensValidAfter;
    }

    public void updateEmail(String email) {
        if (email != null && !email.isBlank()) {
            this.email = email;
            touch();
        }
    }

    public void invalidateTokens() {
        this.tokensValidAfter = Instant.now();
        touch();
    }

    public void deactivate() {
        this.status = "DEACTIVATED";
        invalidateTokens();
    }

    private void touch() {
        this.updatedAt = Instant.now();
    }
}
