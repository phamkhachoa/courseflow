package edu.courseflow.notification.consumer;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.notification.model.ProcessedEvent;
import edu.courseflow.notification.repository.NotificationRepository;
import edu.courseflow.notification.repository.ProcessedEventRepository;
import edu.courseflow.notification.service.NotificationDeliveryDispatcher;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class DeadlineReminderEventConsumer {

    private static final Logger log = LoggerFactory.getLogger(DeadlineReminderEventConsumer.class);
    private static final String CONSUMER = "notification:deadline.reminder.due";
    private static final String CHANNEL = "DEADLINE_REMINDER";

    private final ProcessedEventRepository processedEvents;
    private final ObjectMapper objectMapper;
    private final NotificationRepository notifications;
    private final NotificationDeliveryDispatcher dispatcher;

    public DeadlineReminderEventConsumer(ProcessedEventRepository processedEvents,
                                         ObjectMapper objectMapper,
                                         NotificationRepository notifications,
                                         NotificationDeliveryDispatcher dispatcher) {
        this.processedEvents = processedEvents;
        this.objectMapper = objectMapper;
        this.notifications = notifications;
        this.dispatcher = dispatcher;
    }

    @KafkaListener(topics = "deadline.reminder.due", groupId = "notification-service")
    @Transactional
    public void onDeadlineReminderDue(String payload) throws Exception {
        JsonNode event = objectMapper.readTree(payload);
        String eventIdText = text(event, "eventId");
        if (eventIdText == null) {
            log.warn("notification: deadline reminder payload missing eventId; skipping payload={}", payload);
            return;
        }
        UUID eventId;
        try {
            eventId = UUID.fromString(eventIdText);
        } catch (IllegalArgumentException ex) {
            log.warn("notification: deadline reminder event has non-UUID eventId '{}'; skipping", eventIdText);
            return;
        }
        String studentId = text(event, "studentId");
        if (studentId == null) {
            log.warn("notification: deadline reminder event {} missing studentId; skipping", eventId);
            return;
        }
        if (processedEvents.existsById(eventId)) {
            log.debug("notification: skipping already processed deadline reminder {}", eventId);
            return;
        }
        try {
            processedEvents.saveAndFlush(new ProcessedEvent(eventId, CONSUMER));
        } catch (DataIntegrityViolationException duplicate) {
            log.debug("notification: deadline reminder {} processed concurrently; skipping", eventId);
            return;
        }
        if (!notifications.channelEnabled(studentId, CHANNEL)) {
            log.debug("notification: user {} opted out of {} channel; skipping", studentId, CHANNEL);
            return;
        }

        String assignmentId = text(event, "assignmentId");
        String dueAt = text(event, "dueAt");
        String title = "Sắp đến hạn nộp bài";
        String body = body(assignmentId, dueAt);
        var notification = notifications.insertEntity(studentId, CHANNEL, title, body);
        dispatcher.dispatch(notification);
    }

    private static String body(String assignmentId, String dueAt) {
        String shortAssignment = assignmentId == null || assignmentId.length() < 8
                ? "bài nộp"
                : "bài nộp " + assignmentId.substring(0, 8);
        if (dueAt == null) {
            return "Bạn có " + shortAssignment + " sắp đến hạn.";
        }
        return "Bạn có " + shortAssignment + " đến hạn lúc " + dueAt + ".";
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
