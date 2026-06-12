package edu.courseflow.certificate.controller;

import edu.courseflow.certificate.service.CertificateService;
import edu.courseflow.certificate.dto.CertificateVerificationDto;
import edu.courseflow.certificate.dto.IssueCertificateRequestDto;
import edu.courseflow.certificate.dto.RevokeCertificateRequestDto;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/internal/certificates")
public class CertificateController {

    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_INSTRUCTOR = "INSTRUCTOR";

    private final CertificateService certificates;

    public CertificateController(CertificateService certificates) {
        this.certificates = certificates;
    }

    @GetMapping("/verify/{code}")
    public CertificateVerificationDto verify(@PathVariable String code, CurrentUser user) {
        CertificateVerificationDto certificate = certificates.verify(code);
        boolean owner = user != null && user.id() != null
                && String.valueOf(user.id()).equals(certificate.studentId());
        if (!owner) {
            requirePrivileged(user);
        }
        return certificate;
    }

    @GetMapping("/mine")
    public List<CertificateVerificationDto> mine(CurrentUser user) {
        return certificates.listMine(authenticatedActorId(user));
    }

    /**
     * Issue a certificate. Restricted to ADMIN/INSTRUCTOR. The acting identity is taken from the gateway
     * headers ({@link CurrentUser}), never from the request body, so the audit trail cannot be forged.
     */
    @PostMapping("/issue")
    public CertificateVerificationDto issue(@Valid @RequestBody IssueCertificateRequestDto request,
                                            CurrentUser user) {
        requirePrivileged(user);
        IssueCertificateRequestDto trusted = new IssueCertificateRequestDto(
                request.studentId(), request.courseId(), request.finalGrade(), actorId(user));
        return certificates.issue(trusted);
    }

    /**
     * Revoke a certificate. Restricted to ADMIN/INSTRUCTOR. The actor id comes from the token, not the
     * body — the body only carries the reason.
     */
    @PostMapping("/{certificateId}/revoke")
    public CertificateVerificationDto revoke(@PathVariable UUID certificateId,
                                             @Valid @RequestBody RevokeCertificateRequestDto request,
                                             CurrentUser user) {
        requirePrivileged(user);
        return certificates.revoke(certificateId, actorId(user), request.reason());
    }

    private void requirePrivileged(CurrentUser user) {
        if (user == null || user.id() == null || !user.hasAnyRole(ROLE_ADMIN, ROLE_INSTRUCTOR)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,
                    "Only ADMIN or INSTRUCTOR may issue or revoke certificates");
        }
    }

    private String actorId(CurrentUser user) {
        return String.valueOf(user.id());
    }

    private String authenticatedActorId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated user required");
        }
        return String.valueOf(user.id());
    }
}
