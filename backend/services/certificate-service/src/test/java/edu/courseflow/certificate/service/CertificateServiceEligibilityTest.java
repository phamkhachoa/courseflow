package edu.courseflow.certificate.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.certificate.dto.CertificateVerificationDto;
import edu.courseflow.certificate.dto.IssueCertificateRequestDto;
import edu.courseflow.certificate.mapper.CertificateMapper;
import edu.courseflow.certificate.model.Certificate;
import edu.courseflow.certificate.model.CertificateVerification;
import edu.courseflow.certificate.repository.CertificateAuditLogRepository;
import edu.courseflow.certificate.repository.CertificateRepository;
import edu.courseflow.certificate.repository.CertificateVerificationRepository;
import edu.courseflow.certificate.repository.OutboxEventRepository;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import java.math.BigDecimal;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CertificateServiceEligibilityTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");

    @Mock
    private CertificateRepository certificates;
    @Mock
    private CertificateVerificationRepository verifications;
    @Mock
    private CertificateAuditLogRepository auditLogs;
    @Mock
    private OutboxEventRepository outboxEvents;
    @Mock
    private CertificateMapper mapper;
    @Mock
    private CertificateEligibilityClient eligibilityClient;

    private CertificateService service;

    @BeforeEach
    void setUp() {
        service = new CertificateService(
                certificates,
                verifications,
                auditLogs,
                outboxEvents,
                new ObjectMapper(),
                mapper,
                eligibilityClient,
                "certificate-signing-secret-for-tests");
    }

    @Test
    void issueUsesFinalizedEligibleGradeInsteadOfTrustingRequestBodyGrade() {
        BigDecimal requestGrade = new BigDecimal("100.00");
        BigDecimal finalizedGrade = new BigDecimal("91.50");
        IssueCertificateRequestDto request = new IssueCertificateRequestDto(
                "4", COURSE_ID.toString(), requestGrade, "9");
        AtomicReference<Certificate> savedCertificate = new AtomicReference<>();
        AtomicReference<CertificateVerification> savedVerification = new AtomicReference<>();

        when(eligibilityClient.requireEligible("4", COURSE_ID, requestGrade))
                .thenReturn(new CertificateEligibilityClient.Eligibility(finalizedGrade));
        when(certificates.findByStudentIdAndCourseIdAndStatus("4", COURSE_ID, "ISSUED"))
                .thenReturn(Optional.empty());
        when(certificates.save(any(Certificate.class))).thenAnswer(invocation -> {
            Certificate certificate = invocation.getArgument(0);
            savedCertificate.set(certificate);
            return certificate;
        });
        when(verifications.save(any(CertificateVerification.class))).thenAnswer(invocation -> {
            CertificateVerification verification = invocation.getArgument(0);
            savedVerification.set(verification);
            return verification;
        });
        when(verifications.findByVerificationCode(any())).thenAnswer(invocation ->
                Optional.ofNullable(savedVerification.get()));
        when(certificates.findById(any())).thenAnswer(invocation ->
                Optional.ofNullable(savedCertificate.get()));
        when(mapper.toDto(any(Certificate.class), any(CertificateVerification.class))).thenAnswer(invocation -> {
            Certificate certificate = invocation.getArgument(0);
            CertificateVerification verification = invocation.getArgument(1);
            return new CertificateVerificationDto(
                    certificate.getId().toString(),
                    verification.getVerificationCode(),
                    verification.getPublicSlug(),
                    certificate.getStudentId(),
                    certificate.getCourseId().toString(),
                    certificate.getFinalGrade(),
                    certificate.getStatus(),
                    certificate.getIssuedAt());
        });

        CertificateVerificationDto issued = service.issue(request);

        assertThat(savedCertificate.get().getFinalGrade()).isEqualByComparingTo(finalizedGrade);
        assertThat(savedVerification.get().getSignature()).startsWith("v1:");
        assertThat(issued.finalGrade()).isEqualByComparingTo(finalizedGrade);
        verify(eligibilityClient).requireEligible("4", COURSE_ID, requestGrade);
    }

    @Test
    void verifyRejectsCertificateWithTamperedSignature() {
        UUID certificateId = UUID.fromString("70000000-0000-0000-0000-000000000001");
        Certificate certificate = new Certificate(certificateId, "4", COURSE_ID, new BigDecimal("91.50"));
        CertificateVerification verification = new CertificateVerification(
                certificateId,
                "CF-TAMPERED",
                "v1:not-a-real-signature",
                "cf-tampered");
        when(verifications.findByVerificationCode("CF-TAMPERED")).thenReturn(Optional.of(verification));
        when(certificates.findById(certificateId)).thenReturn(Optional.of(certificate));

        assertThrows(NotFoundException.class, () -> service.verify("CF-TAMPERED"));

        verify(mapper, never()).toDto(any(Certificate.class), any(CertificateVerification.class));
    }
}
