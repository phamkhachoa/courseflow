package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "courses")
public class Course {

    @Id
    private UUID id;

    @Column(nullable = false, unique = true, length = 64)
    private String code;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, unique = true)
    private String slug;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String summary;

    @Column(name = "department_id", nullable = false)
    private UUID departmentId;

    @Column(name = "owner_id", nullable = false, length = 64)
    private String ownerId;

    @Column(nullable = false, length = 40)
    private String level;

    @Column(nullable = false, length = 40)
    private String status = "DRAFT";

    @Column(name = "list_price", precision = 12, scale = 2)
    private BigDecimal listPrice;

    @Column(name = "currency", length = 3)
    private String currency;

    @Column(name = "price_status", nullable = false, length = 40)
    private String priceStatus = "NOT_CONFIGURED";

    @Column(name = "current_version_no", nullable = false)
    private int currentVersionNo = 1;

    @Column(name = "published_version_no")
    private Integer publishedVersionNo;

    @Column(name = "review_state", nullable = false, length = 40)
    private String reviewState = "DRAFT";

    @Column(name = "last_authored_by", length = 64)
    private String lastAuthoredBy;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    @Column(nullable = false)
    private long version;

    protected Course() {
    }

    public Course(UUID id, String code, String title, String slug, String summary,
            UUID departmentId, String ownerId, String level) {
        this.id = id;
        this.code = code;
        this.title = title;
        this.slug = slug;
        this.summary = summary;
        this.departmentId = departmentId;
        this.ownerId = ownerId;
        this.level = level;
        this.status = "DRAFT";
        this.reviewState = "DRAFT";
        this.lastAuthoredBy = ownerId;
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public Course(UUID id, String code, String title, String slug, String summary,
            UUID departmentId, String ownerId, String level, BigDecimal listPrice, String currency) {
        this(id, code, title, slug, summary, departmentId, ownerId, level);
        updatePricing(listPrice, currency);
    }

    public UUID getId() {
        return id;
    }

    public String getCode() {
        return code;
    }

    public String getTitle() {
        return title;
    }

    public String getSlug() {
        return slug;
    }

    public String getSummary() {
        return summary;
    }

    public UUID getDepartmentId() {
        return departmentId;
    }

    public String getOwnerId() {
        return ownerId;
    }

    public String getLevel() {
        return level;
    }

    public String getStatus() {
        return status;
    }

    public BigDecimal getListPrice() {
        return listPrice;
    }

    public String getCurrency() {
        return currency;
    }

    public String getPriceStatus() {
        return priceStatus;
    }

    public void setStatus(String status) {
        this.status = status;
        touch();
    }

    public void updatePricing(BigDecimal listPrice, String currency) {
        if (listPrice == null) {
            this.listPrice = null;
            this.currency = null;
            this.priceStatus = "NOT_CONFIGURED";
            touch();
            return;
        }
        if (listPrice.signum() < 0) {
            throw new IllegalArgumentException("Course list price must not be negative");
        }
        String normalizedCurrency = currency == null || currency.isBlank() ? "USD" : currency.trim().toUpperCase();
        if (normalizedCurrency.length() != 3) {
            throw new IllegalArgumentException("Course price currency must be a 3-letter ISO code");
        }
        this.listPrice = listPrice.setScale(2, RoundingMode.HALF_UP);
        this.currency = normalizedCurrency;
        this.priceStatus = this.listPrice.signum() == 0 ? "FREE" : "ACTIVE";
        touch();
    }

    public int getCurrentVersionNo() {
        return currentVersionNo;
    }

    public void setCurrentVersionNo(int currentVersionNo) {
        this.currentVersionNo = currentVersionNo;
        touch();
    }

    public Integer getPublishedVersionNo() {
        return publishedVersionNo;
    }

    public void publishVersion(int publishedVersionNo) {
        this.publishedVersionNo = publishedVersionNo;
        touch();
    }

    public String getReviewState() {
        return reviewState;
    }

    public void setReviewState(String reviewState) {
        this.reviewState = reviewState;
        touch();
    }

    public String getLastAuthoredBy() {
        return lastAuthoredBy;
    }

    public void setLastAuthoredBy(String lastAuthoredBy) {
        this.lastAuthoredBy = lastAuthoredBy;
        touch();
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void touch() {
        this.updatedAt = Instant.now();
    }
}
