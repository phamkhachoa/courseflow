package edu.courseflow.enrollment.repository;

import edu.courseflow.enrollment.model.OutboxEvent;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OutboxEventJpaRepository extends JpaRepository<OutboxEvent, UUID> {
}
