package edu.courseflow.gradebook.repository;

import edu.courseflow.gradebook.model.GradingSchemeEntry;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GradingSchemeEntryRepository extends JpaRepository<GradingSchemeEntry, UUID> {
    List<GradingSchemeEntry> findBySchemeIdOrderByMinPercentDesc(UUID schemeId);
}
