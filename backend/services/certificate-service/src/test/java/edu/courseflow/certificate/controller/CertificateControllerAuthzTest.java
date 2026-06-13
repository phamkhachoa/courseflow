package edu.courseflow.certificate.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.certificate.dto.CertificateEligibilityDto;
import edu.courseflow.certificate.dto.CertificateVerificationDto;
import edu.courseflow.certificate.dto.IssueCertificateRequestDto;
import edu.courseflow.certificate.dto.RevokeCertificateRequestDto;
import edu.courseflow.certificate.service.CertificateService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class CertificateControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID CERTIFICATE_ID = UUID.fromString("70000000-0000-0000-0000-000000000001");

    @Mock
    private CertificateService certificates;
    @Mock
    private CourseAccessClient courseAccess;

    private CertificateController controller;

    @BeforeEach
    void setUp() {
        controller = new CertificateController(certificates, courseAccess);
    }

    @Test
    void issueRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        IssueCertificateRequestDto request = new IssueCertificateRequestDto(
                "4", COURSE_ID.toString(), new BigDecimal("91.50"), null);
        when(certificates.issue(new IssueCertificateRequestDto(
                "4", COURSE_ID.toString(), new BigDecimal("91.50"), "9"))).thenReturn(certificate("4"));

        controller.issue(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void revokeRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(certificates.courseIdForCertificate(CERTIFICATE_ID)).thenReturn(COURSE_ID);
        when(certificates.revoke(CERTIFICATE_ID, "9", "Academic integrity review")).thenReturn(certificate("4"));

        controller.revoke(CERTIFICATE_ID, new RevokeCertificateRequestDto("Academic integrity review"), instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void nonOwnerVerifyRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(certificates.verify("CF-VERIFY")).thenReturn(certificate("4"));

        controller.verify("CF-VERIFY", instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void ownerCanReadEligibilityWithoutStaffAccess() {
        CurrentUser learner = new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
        when(certificates.eligibility("4", COURSE_ID)).thenReturn(new CertificateEligibilityDto(
                Instant.parse("2026-06-13T00:00:00Z"),
                COURSE_ID.toString(),
                "4",
                false,
                "FINAL_GRADE_NOT_FINALIZED",
                true,
                false,
                true,
                false,
                null,
                new BigDecimal("60.00"),
                null,
                null,
                null,
                null,
                List.of()));

        controller.eligibility(COURSE_ID, "4", learner);

        verifyNoInteractions(courseAccess);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static CertificateVerificationDto certificate(String studentId) {
        return new CertificateVerificationDto(
                CERTIFICATE_ID.toString(),
                "CF-VERIFY",
                "cf-verify",
                studentId,
                COURSE_ID.toString(),
                new BigDecimal("91.50"),
                "ISSUED",
                Instant.parse("2026-06-13T00:00:00Z"));
    }
}
