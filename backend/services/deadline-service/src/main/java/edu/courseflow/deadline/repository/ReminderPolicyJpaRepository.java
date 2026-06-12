package edu.courseflow.deadline.repository;

import edu.courseflow.deadline.model.ReminderPolicy;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ReminderPolicyJpaRepository extends JpaRepository<ReminderPolicy, UUID> {

    List<ReminderPolicy> findAllByOrderByNameAsc();

    List<ReminderPolicy> findByCourseIdOrderByNameAsc(UUID courseId);
}
