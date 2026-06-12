package edu.courseflow.analytics.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateCourseMetricRequestDto;
import edu.courseflow.analytics.model.ProcessedEvent;
import edu.courseflow.analytics.repository.AnalyticsRepository;
import edu.courseflow.analytics.repository.ProcessedEventRepository;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class SubmissionEventConsumer {
    private static final Logger log = LoggerFactory.getLogger(SubmissionEventConsumer.class);
    private static final String CONSUMER = "analytics:submission.created";

    private final AnalyticsRepository analytics;
    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;

    public SubmissionEventConsumer(AnalyticsRepository analytics,
            ProcessedEventRepository processedEvents,
            ObjectMapper objectMapper) {
        this.analytics = analytics; this.processedEvents = processedEvents; this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "submission.created", groupId = "analytics-service")
    @Transactional
    public void onSubmissionCreated(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        UUID eventId = eventId(event, payload);
        if (eventId == null) {
            return;
        }
        if (processedEvents.existsById(eventId)) {
            return;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, CONSUMER));
        } catch (DataIntegrityViolationException duplicate) {
            return;
        }

        String studentId = text(event, "studentId");
        String courseId = text(event, "courseId");
        if (studentId == null || courseId == null) {
            log.warn("analytics: submission event {} missing studentId/courseId; skipping payload={}", eventId, payload);
            return;
        }
        UUID courseUuid;
        try {
            courseUuid = UUID.fromString(courseId);
        } catch (IllegalArgumentException ex) {
            log.warn("analytics: submission event {} has malformed courseId '{}'; skipping", eventId, courseId);
            return;
        }
        analytics.update(new UpdateCourseMetricRequestDto(courseId, 0, 1, 0, null));
        analytics.recordActivity(studentId, courseUuid, "SUBMISSION", 0);
    }

    private static UUID eventId(JsonNode event, String payload) {
        String text = text(event, "eventId");
        if (text == null) {
            log.warn("analytics: submission event missing eventId; skipping payload={}", payload);
            return null;
        }
        try {
            return UUID.fromString(text);
        } catch (IllegalArgumentException ex) {
            log.warn("analytics: submission event has non-UUID eventId '{}'; skipping", text);
            return null;
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
