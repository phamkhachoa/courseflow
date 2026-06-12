package edu.courseflow.portfolio.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "learning_evidence")
@CompoundIndex(name = "uq_evidence_source",
        def = "{'studentId': 1, 'sourceType': 1, 'sourceId': 1}",
        unique = true,
        partialFilter = "{'sourceType': {'$exists': true}, 'sourceId': {'$exists': true}}")
public class LearningEvidence {

    @Id
    private String id;

    @Indexed
    private String studentId;

    @Indexed
    private String courseId;

    private String title;
    private String evidenceType;
    private String sourceType;
    private String sourceId;
    private String reflection;
    private Instant createdAt;

    // New fields
    private List<String> tags;
    private String visibility; // PRIVATE | INSTRUCTOR | PUBLIC
    private List<String> mediaUrls;
    private Instant updatedAt;
    private List<EvidenceEvaluation> evaluations;

    // Existing getters and setters
    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getStudentId() {
        return studentId;
    }

    public void setStudentId(String studentId) {
        this.studentId = studentId;
    }

    public String getCourseId() {
        return courseId;
    }

    public void setCourseId(String courseId) {
        this.courseId = courseId;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getEvidenceType() {
        return evidenceType;
    }

    public void setEvidenceType(String evidenceType) {
        this.evidenceType = evidenceType;
    }

    public String getSourceType() {
        return sourceType;
    }

    public void setSourceType(String sourceType) {
        this.sourceType = sourceType;
    }

    public String getSourceId() {
        return sourceId;
    }

    public void setSourceId(String sourceId) {
        this.sourceId = sourceId;
    }

    public String getReflection() {
        return reflection;
    }

    public void setReflection(String reflection) {
        this.reflection = reflection;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    // New getters and setters
    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public String getVisibility() {
        return visibility;
    }

    public void setVisibility(String visibility) {
        this.visibility = visibility;
    }

    public List<String> getMediaUrls() {
        return mediaUrls;
    }

    public void setMediaUrls(List<String> mediaUrls) {
        this.mediaUrls = mediaUrls;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    public List<EvidenceEvaluation> getEvaluations() {
        return evaluations;
    }

    public void setEvaluations(List<EvidenceEvaluation> evaluations) {
        this.evaluations = evaluations;
    }

    // Inner static class embedded in MongoDB document
    public static class EvidenceEvaluation {
        private String evaluatorId;
        private String evaluatorRole; // INSTRUCTOR | PEER | SELF
        private BigDecimal score;
        private String comment;
        private Instant evaluatedAt;

        public String getEvaluatorId() {
            return evaluatorId;
        }

        public void setEvaluatorId(String evaluatorId) {
            this.evaluatorId = evaluatorId;
        }

        public String getEvaluatorRole() {
            return evaluatorRole;
        }

        public void setEvaluatorRole(String evaluatorRole) {
            this.evaluatorRole = evaluatorRole;
        }

        public BigDecimal getScore() {
            return score;
        }

        public void setScore(BigDecimal score) {
            this.score = score;
        }

        public String getComment() {
            return comment;
        }

        public void setComment(String comment) {
            this.comment = comment;
        }

        public Instant getEvaluatedAt() {
            return evaluatedAt;
        }

        public void setEvaluatedAt(Instant evaluatedAt) {
            this.evaluatedAt = evaluatedAt;
        }
    }
}
