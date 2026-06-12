package edu.courseflow.certificate.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "certificate_verifications")
public class CertificateVerification {

    @Id
    private UUID id;

    @Column(name = "certificate_id", nullable = false)
    private UUID certificateId;

    @Column(name = "verification_code", nullable = false, unique = true, length = 120)
    private String verificationCode;

    @Column(nullable = false)
    private String signature;

    @Column(name = "public_slug", nullable = false, unique = true)
    private String publicSlug;

    protected CertificateVerification() {
    }

    public CertificateVerification(UUID certificateId, String verificationCode, String signature, String publicSlug) {
        this.id = UUID.randomUUID();
        this.certificateId = certificateId;
        this.verificationCode = verificationCode;
        this.signature = signature;
        this.publicSlug = publicSlug;
    }

    public UUID getCertificateId() { return certificateId; }
    public String getVerificationCode() { return verificationCode; }
    public String getPublicSlug() { return publicSlug; }
}
