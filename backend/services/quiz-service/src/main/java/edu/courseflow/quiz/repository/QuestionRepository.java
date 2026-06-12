package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.Question;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuestionRepository extends JpaRepository<Question, UUID> {
}
