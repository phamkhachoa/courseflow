package edu.courseflow.portfolio.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.portfolio.mapper.PortfolioMapper;
import edu.courseflow.portfolio.model.LearningEvidence;
import edu.courseflow.portfolio.repository.LearningEvidenceRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * Auto-captures a learning-evidence entry whenever a student makes a submission
 * (Portfolium-style auto-capture) by consuming {@code submission.created} events.
 *
 * <p>Kafka delivery is at-least-once, so this listener may receive the same event
 * more than once. Rather than relying on a dedup table, idempotency is achieved
 * with a natural key: an evidence row is uniquely identified by
 * {@code (studentId, sourceType=ASSIGNMENT_SUBMISSION, sourceId=submissionId)}.
 * On each event we find-or-create against that key, so redelivery is safe and
 * never produces duplicate evidence.
 */
@Component
public class SubmissionEvidenceConsumer {

    private static final Logger log = LoggerFactory.getLogger(SubmissionEvidenceConsumer.class);
    private static final String SOURCE_TYPE = "ASSIGNMENT_SUBMISSION";

    private final LearningEvidenceRepository repository;
    private final PortfolioMapper mapper;
    private final ObjectMapper objectMapper;

    public SubmissionEvidenceConsumer(LearningEvidenceRepository repository,
            PortfolioMapper mapper,
            ObjectMapper objectMapper) {
        this.repository = repository;
        this.mapper = mapper;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "submission.created", groupId = "portfolio-service")
    public void onSubmissionCreated(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        String studentId = text(event, "studentId");
        String submissionId = text(event, "submissionId");
        String courseId = text(event, "courseId");
        String assignmentId = text(event, "assignmentId");
        if (studentId == null || submissionId == null || courseId == null || assignmentId == null) {
            log.warn("portfolio: submission.created missing required fields; skipping payload={}", payload);
            return;
        }

        if (repository.findByStudentIdAndSourceTypeAndSourceId(studentId, SOURCE_TYPE, submissionId).isPresent()) {
            log.debug("Evidence already exists for student={} submission={}, skipping", studentId, submissionId);
            return;
        }

        LearningEvidence evidence = mapper.toSubmissionEvidence(studentId, courseId, assignmentId, submissionId);
        repository.save(evidence);
        log.info("Auto-captured learning evidence for student={} submission={}", studentId, submissionId);
    }

    private static String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return text.isBlank() ? null : text;
    }
}
