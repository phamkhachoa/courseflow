package edu.courseflow.portfolio.repository;

import edu.courseflow.portfolio.model.LearningEvidence;
import java.util.List;
import java.util.Optional;
import org.springframework.data.mongodb.repository.MongoRepository;

public interface LearningEvidenceRepository extends MongoRepository<LearningEvidence, String> {

    List<LearningEvidence> findByStudentIdOrderByCreatedAtDesc(String studentId);

    List<LearningEvidence> findByStudentIdAndCourseIdOrderByCreatedAtDesc(String studentId, String courseId);

    List<LearningEvidence> findByCourseIdOrderByCreatedAtDesc(String courseId);

    Optional<LearningEvidence> findByIdAndStudentId(String id, String studentId);

    Optional<LearningEvidence> findByStudentIdAndSourceTypeAndSourceId(String studentId, String sourceType, String sourceId);
}
