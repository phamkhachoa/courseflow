package edu.courseflow.organization.repository;

import edu.courseflow.organization.model.Department;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DepartmentJpaRepository extends JpaRepository<Department, UUID> {

    List<Department> findAllByOrderByCodeAsc();
}
