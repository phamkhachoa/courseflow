package edu.courseflow.analytics.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.analytics.dto.AnalyticsDtos.UpdateCourseMetricRequestDto;
import edu.courseflow.analytics.model.ProcessedEvent;
import edu.courseflow.analytics.repository.AnalyticsRepository;
import edu.courseflow.analytics.repository.ProcessedEventRepository;
import edu.courseflow.analytics.repository.ReportingRepository;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class EnrollmentEventConsumer {
    private static final Logger log = LoggerFactory.getLogger(EnrollmentEventConsumer.class);
    private static final String CONSUMER = "analytics:enrollment.created";

    private final AnalyticsRepository analytics;
    private final ReportingRepository reporting;
    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;

    public EnrollmentEventConsumer(AnalyticsRepository analytics, ReportingRepository reporting,
                                    ProcessedEventRepository processedEvents, ObjectMapper objectMapper) {
        this.analytics = analytics; this.reporting = reporting;
        this.processedEvents = processedEvents; this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "enrollment.created", groupId = "analytics-service")
    @Transactional
    public void onEnrollmentCreated(String payload) throws Exception {
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

        String courseId = text(event, "courseId");
        if (courseId == null) {
            log.warn("analytics: enrollment event {} missing courseId; skipping payload={}", eventId, payload);
            return;
        }
        UUID courseUuid;
        try {
            courseUuid = UUID.fromString(courseId);
        } catch (IllegalArgumentException ex) {
            log.warn("analytics: enrollment event {} has malformed courseId '{}'; skipping", eventId, courseId);
            return;
        }
        analytics.update(new UpdateCourseMetricRequestDto(courseId, 1, 0, 0, null));
        reporting.upsertCompletionEnrolled(courseUuid);
    }

    private static UUID eventId(JsonNode event, String payload) {
        String text = text(event, "eventId");
        if (text == null) {
            log.warn("analytics: enrollment event missing eventId; skipping payload={}", payload);
            return null;
        }
        try {
            return UUID.fromString(text);
        } catch (IllegalArgumentException ex) {
            log.warn("analytics: enrollment event has non-UUID eventId '{}'; skipping", text);
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
