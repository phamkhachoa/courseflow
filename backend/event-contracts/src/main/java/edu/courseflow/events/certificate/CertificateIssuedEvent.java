package edu.courseflow.events.certificate;

import edu.courseflow.events.common.CourseFlowEvent;
import edu.courseflow.events.common.EventMetadata;

import java.math.BigDecimal;
import java.time.Instant;

public record CertificateIssuedEvent(
        String eventId,
        String certificateId,
        String courseId,
        String studentId,
        BigDecimal finalGrade,
        String verificationCode,
        Instant issuedAt,
        EventMetadata metadata
) implements CourseFlowEvent {
    @Override
    public String eventType() {
        return "certificate.issued";
    }

    @Override
    public String aggregateId() {
        return certificateId;
    }

    @Override
    public String aggregateType() {
        return "certificate";
    }

    @Override
    public Instant occurredAt() {
        return issuedAt;
    }
}
