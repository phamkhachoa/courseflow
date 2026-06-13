package edu.courseflow.course.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.course.dto.RecordItemCompletionRequestDto;
import edu.courseflow.course.service.CourseModuleService;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class LearningActivityCompletionConsumer {

    private static final Logger log = LoggerFactory.getLogger(LearningActivityCompletionConsumer.class);

    private final CourseModuleService modules;
    private final ObjectMapper objectMapper;

    public LearningActivityCompletionConsumer(CourseModuleService modules, ObjectMapper objectMapper) {
        this.modules = modules;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "quiz.attempt.graded", groupId = "course-service")
    public void onQuizAttemptGraded(String payload) throws Exception {
        completeFromEvent(payload, "QUIZ", "quizId", "gradedAt");
    }

    @KafkaListener(topics = "submission.created", groupId = "course-service")
    public void onSubmissionCreated(String payload) throws Exception {
        completeFromEvent(payload, "ASSIGNMENT", "assignmentId", "submittedAt");
    }

    @KafkaListener(topics = "submission.graded", groupId = "course-service")
    public void onSubmissionGraded(String payload) throws Exception {
        completeFromEvent(payload, "ASSIGNMENT", "assignmentId", "gradedAt");
    }

    private void completeFromEvent(String payload, String sourceType, String sourceField, String completedAtField)
            throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        String courseId = text(event, "courseId");
        String sourceId = text(event, sourceField);
        String studentId = text(event, "studentId");
        if (courseId == null || sourceId == null || studentId == null) {
            log.warn("course progress: {} event missing courseId/{}/studentId; skipping payload={}",
                    sourceType, sourceField, payload);
            return;
        }

        try {
            modules.recordVerifiedItemCompletion(
                    UUID.fromString(courseId),
                    new RecordItemCompletionRequestDto(
                            studentId,
                            sourceType,
                            sourceId,
                            parseInstant(text(event, completedAtField))));
        } catch (IllegalArgumentException ex) {
            log.warn("course progress: {} event has malformed UUIDs; skipping payload={}", sourceType, payload);
        } catch (NotFoundException | BadRequestException ex) {
            log.info("course progress: {} event did not match a published course item: {}", sourceType, ex.getMessage());
        }
    }

    private Instant parseInstant(String value) {
        if (value == null) {
            return Instant.now();
        }
        try {
            return Instant.parse(value);
        } catch (RuntimeException ex) {
            return Instant.now();
        }
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
