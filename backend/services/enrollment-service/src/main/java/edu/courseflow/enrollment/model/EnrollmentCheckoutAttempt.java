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
        name = "enrollment_checkout_attempts",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_enrollment_checkout_attempt_idempotency_key",
                columnNames = "idempotency_key"))
public class EnrollmentCheckoutAttempt {

    @Id
    private UUID id;

    @Column(name = "idempotency_key", nullable = false, length = 180)
    private String idempotencyKey;

    @Column(name = "request_hash", nullable = false, length = 96)
    private String requestHash;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "promotion_preview_id", length = 120)
    private String promotionPreviewId;

    @Column(name = "reservation_id")
    private UUID reservationId;

    @Column(name = "redemption_id")
    private UUID redemptionId;

    @Column(name = "enrollment_id")
    private UUID enrollmentId;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(name = "retry_count", nullable = false)
    private int retryCount;

    @Column(name = "next_retry_at")
    private Instant nextRetryAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "response_json", columnDefinition = "jsonb")
    private String responseJson;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected EnrollmentCheckoutAttempt() {
    }

    public EnrollmentCheckoutAttempt(
            String idempotencyKey,
            String requestHash,
            UUID courseId,
            String studentId,
            String promotionPreviewId) {
        this.id = UUID.randomUUID();
        this.idempotencyKey = idempotencyKey;
        this.requestHash = requestHash;
        this.courseId = courseId;
        this.studentId = studentId;
        this.promotionPreviewId = promotionPreviewId;
        this.status = "STARTED";
    }

    public void markReserved(UUID reservationId) {
        this.status = "RESERVED";
        this.reservationId = reservationId;
        this.updatedAt = Instant.now();
    }

    public void markEnrollmentCreated(UUID enrollmentId) {
        this.status = "ENROLLMENT_CREATED";
        this.enrollmentId = enrollmentId;
        this.updatedAt = Instant.now();
    }

    public void markCommitting() {
        this.status = "COMMITTING";
        this.updatedAt = Instant.now();
    }

    public void finish(String status, String responseJson, UUID redemptionId) {
        this.status = status;
        this.responseJson = responseJson;
        this.redemptionId = redemptionId;
        this.errorMessage = null;
        this.nextRetryAt = null;
        this.updatedAt = Instant.now();
    }

    public void fail(String message) {
        this.status = "FAILED";
        this.errorMessage = message;
        this.updatedAt = Instant.now();
    }

    public void retryFailed(String message, Instant nextRetryAt) {
        retryFailed(message, nextRetryAt, this.responseJson);
    }

    public void retryFailed(String message, Instant nextRetryAt, String responseJson) {
        this.status = "COMMIT_FAILED";
        this.retryCount++;
        this.errorMessage = message;
        this.nextRetryAt = nextRetryAt;
        this.responseJson = responseJson;
        this.updatedAt = Instant.now();
    }

    public UUID getId() { return id; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getRequestHash() { return requestHash; }
    public UUID getCourseId() { return courseId; }
    public String getStudentId() { return studentId; }
    public String getPromotionPreviewId() { return promotionPreviewId; }
    public UUID getReservationId() { return reservationId; }
    public UUID getRedemptionId() { return redemptionId; }
    public UUID getEnrollmentId() { return enrollmentId; }
    public String getStatus() { return status; }
    public int getRetryCount() { return retryCount; }
    public Instant getNextRetryAt() { return nextRetryAt; }
    public String getResponseJson() { return responseJson; }
    public String getErrorMessage() { return errorMessage; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
