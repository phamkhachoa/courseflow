package edu.courseflow.certificate.repository;

import edu.courseflow.certificate.model.Certificate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CertificateRepository extends JpaRepository<Certificate, UUID> {

    boolean existsByStudentIdAndCourseIdAndStatus(String studentId, UUID courseId, String status);

    Optional<Certificate> findByStudentIdAndCourseIdAndStatus(String studentId, UUID courseId, String status);

    List<Certificate> findByStudentIdOrderByIssuedAtDesc(String studentId);
}
