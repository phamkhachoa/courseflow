package edu.courseflow.usermanagement.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "user_profiles")
public class UserProfile {

    @Id
    @Column(name = "user_id")
    private Long userId;

    @Column(name = "display_name", nullable = false)
    private String displayName;

    @Column(name = "avatar_url")
    private String avatarUrl;

    @Column(columnDefinition = "TEXT")
    private String bio;

    @Column(nullable = false, length = 20)
    private String locale = "vi-VN";

    @Column(nullable = false, length = 80)
    private String timezone = "Asia/Ho_Chi_Minh";

    @Column(nullable = false, length = 20)
    private String visibility = "PRIVATE";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    protected UserProfile() {
    }

    public UserProfile(Long userId, String displayName, String avatarUrl, String bio,
            String locale, String timezone, String visibility) {
        this.userId = userId;
        update(displayName, avatarUrl, bio, locale, timezone, visibility);
        this.createdAt = Instant.now();
    }

    public Long getUserId() {
        return userId;
    }

    public String getDisplayName() {
        return displayName;
    }

    public String getAvatarUrl() {
        return avatarUrl;
    }

    public String getBio() {
        return bio;
    }

    public String getLocale() {
        return locale;
    }

    public String getTimezone() {
        return timezone;
    }

    public String getVisibility() {
        return visibility;
    }

    public void update(String displayName, String avatarUrl, String bio,
            String locale, String timezone, String visibility) {
        this.displayName = displayName;
        this.avatarUrl = avatarUrl;
        this.bio = bio;
        this.locale = locale;
        this.timezone = timezone;
        this.visibility = visibility;
        this.updatedAt = Instant.now();
    }
}
