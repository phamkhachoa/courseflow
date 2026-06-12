package edu.courseflow.quiz.repository;

import edu.courseflow.quiz.model.QuestionBank;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface QuestionBankRepository extends JpaRepository<QuestionBank, UUID> {

    Optional<QuestionBank> findFirstByCourseIdOrderByCreatedAtAsc(UUID courseId);
}
