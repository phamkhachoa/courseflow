package edu.courseflow.organization.repository;

import edu.courseflow.organization.model.AcademicTerm;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AcademicTermJpaRepository extends JpaRepository<AcademicTerm, UUID> {

    List<AcademicTerm> findAllByOrderByStartDateDesc();
}
