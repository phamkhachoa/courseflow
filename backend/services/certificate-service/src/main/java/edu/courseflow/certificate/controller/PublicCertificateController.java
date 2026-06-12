package edu.courseflow.certificate.controller;

import edu.courseflow.certificate.dto.PublicCertificateVerificationDto;
import edu.courseflow.certificate.service.CertificateService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PublicCertificateController {

    private final CertificateService certificates;

    public PublicCertificateController(CertificateService certificates) {
        this.certificates = certificates;
    }

    /**
     * Unauthenticated verification. Returns a PII-free view (no student id, no grade) and 404 for an
     * unknown code instead of leaking data or 500-ing.
     */
    @GetMapping("/public/certificates/verify/{code}")
    public PublicCertificateVerificationDto verify(@PathVariable String code) {
        return certificates.verifyPublic(code);
    }
}
