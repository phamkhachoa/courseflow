package edu.courseflow.certificate.repository;

import edu.courseflow.certificate.model.CertificateVerification;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CertificateVerificationRepository extends JpaRepository<CertificateVerification, UUID> {

    Optional<CertificateVerification> findByVerificationCode(String verificationCode);

    Optional<CertificateVerification> findByCertificateId(UUID certificateId);
}
