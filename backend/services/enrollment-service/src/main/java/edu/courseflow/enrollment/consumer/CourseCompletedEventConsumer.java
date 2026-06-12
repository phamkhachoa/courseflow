package edu.courseflow.enrollment.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.enrollment.model.ProcessedEvent;
import edu.courseflow.enrollment.repository.ProcessedEventRepository;
import edu.courseflow.enrollment.service.EnrollmentService;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Consumes {@code course.completed} events emitted by course-service and auto-transitions every
 * affected student's ACTIVE enrollment to COMPLETED.
 *
 * <p>The dedup insert into {@code processed_events} and the completion both share one transaction,
 * so any failure rolls back the processed_events row and the event is retried (and ultimately routed
 * to the DLT by {@code KafkaErrorHandlingConfig}). Malformed payloads are skipped with a log rather
 * than thrown, so a data-shape problem never becomes an un-skippable poison message.
 *
 * <p>The event may carry a single {@code studentId} (per-student completion) and/or a
 * {@code studentIds} array (whole-course completion); both shapes are handled.
 */
@Component
public class CourseCompletedEventConsumer {
    private static final Logger log = LoggerFactory.getLogger(CourseCompletedEventConsumer.class);
    private static final String CONSUMER = "enrollment:course.completed";

    private final EnrollmentService enrollmentService;
    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;

    public CourseCompletedEventConsumer(EnrollmentService enrollmentService,
            ProcessedEventRepository processedEvents,
            ObjectMapper objectMapper) {
        this.enrollmentService = enrollmentService;
        this.processedEvents = processedEvents;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "course.completed", groupId = "enrollment-service")
    @Transactional
    public void onCourseCompleted(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);

        String eventIdText = text(event, "eventId");
        if (eventIdText == null) {
            log.warn("enrollment: course.completed event missing eventId; skipping payload={}", payload);
            return;
        }
        UUID eventId;
        try {
            eventId = UUID.fromString(eventIdText);
        } catch (IllegalArgumentException ex) {
            log.warn("enrollment: course.completed event has non-UUID eventId '{}'; skipping", eventIdText);
            return;
        }

        String courseIdText = text(event, "courseId");
        if (courseIdText == null) {
            log.warn("enrollment: course.completed event {} missing courseId; skipping", eventId);
            return;
        }
        UUID courseId;
        try {
            courseId = UUID.fromString(courseIdText);
        } catch (IllegalArgumentException ex) {
            log.warn("enrollment: course.completed event {} has non-UUID courseId '{}'; skipping", eventId, courseIdText);
            return;
        }

        if (alreadyProcessed(eventId)) {
            return; // already processed
        }

        int completed = 0;
        String singleStudent = text(event, "studentId");
        if (singleStudent != null) {
            if (enrollmentService.completeForCourseCompletion(singleStudent, courseId).isPresent()) {
                completed++;
            }
        }
        JsonNode studentIds = event.get("studentIds");
        if (studentIds != null && studentIds.isArray()) {
            for (JsonNode node : studentIds) {
                if (node == null || node.isNull()) {
                    continue;
                }
                String studentId = node.asText();
                if (studentId.isBlank()) {
                    continue;
                }
                if (enrollmentService.completeForCourseCompletion(studentId, courseId).isPresent()) {
                    completed++;
                }
            }
        }
        log.info("enrollment: course.completed event {} for course {} -> {} enrollment(s) completed",
                eventId, courseId, completed);
    }

    /** Read a text field, returning null when absent or JSON null (no NPE on missing keys). */
    private static String text(JsonNode node, String field) {
        JsonNode value = node.get(field);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return text.isBlank() ? null : text;
    }

    private boolean alreadyProcessed(UUID eventId) {
        if (processedEvents.existsById(eventId)) {
            return true;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, CONSUMER));
            return false;
        } catch (DataIntegrityViolationException duplicate) {
            return true;
        }
    }
}
