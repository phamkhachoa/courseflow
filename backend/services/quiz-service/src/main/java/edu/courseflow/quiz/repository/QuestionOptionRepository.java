package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.QuestionOption;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuestionOptionRepository extends JpaRepository<QuestionOption, UUID> {

    List<QuestionOption> findByQuestionIdOrderByLabelAsc(UUID questionId);

    long deleteByQuestionId(UUID questionId);
}
