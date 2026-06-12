package edu.courseflow.certificate.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.certificate.dto.CertificateVerificationDto;
import edu.courseflow.certificate.dto.IssueCertificateRequestDto;
import edu.courseflow.certificate.dto.PublicCertificateVerificationDto;
import edu.courseflow.certificate.dto.RevokeCertificateRequestDto;
import edu.courseflow.certificate.mapper.CertificateMapper;
import edu.courseflow.certificate.model.Certificate;
import edu.courseflow.certificate.model.CertificateAuditLog;
import edu.courseflow.certificate.model.CertificateVerification;
import edu.courseflow.certificate.model.OutboxEvent;
import edu.courseflow.certificate.repository.CertificateAuditLogRepository;
import edu.courseflow.certificate.repository.CertificateRepository;
import edu.courseflow.certificate.repository.CertificateVerificationRepository;
import edu.courseflow.certificate.repository.OutboxEventRepository;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CertificateService {
    private final CertificateRepository certificates;
    private final CertificateVerificationRepository verifications;
    private final CertificateAuditLogRepository auditLogs;
    private final OutboxEventRepository outboxEvents;
    private final ObjectMapper objectMapper;
    private final CertificateMapper mapper;

    public CertificateService(CertificateRepository certificates,
            CertificateVerificationRepository verifications,
            CertificateAuditLogRepository auditLogs,
            OutboxEventRepository outboxEvents,
            ObjectMapper objectMapper,
            CertificateMapper mapper) {
        this.certificates = certificates;
        this.verifications = verifications;
        this.auditLogs = auditLogs;
        this.outboxEvents = outboxEvents;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
    }

    /**
     * Full verification view including PII (student id, grade). For internal/authenticated callers only
     * (see {@code CertificateController}, which is behind the gateway). Throws {@link NotFoundException}
     * when the code is unknown so the API returns 404 rather than a 500 — previously {@code .single()}
     * threw {@code EmptyResultDataAccessException} for any bad code and surfaced as a server error.
     */
    public CertificateVerificationDto verify(String code) {
        return findByCode(code)
                .orElseThrow(() -> new NotFoundException("Certificate not found for code: " + code));
    }

    /**
     * Public verification view for the unauthenticated {@code /public/...} endpoint. Deliberately omits
     * PII (no student id, no final grade): a public verifier only needs to know the certificate is valid,
     * for which course, and when it was issued. An unknown code yields {@link NotFoundException} (404),
     * not a 500.
     */
    public PublicCertificateVerificationDto verifyPublic(String code) {
        return findByCode(code)
                .map(dto -> mapper.toPublicDto(dto, isPubliclyValid(dto)))
                .orElseThrow(() -> new NotFoundException("Certificate not found for code: " + code));
    }

    public List<CertificateVerificationDto> listMine(String studentId) {
        return certificates.findByStudentIdOrderByIssuedAtDesc(studentId).stream()
                .map(certificate -> {
                    CertificateVerification verification = verifications.findByCertificateId(certificate.getId())
                            .orElseThrow(() -> new NotFoundException(
                                    "Certificate verification not found: " + certificate.getId()));
                    return mapper.toDto(certificate, verification);
                })
                .toList();
    }

    private boolean isPubliclyValid(CertificateVerificationDto dto) {
        return "ISSUED".equalsIgnoreCase(dto.status());
    }

    private Optional<CertificateVerificationDto> findByCode(String code) {
        return verifications.findByVerificationCode(code)
                .flatMap(verification -> certificates.findById(verification.getCertificateId())
                        .map(certificate -> mapper.toDto(certificate, verification)));
    }

    @Transactional
    public CertificateVerificationDto issue(IssueCertificateRequestDto request) {
        UUID courseId = UUID.fromString(request.courseId());
        Optional<Certificate> existing = certificates.findByStudentIdAndCourseIdAndStatus(
                request.studentId(), courseId, "ISSUED");
        if (existing.isPresent()) {
            Certificate certificate = existing.get();
            CertificateVerification verification = verifications.findByCertificateId(certificate.getId())
                    .orElseThrow(() -> new NotFoundException(
                            "Certificate verification not found: " + certificate.getId()));
            return mapper.toDto(certificate, verification);
        }

        UUID certificateId = UUID.randomUUID();
        String code = "CF-" + UUID.randomUUID().toString().replace("-", "").toUpperCase();
        String signature = sign(certificateId + ":" + request.studentId() + ":" + request.courseId() + ":" + request.finalGrade());
        String publicSlug = code.toLowerCase();

        certificates.save(new Certificate(certificateId, request.studentId(), courseId, request.finalGrade()));
        verifications.save(new CertificateVerification(certificateId, code, signature, publicSlug));
        audit(certificateId, "ISSUED", request.actorId(), "Certificate issued from final grade");
        outbox(certificateId, "certificate.issued", Map.of(
                "eventId", UUID.randomUUID().toString(),
                "certificateId", certificateId.toString(),
                "studentId", request.studentId(),
                "courseId", request.courseId(),
                "finalGrade", request.finalGrade(),
                "verificationCode", code));
        return verify(code);
    }

    @Transactional
    public CertificateVerificationDto revoke(UUID certificateId, String actorId, String reason) {
        Certificate certificate = certificates.findById(certificateId)
                .orElseThrow(() -> new NotFoundException("Certificate not found: " + certificateId));
        certificate.revoke();
        certificates.save(certificate);
        audit(certificateId, "REVOKED", actorId, reason);
        CertificateVerification verification = verifications.findByCertificateId(certificateId)
                .orElseThrow(() -> new NotFoundException("Certificate verification not found: " + certificateId));
        return mapper.toDto(certificate, verification);
    }

    private void audit(UUID certificateId, String action, String actorId, String reason) {
        auditLogs.save(new CertificateAuditLog(certificateId, action, actorId, reason));
    }

    private void outbox(UUID aggregateId, String eventType, Map<String, ?> payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "certificate", eventType, toJson(payload)));
    }

    private String sign(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            return HexFormat.of().formatHex(digest.digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
