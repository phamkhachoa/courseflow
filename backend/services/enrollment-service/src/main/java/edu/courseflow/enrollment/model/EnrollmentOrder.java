package edu.courseflow.enrollment.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(
        name = "enrollment_orders",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_enrollment_order_enrollment",
                columnNames = "enrollment_id"))
public class EnrollmentOrder {

    @Id
    private UUID id;

    @Column(name = "enrollment_id", nullable = false)
    private UUID enrollmentId;

    @Column(name = "checkout_attempt_id")
    private UUID checkoutAttemptId;

    @Column(name = "student_id", nullable = false, length = 64)
    private String studentId;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false, length = 40)
    private String status;

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal amount;

    @Column(nullable = false, length = 12)
    private String currency;

    @Column(name = "payment_provider", length = 80)
    private String paymentProvider;

    @Column(name = "payment_reference", length = 180)
    private String paymentReference;

    @Column(name = "failure_reason", columnDefinition = "TEXT")
    private String failureReason;

    @Column(name = "idempotency_key", length = 180)
    private String idempotencyKey;

    @Column(name = "paid_at")
    private Instant paidAt;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @Version
    private long version;

    protected EnrollmentOrder() {
    }

    public EnrollmentOrder(
            UUID enrollmentId,
            UUID checkoutAttemptId,
            String studentId,
            UUID courseId,
            BigDecimal amount,
            String currency,
            String idempotencyKey) {
        this.id = UUID.randomUUID();
        this.enrollmentId = enrollmentId;
        this.checkoutAttemptId = checkoutAttemptId;
        this.studentId = studentId;
        this.courseId = courseId;
        this.status = "PAYMENT_PENDING";
        this.amount = money(amount);
        this.currency = normalizeCurrency(currency);
        this.idempotencyKey = idempotencyKey;
    }

    public void markPaid(String paymentProvider, String paymentReference) {
        this.status = "PAID";
        this.paymentProvider = normalize(paymentProvider);
        this.paymentReference = normalize(paymentReference);
        this.failureReason = null;
        this.paidAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public void markFailed(String status, String failureReason) {
        this.status = status;
        this.failureReason = normalize(failureReason);
        this.updatedAt = Instant.now();
    }

    public void markManualReview(String failureReason) {
        this.status = "MANUAL_REVIEW";
        this.failureReason = normalize(failureReason);
        this.updatedAt = Instant.now();
    }

    private BigDecimal money(BigDecimal value) {
        return (value == null ? BigDecimal.ZERO : value).setScale(2, RoundingMode.HALF_UP);
    }

    private String normalizeCurrency(String value) {
        String normalized = normalize(value);
        return normalized == null ? "USD" : normalized.toUpperCase();
    }

    private String normalize(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    public UUID getId() { return id; }
    public UUID getEnrollmentId() { return enrollmentId; }
    public UUID getCheckoutAttemptId() { return checkoutAttemptId; }
    public String getStudentId() { return studentId; }
    public UUID getCourseId() { return courseId; }
    public String getStatus() { return status; }
    public BigDecimal getAmount() { return amount; }
    public String getCurrency() { return currency; }
    public String getPaymentProvider() { return paymentProvider; }
    public String getPaymentReference() { return paymentReference; }
    public String getFailureReason() { return failureReason; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public Instant getPaidAt() { return paidAt; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
