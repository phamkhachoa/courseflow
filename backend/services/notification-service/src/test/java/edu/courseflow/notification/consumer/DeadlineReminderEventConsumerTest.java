package edu.courseflow.notification.consumer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.model.ProcessedEvent;
import edu.courseflow.notification.repository.NotificationRepository;
import edu.courseflow.notification.repository.ProcessedEventRepository;
import edu.courseflow.notification.service.NotificationDeliveryDispatcher;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class DeadlineReminderEventConsumerTest {

    @Mock
    private ProcessedEventRepository processedEvents;
    @Mock
    private NotificationRepository notifications;
    @Mock
    private NotificationDeliveryDispatcher dispatcher;

    private DeadlineReminderEventConsumer consumer;

    @BeforeEach
    void setUp() {
        consumer = new DeadlineReminderEventConsumer(
                processedEvents,
                new ObjectMapper().findAndRegisterModules(),
                notifications,
                dispatcher);
    }

    @Test
    void deadlineReminderCreatesNotificationAndPushesIt() throws Exception {
        UUID eventId = UUID.fromString("70000000-0000-0000-0000-000000000001");
        Notification notification = new Notification(
                "4", "DEADLINE_REMINDER", "Sắp đến hạn nộp bài", "body");
        NotificationDto dto = new NotificationDto(
                notification.getId().toString(), "4", "DEADLINE_REMINDER", notification.getTitle(),
                notification.getBody(), null, "PENDING", null, null, Instant.now());
        when(processedEvents.existsById(eventId)).thenReturn(false);
        when(processedEvents.saveAndFlush(any(ProcessedEvent.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(notifications.channelEnabled("4", "DEADLINE_REMINDER")).thenReturn(true);
        when(notifications.insertEntity(eq("4"), eq("DEADLINE_REMINDER"), eq("Sắp đến hạn nộp bài"), any()))
                .thenReturn(notification);
        when(dispatcher.dispatch(notification)).thenReturn(dto);

        consumer.onDeadlineReminderDue("""
                {
                  "eventId": "70000000-0000-0000-0000-000000000001",
                  "reminderId": "61000000-0000-0000-0000-000000000001",
                  "assignmentId": "63000000-0000-0000-0000-000000000001",
                  "courseId": "30000000-0000-0000-0000-000000000001",
                  "studentId": "4",
                  "dueAt": "2026-07-02T00:00:00Z",
                  "reminderAt": "2026-07-01T00:00:00Z"
                }
                """);

        verify(dispatcher).dispatch(notification);
    }

    @Test
    void optOutSkipsNotificationRow() throws Exception {
        UUID eventId = UUID.fromString("70000000-0000-0000-0000-000000000001");
        when(processedEvents.existsById(eventId)).thenReturn(false);
        when(processedEvents.saveAndFlush(any(ProcessedEvent.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(notifications.channelEnabled("4", "DEADLINE_REMINDER")).thenReturn(false);

        consumer.onDeadlineReminderDue("""
                {
                  "eventId": "70000000-0000-0000-0000-000000000001",
                  "studentId": "4"
                }
                """);

        verify(notifications, never()).insertEntity(any(), any(), any(), any());
        verify(dispatcher, never()).dispatch(any());
    }
}
