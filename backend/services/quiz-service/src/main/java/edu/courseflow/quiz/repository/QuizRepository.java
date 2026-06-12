package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.Quiz;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuizRepository extends JpaRepository<Quiz, UUID> {

    List<Quiz> findByCourseIdOrderByTitleAsc(UUID courseId);
}
