package edu.courseflow.enrollment.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.enrollment.model.ProcessedEvent;
import edu.courseflow.enrollment.repository.ProcessedEventRepository;
import edu.courseflow.enrollment.service.EnrollmentService;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class CourseLifecycleEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(CourseLifecycleEventConsumer.class);
    private static final String CONSUMER_PUBLISHED = "enrollment:course.published";
    private static final String CONSUMER_ARCHIVED = "enrollment:course.archived";

    private final EnrollmentService enrollmentService;
    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;
    private final Integer defaultCapacity;

    public CourseLifecycleEventConsumer(EnrollmentService enrollmentService,
            ProcessedEventRepository processedEvents,
            ObjectMapper objectMapper,
            @Value("${courseflow.enrollment.default-capacity:100}") Integer defaultCapacity) {
        this.enrollmentService = enrollmentService;
        this.processedEvents = processedEvents;
        this.objectMapper = objectMapper;
        this.defaultCapacity = defaultCapacity == null || defaultCapacity < 0 ? 100 : defaultCapacity;
    }

    @KafkaListener(topics = "course.published", groupId = "enrollment-service")
    @Transactional
    public void onCoursePublished(String payload) throws Exception {
        handleLifecycle(payload, CONSUMER_PUBLISHED, true);
    }

    @KafkaListener(topics = "course.archived", groupId = "enrollment-service")
    @Transactional
    public void onCourseArchived(String payload) throws Exception {
        handleLifecycle(payload, CONSUMER_ARCHIVED, false);
    }

    private void handleLifecycle(String payload, String consumer, boolean published) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        UUID eventId = parseUuid(text(event, "eventId"), "eventId", consumer, payload);
        if (eventId == null || alreadyProcessed(eventId, consumer)) {
            return;
        }
        UUID courseId = parseUuid(text(event, "courseId"), "courseId", consumer, payload);
        if (courseId == null) {
            return;
        }
        if (published) {
            enrollmentService.initializePublishedCourse(courseId, defaultCapacity);
            log.info("enrollment: initialized capacity for published course {} if absent", courseId);
        } else {
            enrollmentService.archiveCourse(courseId);
            log.info("enrollment: archived course {} by closing capacity", courseId);
        }
    }

    private boolean alreadyProcessed(UUID eventId, String consumer) {
        if (processedEvents.existsById(eventId)) {
            return true;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, consumer));
            return false;
        } catch (DataIntegrityViolationException duplicate) {
            return true;
        }
    }

    private UUID parseUuid(String raw, String field, String consumer, String payload) {
        if (raw == null) {
            log.warn("enrollment: {} event missing {}; skipping payload={}", consumer, field, payload);
            return null;
        }
        try {
            return UUID.fromString(raw);
        } catch (IllegalArgumentException ex) {
            log.warn("enrollment: {} event has non-UUID {} '{}'; skipping", consumer, field, raw);
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
