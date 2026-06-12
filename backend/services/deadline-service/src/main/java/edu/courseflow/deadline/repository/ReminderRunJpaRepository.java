package edu.courseflow.deadline.repository;

import edu.courseflow.deadline.model.ReminderRun;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ReminderRunJpaRepository extends JpaRepository<ReminderRun, UUID> {

    Optional<ReminderRun> findByAssignmentIdAndStudentIdAndReminderPolicyId(
            UUID assignmentId, String studentId, UUID reminderPolicyId);

    List<ReminderRun> findByStatusAndReminderAtLessThanEqualOrderByReminderAtAsc(String status, Instant now);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select r from ReminderRun r where r.id = :id and r.status = 'PENDING' and r.reminderAt <= :now")
    Optional<ReminderRun> lockDuePending(@Param("id") UUID id, @Param("now") Instant now);
}
