package edu.courseflow.certificate.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.certificate.dto.CertificateEligibilityDto;
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
import jakarta.annotation.PostConstruct;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CertificateService {
    private static final String SIGNATURE_VERSION = "v1";
    private static final String SIGNATURE_ALGORITHM = "HmacSHA256";

    private final CertificateRepository certificates;
    private final CertificateVerificationRepository verifications;
    private final CertificateAuditLogRepository auditLogs;
    private final OutboxEventRepository outboxEvents;
    private final ObjectMapper objectMapper;
    private final CertificateMapper mapper;
    private final CertificateEligibilityClient eligibilityClient;
    private final String signingSecret;

    public CertificateService(CertificateRepository certificates,
            CertificateVerificationRepository verifications,
            CertificateAuditLogRepository auditLogs,
            OutboxEventRepository outboxEvents,
            ObjectMapper objectMapper,
            CertificateMapper mapper,
            CertificateEligibilityClient eligibilityClient,
            @Value("${courseflow.certificate.signing-secret:}") String signingSecret) {
        this.certificates = certificates;
        this.verifications = verifications;
        this.auditLogs = auditLogs;
        this.outboxEvents = outboxEvents;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
        this.eligibilityClient = eligibilityClient;
        this.signingSecret = signingSecret == null ? "" : signingSecret.trim();
    }

    @PostConstruct
    void validateSigningSecret() {
        if (signingSecret.isBlank()) {
            throw new IllegalStateException("courseflow.certificate.signing-secret must be configured");
        }
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

    public CertificateEligibilityDto eligibility(String studentId, UUID courseId) {
        CertificateEligibilityDto base = eligibilityClient.evaluate(studentId, courseId);
        Optional<Certificate> issued = certificates.findByStudentIdAndCourseIdAndStatus(studentId, courseId, "ISSUED");
        if (issued.isEmpty()) {
            return base;
        }
        Certificate certificate = issued.get();
        CertificateVerification verification = verifications.findByCertificateId(certificate.getId())
                .orElseThrow(() -> new NotFoundException(
                        "Certificate verification not found: " + certificate.getId()));
        return new CertificateEligibilityDto(
                base.generatedAt(),
                courseId.toString(),
                studentId,
                true,
                "ISSUED",
                true,
                true,
                true,
                true,
                certificate.getFinalGrade(),
                base.gradeThreshold(),
                base.finalGradeStatus(),
                certificate.getId().toString(),
                verification.getVerificationCode(),
                certificate.getIssuedAt(),
                List.of());
    }

    private boolean isPubliclyValid(CertificateVerificationDto dto) {
        return "ISSUED".equalsIgnoreCase(dto.status());
    }

    private Optional<CertificateVerificationDto> findByCode(String code) {
        return verifications.findByVerificationCode(code)
                .flatMap(verification -> certificates.findById(verification.getCertificateId())
                        .filter(certificate -> hasValidSignature(certificate, verification))
                        .map(certificate -> mapper.toDto(certificate, verification)));
    }

    @Transactional
    public CertificateVerificationDto issue(IssueCertificateRequestDto request) {
        UUID courseId = UUID.fromString(request.courseId());
        BigDecimal finalGrade = eligibilityClient
                .requireEligible(request.studentId(), courseId, request.finalGrade())
                .finalScore();
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
        String signature = sign(certificateId, code, request.studentId(), courseId, finalGrade);
        String publicSlug = code.toLowerCase();

        certificates.save(new Certificate(certificateId, request.studentId(), courseId, finalGrade));
        verifications.save(new CertificateVerification(certificateId, code, signature, publicSlug));
        audit(certificateId, "ISSUED", request.actorId(), "Certificate issued from final grade");
        outbox(certificateId, "certificate.issued", Map.of(
                "eventId", UUID.randomUUID().toString(),
                "certificateId", certificateId.toString(),
                "studentId", request.studentId(),
                "courseId", request.courseId(),
                "finalGrade", finalGrade,
                "verificationCode", code));
        return verify(code);
    }

    public UUID courseIdForCertificate(UUID certificateId) {
        return certificates.findById(certificateId)
                .map(Certificate::getCourseId)
                .orElseThrow(() -> new NotFoundException("Certificate not found: " + certificateId));
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

    private boolean hasValidSignature(Certificate certificate, CertificateVerification verification) {
        if (verification.getSignature() == null || verification.getSignature().isBlank()) {
            return false;
        }
        String expected = sign(
                certificate.getId(),
                verification.getVerificationCode(),
                certificate.getStudentId(),
                certificate.getCourseId(),
                certificate.getFinalGrade());
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                verification.getSignature().getBytes(StandardCharsets.UTF_8));
    }

    private String sign(UUID certificateId, String verificationCode, String studentId, UUID courseId, BigDecimal finalGrade) {
        try {
            Mac mac = Mac.getInstance(SIGNATURE_ALGORITHM);
            mac.init(new SecretKeySpec(signingSecret.getBytes(StandardCharsets.UTF_8), SIGNATURE_ALGORITHM));
            return SIGNATURE_VERSION + ":" + HexFormat.of().formatHex(mac.doFinal(signingPayload(
                    certificateId,
                    verificationCode,
                    studentId,
                    courseId,
                    finalGrade).getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("Unable to sign certificate", ex);
        }
    }

    private String signingPayload(UUID certificateId, String verificationCode, String studentId,
                                  UUID courseId, BigDecimal finalGrade) {
        return String.join("\n",
                "courseflow-certificate",
                SIGNATURE_VERSION,
                certificateId.toString(),
                verificationCode,
                studentId,
                courseId.toString(),
                finalGrade.toPlainString());
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
