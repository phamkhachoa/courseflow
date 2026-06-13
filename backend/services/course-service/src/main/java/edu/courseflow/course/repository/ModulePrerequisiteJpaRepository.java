package edu.courseflow.course.repository;

import edu.courseflow.course.model.ModulePrerequisite;
import java.util.Collection;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ModulePrerequisiteJpaRepository extends JpaRepository<ModulePrerequisite, UUID> {

    List<ModulePrerequisite> findByModuleId(UUID moduleId);

    List<ModulePrerequisite> findByModuleIdIn(Collection<UUID> moduleIds);
}
