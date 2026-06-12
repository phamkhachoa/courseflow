package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.QuizQuestion;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuizQuestionRepository extends JpaRepository<QuizQuestion, UUID> {

    List<QuizQuestion> findByQuizIdOrderByPositionAsc(UUID quizId);

    Optional<QuizQuestion> findByQuizIdAndQuestionId(UUID quizId, UUID questionId);

    int countByQuizId(UUID quizId);

    long deleteByQuizIdAndQuestionId(UUID quizId, UUID questionId);
}
