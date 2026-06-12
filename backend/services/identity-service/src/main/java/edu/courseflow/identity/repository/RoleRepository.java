package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.Role;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RoleRepository extends JpaRepository<Role, UUID> {

    boolean existsByCode(String code);

    Optional<Role> findByCode(String code);

    List<Role> findAllByOrderBySystemDescCodeAsc();

    @EntityGraph(attributePaths = "parentRole")
    Optional<Role> findWithParentRoleById(UUID id);
}
