package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.QuizAttempt;
import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface QuizAttemptRepository extends JpaRepository<QuizAttempt, UUID> {

    boolean existsByQuizIdAndStudentIdAndStatus(UUID quizId, String studentId, String status);

    boolean existsByQuizId(UUID quizId);

    List<QuizAttempt> findByQuizIdOrderByStartedAtDesc(UUID quizId);

    List<QuizAttempt> findByQuizIdAndStudentIdOrderByAttemptNoDesc(UUID quizId, String studentId);

    List<QuizAttempt> findByQuizIdInAndStudentIdOrderByStartedAtDesc(Collection<UUID> quizIds, String studentId);

    Optional<QuizAttempt> findFirstByQuizIdAndStudentIdAndStatusInOrderByStartedAtDesc(
            UUID quizId, String studentId, Collection<String> statuses);

    List<QuizAttempt> findByQuizIdAndStudentIdAndStatusOrderByAttemptNoAsc(
            UUID quizId, String studentId, String status);

    long countByQuizIdAndStudentId(UUID quizId, String studentId);

    long countByQuizIdAndStudentIdAndStatusIn(UUID quizId, String studentId, Collection<String> statuses);

    boolean existsByQuizIdAndStudentIdAndStatusIn(UUID quizId, String studentId, Collection<String> statuses);

    List<QuizAttempt> findByStatusAndDeadlineAtLessThanEqualOrderByDeadlineAtAsc(String status, Instant deadlineAt);

    @Query("select coalesce(max(a.attemptNo), 0) + 1 from QuizAttempt a "
            + "where a.quizId = :quizId and a.studentId = :studentId")
    int nextAttemptNo(@Param("quizId") UUID quizId, @Param("studentId") String studentId);
}
