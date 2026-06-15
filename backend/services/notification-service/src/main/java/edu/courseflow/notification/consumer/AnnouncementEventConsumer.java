package edu.courseflow.notification.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.notification.client.EnrollmentRosterClient;
import edu.courseflow.notification.model.ProcessedEvent;
import edu.courseflow.notification.repository.NotificationRepository;
import edu.courseflow.notification.repository.ProcessedEventRepository;
import edu.courseflow.notification.service.NotificationDeliveryDispatcher;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Consumes {@code announcement.published} events and fans them out to one notification row per
 * enrolled recipient. The relay delivers at-least-once, so this consumer dedups on {@code eventId}
 * via the {@code processed_events} table. The dedup insert and the business inserts share one
 * transaction: if the fan-out fails, the processed_events row rolls back too and the event is
 * reprocessed on redelivery.
 *
 * <p>Recipients: notification-service owns no enrollment data, so it asks enrollment-service for the
 * course roster (the announcement event carries only {@code courseId}). Each notification is written
 * with the recipient's real {@code userId} — previously the buggy code stored {@code courseId} in the
 * {@code user_id} column, so every user's inbox query missed these rows.
 *
 * <p>Preferences: before writing a row the fan-out consults {@code notification_preferences} and skips
 * any recipient who has opted out of the {@code ANNOUNCEMENT} channel (preferences are opt-out — no row
 * means the default-enabled applies). Realtime push: each persisted row is also pushed to that user's
 * active SSE emitters (best-effort; the inbox row is the durable record).
 */
@Component
public class AnnouncementEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(AnnouncementEventConsumer.class);
    private static final String CONSUMER = "notification:announcement.published";
    /** Notification type written for these rows; also the preference channel a user can opt out of. */
    private static final String CHANNEL = "ANNOUNCEMENT";

    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;
    private final EnrollmentRosterClient roster;
    private final NotificationRepository notifications;
    private final NotificationDeliveryDispatcher dispatcher;

    public AnnouncementEventConsumer(ProcessedEventRepository processedEvents, ObjectMapper objectMapper,
                                     EnrollmentRosterClient roster,
                                     NotificationRepository notifications,
                                     NotificationDeliveryDispatcher dispatcher) {
        this.processedEvents = processedEvents;
        this.objectMapper = objectMapper;
        this.roster = roster;
        this.notifications = notifications;
        this.dispatcher = dispatcher;
    }

    @KafkaListener(topics = "announcement.published", groupId = "notification-service")
    @Transactional
    public void onAnnouncementPublished(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);

        // Null-safe parsing: a malformed payload (missing eventId/courseId) must not throw an NPE that
        // turns the message into an un-skippable poison message. Skip it with a clear log instead.
        String eventIdText = text(event, "eventId");
        if (eventIdText == null) {
            log.warn("notification: announcement event missing eventId; skipping payload={}", payload);
            return;
        }
        UUID eventId;
        try {
            eventId = UUID.fromString(eventIdText);
        } catch (IllegalArgumentException ex) {
            log.warn("notification: announcement event has non-UUID eventId '{}'; skipping", eventIdText);
            return;
        }

        String courseId = text(event, "courseId");
        if (courseId == null) {
            log.warn("notification: announcement event {} missing courseId; skipping", eventId);
            return;
        }
        String title = text(event, "title");
        if (title == null) {
            title = "New announcement";
        }

        if (processedEvents.existsById(eventId)) {
            log.debug("Skipping already-processed event {}", eventId);
            return;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, CONSUMER));
        } catch (DataIntegrityViolationException duplicate) {
            log.debug("Skipping concurrently processed event {}", eventId);
            return;
        }

        List<String> recipients = roster.activeStudentIds(courseId);
        if (recipients.isEmpty()) {
            log.info("notification: announcement {} for course {} has no active recipients; nothing to fan out",
                    eventId, courseId);
            return;
        }

        String body = "New announcement: " + title;
        int fannedOut = 0;
        for (String userId : recipients) {
            // Respect per-user opt-out before writing the row at all.
            if (!notifications.channelEnabled(userId, CHANNEL)) {
                log.debug("notification: user {} opted out of {} channel; skipping", userId, CHANNEL);
                continue;
            }
            var notification = notifications.insertEntity(userId, CHANNEL, title, body);
            fannedOut++;
            dispatcher.dispatch(notification);
        }
        log.debug("notification: fanned out announcement {} to {} of {} recipient(s) (rest opted out)",
                eventId, fannedOut, recipients.size());
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
}
