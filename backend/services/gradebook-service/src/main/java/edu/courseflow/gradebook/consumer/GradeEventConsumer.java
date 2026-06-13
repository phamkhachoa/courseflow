package edu.courseflow.gradebook.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.gradebook.model.GradeCategory;
import edu.courseflow.gradebook.model.GradeEntry;
import edu.courseflow.gradebook.model.GradeItem;
import edu.courseflow.gradebook.model.ProcessedEvent;
import edu.courseflow.gradebook.repository.GradeCategoryRepository;
import edu.courseflow.gradebook.repository.GradeEntryRepository;
import edu.courseflow.gradebook.repository.GradeItemRepository;
import edu.courseflow.gradebook.repository.ProcessedEventRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Ingests auto-grade events from the quiz, peer-review and assignment services and folds them into
 * the gradebook as published {@code grade_entries}. The outbox relay delivers at-least-once, so each
 * listener dedups on {@code eventId} via the {@code processed_events} table (distinct consumer name
 * per topic). The dedup insert and the upsert share one transaction: if the upsert fails, the
 * processed_events row rolls back and the event is reprocessed on redelivery.
 */
@Component
public class GradeEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(GradeEventConsumer.class);

    private static final String CONSUMER_QUIZ = "gradebook:quiz.attempt.graded";
    private static final String CONSUMER_PEER_REVIEW = "gradebook:peer_review.finalized";
    private static final String CONSUMER_SUBMISSION = "gradebook:submission.graded";

    private final ProcessedEventRepository processedEvents;
    private final GradeCategoryRepository categories;
    private final GradeItemRepository items;
    private final GradeEntryRepository entries;
    private final ObjectMapper objectMapper;

    public GradeEventConsumer(ProcessedEventRepository processedEvents,
            GradeCategoryRepository categories,
            GradeItemRepository items,
            GradeEntryRepository entries,
            ObjectMapper objectMapper) {
        this.processedEvents = processedEvents;
        this.categories = categories;
        this.items = items;
        this.entries = entries;
        this.objectMapper = objectMapper;
    }

    @KafkaListener(topics = "quiz.attempt.graded", groupId = "gradebook-service")
    @Transactional
    public void onQuizAttemptGraded(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        UUID eventId = eventId(event, CONSUMER_QUIZ, payload);
        if (eventId == null || !markProcessed(eventId, CONSUMER_QUIZ)) {
            return;
        }
        String quizId = text(event, "quizId");
        String courseId = text(event, "courseId");
        String studentId = text(event, "studentId");
        BigDecimal score = bigDecimal(event, "score");
        BigDecimal maxScore = bigDecimal(event, "maxScore");
        Instant gradedAt = instant(event, "gradedAt");
        if (quizId == null || courseId == null || studentId == null || score == null || maxScore == null) {
            log.warn("gradebook: quiz event {} missing required fields; skipping payload={}", eventId, payload);
            return;
        }
        upsertFromSource(courseId, "QUIZ", quizId, "Quiz " + quizId, studentId, score, maxScore, eventId, gradedAt);
    }

    /**
     * Peer-review finalize events should carry courseId + maxScore so this listener can create a
     * PEER_REVIEW grade item even before any assignment grade item exists. Older events without those
     * fields still fall back to an existing assignment/peer-review item.
     */
    @KafkaListener(topics = "peer_review.finalized", groupId = "gradebook-service")
    @Transactional
    public void onPeerReviewFinalized(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        UUID eventId = eventId(event, CONSUMER_PEER_REVIEW, payload);
        if (eventId == null || !markProcessed(eventId, CONSUMER_PEER_REVIEW)) {
            return;
        }
        String courseId = text(event, "courseId");
        String assignmentId = text(event, "assignmentId");
        String studentId = text(event, "studentId");
        BigDecimal finalScore = bigDecimal(event, "finalScore");
        BigDecimal maxScore = bigDecimal(event, "maxScore");
        Instant gradedAt = instant(event, "gradedAt");
        if (assignmentId == null || studentId == null || finalScore == null) {
            log.warn("gradebook: peer-review event {} missing required fields; skipping payload={}", eventId, payload);
            return;
        }

        GradeItem existing = items.findBySourceTypeAndSourceId("PEER_REVIEW", assignmentId).orElse(null);
        if (existing != null) {
            upsertFromSource(existing.getCourseId().toString(), "PEER_REVIEW", assignmentId,
                    "Peer Review " + assignmentId, studentId, finalScore,
                    maxScore == null ? existing.getMaxScore() : maxScore, eventId, gradedAt);
            return;
        }

        if (courseId != null && maxScore != null) {
            upsertFromSource(courseId, "PEER_REVIEW", assignmentId,
                    "Peer Review " + assignmentId, studentId, finalScore, maxScore, eventId, gradedAt);
            return;
        }

        GradeItem assignmentItem = items.findBySourceTypeAndSourceId("ASSIGNMENT", assignmentId).orElse(null);
        if (assignmentItem == null) {
            log.info("Skipping peer_review.finalized for assignment {}: event has no courseId/maxScore and no ASSIGNMENT/PEER_REVIEW grade item exists",
                    assignmentId);
            return;
        }
        upsertFromSource(assignmentItem.getCourseId().toString(), "PEER_REVIEW", assignmentId,
                "Peer Review " + assignmentId, studentId, finalScore,
                maxScore == null ? assignmentItem.getMaxScore() : maxScore, eventId, gradedAt);
    }

    @KafkaListener(topics = "submission.graded", groupId = "gradebook-service")
    @Transactional
    public void onSubmissionGraded(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        UUID eventId = eventId(event, CONSUMER_SUBMISSION, payload);
        if (eventId == null || !markProcessed(eventId, CONSUMER_SUBMISSION)) {
            return;
        }
        String assignmentId = text(event, "assignmentId");
        String courseId = text(event, "courseId");
        String studentId = text(event, "studentId");
        BigDecimal finalScore = bigDecimal(event, "finalScore");
        BigDecimal maxScore = bigDecimal(event, "maxScore");
        Instant gradedAt = instant(event, "gradedAt");
        if (assignmentId == null || courseId == null || studentId == null || finalScore == null || maxScore == null) {
            log.warn("gradebook: submission event {} missing required fields; skipping payload={}", eventId, payload);
            return;
        }
        upsertFromSource(courseId, "ASSIGNMENT", assignmentId, "Assignment " + assignmentId,
                studentId, finalScore, maxScore, eventId, gradedAt);
    }

    private boolean markProcessed(UUID eventId, String consumer) {
        if (processedEvents.existsById(eventId)) {
            log.debug("Skipping already-processed event {} for {}", eventId, consumer);
            return false;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, consumer));
            return true;
        } catch (DataIntegrityViolationException duplicate) {
            log.debug("Skipping concurrently processed event {} for {}", eventId, consumer);
            return false;
        }
    }

    private static BigDecimal bigDecimal(JsonNode node, String field) {
        String text = text(node, field);
        if (text == null) {
            return null;
        }
        try {
            return new BigDecimal(text);
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private static UUID eventId(JsonNode event, String consumer, String payload) {
        String text = text(event, "eventId");
        if (text == null) {
            log.warn("gradebook: event for {} missing eventId; skipping payload={}", consumer, payload);
            return null;
        }
        try {
            return UUID.fromString(text);
        } catch (IllegalArgumentException ex) {
            log.warn("gradebook: event for {} has non-UUID eventId '{}'; skipping", consumer, text);
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

    private static Instant instant(JsonNode node, String field) {
        String text = text(node, field);
        if (text == null) {
            return null;
        }
        try {
            return Instant.parse(text);
        } catch (RuntimeException ex) {
            return null;
        }
    }

    /**
     * Upserts a grade entry from an auto-grade source. Finds or creates a Canvas-style category and a
     * grade item keyed on (source_type, source_id), then upserts the student's published entry.
     */
    private void upsertFromSource(String courseId, String sourceType, String sourceId, String title,
            String studentId, BigDecimal score, BigDecimal maxScore, UUID eventId, Instant gradedAt) {
        UUID courseUuid = UUID.fromString(courseId);
        UUID categoryId = findOrCreateCategory(courseUuid, categoryName(sourceType));
        UUID gradeItemId = findOrCreateItem(courseUuid, categoryId, sourceType, sourceId, title, maxScore);

        GradeEntry entry = entries.findByGradeItemIdAndStudentId(gradeItemId, studentId)
                .orElseGet(() -> new GradeEntry(UUID.randomUUID(), gradeItemId, studentId));
        if (!entry.publishFromSource(score, null, false, 0, BigDecimal.ZERO, eventId, gradedAt)) {
            log.info("Skipping stale {} grade event {} for student {} source {}:{}",
                    sourceType, eventId, studentId, sourceType, sourceId);
            return;
        }
        entries.save(entry);
    }

    private static String categoryName(String sourceType) {
        return switch (sourceType) {
            case "QUIZ" -> "Quizzes";
            case "PEER_REVIEW" -> "Peer Review";
            case "ASSIGNMENT" -> "Assignments";
            default -> sourceType;
        };
    }

    private UUID findOrCreateCategory(UUID courseId, String name) {
        // weight_percent=0: Canvas style — instructor sets the real weight later.
        return categories.findByCourseIdAndName(courseId, name)
                .map(GradeCategory::getId)
                .orElseGet(() -> categories.save(new GradeCategory(
                        UUID.randomUUID(),
                        courseId,
                        name,
                        BigDecimal.ZERO,
                        categories.nextPosition(courseId),
                        "WEIGHTED_MEAN",
                        0)).getId());
    }

    private UUID findOrCreateItem(UUID courseId, UUID categoryId, String sourceType, String sourceId,
            String title, BigDecimal maxScore) {
        GradeItem item = items.findBySourceTypeAndSourceId(sourceType, sourceId)
                .map(existing -> {
                    existing.setTitle(title);
                    return existing;
                })
                .orElseGet(() -> new GradeItem(
                        UUID.randomUUID(),
                        courseId,
                        categoryId,
                        sourceType,
                        sourceId,
                        title,
                        maxScore,
                        new BigDecimal("100"),
                        BigDecimal.ZERO));
        return items.save(item).getId();
    }
}
