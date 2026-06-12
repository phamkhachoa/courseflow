package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.QuizAnswer;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuizAnswerRepository extends JpaRepository<QuizAnswer, UUID> {

    Optional<QuizAnswer> findByAttemptIdAndQuestionId(UUID attemptId, UUID questionId);

    List<QuizAnswer> findByAttemptId(UUID attemptId);
}
