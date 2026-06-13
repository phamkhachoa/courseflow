package edu.courseflow.search.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.search.dto.SearchDtos.IndexCourseRequestDto;
import edu.courseflow.search.model.ProcessedEventDocument;
import edu.courseflow.search.repository.ProcessedEventRepository;
import edu.courseflow.search.service.SearchService;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * Projects Debezium CDC events for {@code course-service.courses} into the Elasticsearch course
 * discovery index.
 *
 * <p>Outbox events remain reserved for business workflows. Search is a database projection: Debezium
 * captures inserts/updates/deletes from {@code public.courses} and emits the standard CDC envelope to
 * Kafka. The handler keeps the projection idempotent: the ES write happens first, then a processed
 * marker is saved. If the process crashes between those two actions, Kafka redelivery simply repeats
 * an idempotent upsert/delete.
 */
@Component
public class CourseSearchEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(CourseSearchEventConsumer.class);
    private static final String CONSUMER_NAME = "search-service:course-cdc";

    private final SearchService search;
    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;

    public CourseSearchEventConsumer(SearchService search,
            ProcessedEventRepository processedEvents,
            ObjectMapper objectMapper) {
        this.search = search;
        this.processedEvents = processedEvents;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(
            topics = "${courseflow.search.kafka.course-cdc-topic:courseflow.course.public.courses}",
            groupId = "${courseflow.search.kafka.group-id:search-service}")
    public void onCourseRowChanged(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        String operation = text(event, "op");
        JsonNode row = "d".equals(operation) ? event.get("before") : event.get("after");
        String courseId = text(row, "id");
        String eventId = cdcEventId(event, courseId, operation);
        if (eventId == null || alreadyProcessed(eventId)) {
            return;
        }
        if (courseId == null) {
            log.warn("search: course CDC event {} missing course id; skipping payload={}", eventId, payload);
            markProcessed(eventId);
            return;
        }

        if ("d".equals(operation) || !"PUBLISHED".equals(text(row, "status"))) {
            search.deleteCourse(courseId);
            markProcessed(eventId);
            return;
        }

        IndexCourseRequestDto request = toIndexRequest(row, payload);
        if (request == null) {
            markProcessed(eventId);
            return;
        }

        search.indexCourse(request);
        markProcessed(eventId);
    }

    private IndexCourseRequestDto toIndexRequest(JsonNode row, String payload) {
        String courseId = text(row, "id");
        String code = text(row, "code");
        String title = text(row, "title");
        String slug = text(row, "slug");
        String summary = text(row, "summary");
        String departmentId = text(row, "department_id");
        String level = text(row, "level");
        String status = text(row, "status");
        if (courseId == null || code == null || title == null || slug == null || summary == null
                || departmentId == null || level == null || status == null) {
            log.warn("search: course CDC event missing required index fields; skipping payload={}", payload);
            return null;
        }
        return new IndexCourseRequestDto(courseId, code, title, slug, summary, departmentId, level, status);
    }

    private boolean alreadyProcessed(String eventId) {
        return processedEvents.existsById(markerId(eventId));
    }

    private void markProcessed(String eventId) {
        processedEvents.save(new ProcessedEventDocument(CONSUMER_NAME, eventId, Instant.now()));
    }

    private static String markerId(String eventId) {
        return CONSUMER_NAME + ":" + eventId;
    }

    private static String cdcEventId(JsonNode event, String courseId, String operation) {
        JsonNode source = event.get("source");
        String lsn = text(source, "lsn");
        String txId = text(source, "txId");
        String ts = text(event, "ts_ms");
        String suffix = lsn != null ? lsn : ts;
        if (courseId == null || operation == null || suffix == null) {
            log.warn("search: course CDC event missing id/op/source offset; skipping payload={}", event);
            return null;
        }
        return String.join(":", "course-cdc", courseId, operation, txId == null ? "no-tx" : txId, suffix);
    }

    private static String text(JsonNode node, String field) {
        if (node == null || node.isNull() || node.isMissingNode()) {
            return null;
        }
        JsonNode value = node.get(field);
        if (value == null || value.isNull()) {
            return null;
        }
        String text = value.asText();
        return text.isBlank() ? null : text;
    }
}
