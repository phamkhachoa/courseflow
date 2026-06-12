package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.Permission;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PermissionRepository extends JpaRepository<Permission, String> {

    List<Permission> findAllByOrderByCategoryAscCodeAsc();
}
