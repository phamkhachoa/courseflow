package edu.courseflow.promotion.repository;

import edu.courseflow.promotion.model.IncentiveRestoreDrill;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IncentiveRestoreDrillRepository extends JpaRepository<IncentiveRestoreDrill, UUID> {
    Optional<IncentiveRestoreDrill> findByRestoreDrillRef(String restoreDrillRef);
}
