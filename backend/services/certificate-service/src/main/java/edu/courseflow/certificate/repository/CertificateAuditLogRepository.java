package edu.courseflow.certificate.repository;

import edu.courseflow.certificate.model.CertificateAuditLog;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CertificateAuditLogRepository extends JpaRepository<CertificateAuditLog, UUID> {
}
