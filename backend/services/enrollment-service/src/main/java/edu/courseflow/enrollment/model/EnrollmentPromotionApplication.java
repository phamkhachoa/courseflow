package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(
        name = "enrollment_promotion_applications",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_enrollment_promotion_application_enrollment",
                columnNames = "enrollment_id"))
public class EnrollmentPromotionApplication {

    @Id
    private UUID id;

    @Column(name = "enrollment_id", nullable = false)
    private UUID enrollmentId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(name = "coupon_code", length = 120)
    private String couponCode;

    @Column(name = "coupon_id")
    private UUID couponId;

    @Column(name = "reservation_id")
    private UUID reservationId;

    @Column(name = "redemption_id")
    private UUID redemptionId;

    @Column(name = "idempotency_key", length = 180)
    private String idempotencyKey;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "reason_codes_json", nullable = false, columnDefinition = "jsonb")
    private String reasonCodesJson = "[]";

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "effects_json", nullable = false, columnDefinition = "jsonb")
    private String effectsJson = "[]";

    @Column(columnDefinition = "TEXT")
    private String message;

    @Column(name = "retry_count", nullable = false)
    private int retryCount;

    @Column(name = "next_retry_at")
    private Instant nextRetryAt;

    @Column(name = "last_retry_error", columnDefinition = "TEXT")
    private String lastRetryError;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected EnrollmentPromotionApplication() {
    }

    public EnrollmentPromotionApplication(
            UUID enrollmentId,
            String studentId,
            UUID courseId,
            String status,
            String couponCode,
            UUID couponId,
            UUID reservationId,
            UUID redemptionId,
            String idempotencyKey,
            String reasonCodesJson,
            String effectsJson,
            String message) {
        this.id = UUID.randomUUID();
        this.enrollmentId = enrollmentId;
        this.studentId = studentId;
        this.courseId = courseId;
        this.status = status;
        this.couponCode = couponCode;
        this.couponId = couponId;
        this.reservationId = reservationId;
        this.redemptionId = redemptionId;
        this.idempotencyKey = idempotencyKey;
        this.reasonCodesJson = safeArrayJson(reasonCodesJson);
        this.effectsJson = safeArrayJson(effectsJson);
        this.message = message;
        if (!"COMMIT_FAILED".equals(status)) {
            clearRetryState();
        }
    }

    public void update(
            String status,
            UUID redemptionId,
            String reasonCodesJson,
            String effectsJson,
            String message) {
        this.status = status;
        this.redemptionId = redemptionId;
        this.reasonCodesJson = safeArrayJson(reasonCodesJson);
        this.effectsJson = safeArrayJson(effectsJson);
        this.message = message;
        if (!"COMMIT_FAILED".equals(status)) {
            clearRetryState();
        }
        this.updatedAt = Instant.now();
    }

    public void cancel(String reasonCodesJson, String message) {
        this.status = "CANCELLED";
        this.reasonCodesJson = safeArrayJson(reasonCodesJson);
        this.message = message;
        clearRetryState();
        this.updatedAt = Instant.now();
    }

    public void scheduleRetry(String message, Instant nextRetryAt) {
        this.retryCount++;
        this.nextRetryAt = nextRetryAt;
        this.lastRetryError = message;
        this.updatedAt = Instant.now();
    }

    public void recordOperatorBlockingError(String message) {
        this.lastRetryError = message;
        this.updatedAt = Instant.now();
    }

    private void clearRetryState() {
        this.nextRetryAt = null;
        this.lastRetryError = null;
    }

    private String safeArrayJson(String value) {
        return value == null || value.isBlank() ? "[]" : value;
    }

    public UUID getId() { return id; }
    public UUID getEnrollmentId() { return enrollmentId; }
    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public String getStatus() { return status; }
    public String getCouponCode() { return couponCode; }
    public UUID getCouponId() { return couponId; }
    public UUID getReservationId() { return reservationId; }
    public UUID getRedemptionId() { return redemptionId; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getReasonCodesJson() { return reasonCodesJson; }
    public String getEffectsJson() { return effectsJson; }
    public String getMessage() { return message; }
    public int getRetryCount() { return retryCount; }
    public Instant getNextRetryAt() { return nextRetryAt; }
    public String getLastRetryError() { return lastRetryError; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
