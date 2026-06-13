package edu.courseflow.accesscontrol.model;

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
@Table(name = "external_identity_links")
public class ExternalIdentityLink {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private AccessUser user;

    @Column(nullable = false, length = 80)
    private String provider = "keycloak";

    @Column(nullable = false)
    private String issuer;

    @Column(nullable = false)
    private String subject;

    @Column(name = "email_at_link")
    private String emailAtLink;

    @Column(name = "email_verified_at_link")
    private Boolean emailVerifiedAtLink;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    @Column(name = "linked_at", nullable = false)
    private Instant linkedAt = Instant.now();

    @Column(name = "last_seen_at")
    private Instant lastSeenAt;

    protected ExternalIdentityLink() {
    }

    public ExternalIdentityLink(AccessUser user, String provider, String issuer, String subject,
            String emailAtLink, Boolean emailVerifiedAtLink) {
        this.user = user;
        this.provider = provider;
        this.issuer = issuer;
        this.subject = subject;
        this.emailAtLink = emailAtLink;
        this.emailVerifiedAtLink = emailVerifiedAtLink;
        this.status = "ACTIVE";
        this.linkedAt = Instant.now();
        this.lastSeenAt = Instant.now();
    }

    public AccessUser getUser() {
        return user;
    }

    public String getIssuer() {
        return issuer;
    }

    public String getSubject() {
        return subject;
    }

    public String getEmailAtLink() {
        return emailAtLink;
    }

    public Boolean getEmailVerifiedAtLink() {
        return emailVerifiedAtLink;
    }

    public String getStatus() {
        return status;
    }

    public void relink(AccessUser user, String emailAtLink, Boolean emailVerifiedAtLink) {
        this.user = user;
        this.emailAtLink = emailAtLink;
        this.emailVerifiedAtLink = emailVerifiedAtLink;
        this.status = "ACTIVE";
        touchSeen();
    }

    public void touchSeen() {
        this.lastSeenAt = Instant.now();
    }
}
