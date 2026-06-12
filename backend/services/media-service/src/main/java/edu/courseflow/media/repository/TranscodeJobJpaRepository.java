package edu.courseflow.media.repository;

import edu.courseflow.media.model.TranscodeJob;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TranscodeJobJpaRepository extends JpaRepository<TranscodeJob, UUID> {
}
