package edu.courseflow.notification.consumer;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.notification.client.EnrollmentRosterClient;
import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.model.ProcessedEvent;
import edu.courseflow.notification.repository.NotificationRepository;
import edu.courseflow.notification.repository.ProcessedEventRepository;
import edu.courseflow.notification.service.NotificationDeliveryDispatcher;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AnnouncementEventConsumerTest {

    private static final String COURSE_ID = "30000000-0000-0000-0000-000000000001";

    @Mock
    private ProcessedEventRepository processedEvents;
    @Mock
    private EnrollmentRosterClient roster;
    @Mock
    private NotificationRepository notifications;
    @Mock
    private NotificationDeliveryDispatcher dispatcher;

    private AnnouncementEventConsumer consumer;

    @BeforeEach
    void setUp() {
        consumer = new AnnouncementEventConsumer(
                processedEvents,
                new ObjectMapper().findAndRegisterModules(),
                roster,
                notifications,
                dispatcher);
    }

    @Test
    void announcementPublishedFansOutToRosterRecipients() throws Exception {
        UUID eventId = UUID.fromString("70000000-0000-0000-0000-000000000101");
        Notification notification = new Notification("4", "ANNOUNCEMENT", "Welcome", "New announcement: Welcome");
        NotificationDto dto = new NotificationDto(
                notification.getId().toString(),
                "4",
                "ANNOUNCEMENT",
                notification.getTitle(),
                notification.getBody(),
                null,
                "PENDING",
                null,
                null,
                Instant.now());
        when(processedEvents.existsById(eventId)).thenReturn(false);
        when(processedEvents.saveAndFlush(any(ProcessedEvent.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(roster.activeStudentIds(COURSE_ID)).thenReturn(List.of("4", "5"));
        when(notifications.channelEnabled("4", "ANNOUNCEMENT")).thenReturn(true);
        when(notifications.channelEnabled("5", "ANNOUNCEMENT")).thenReturn(false);
        when(notifications.insertEntity("4", "ANNOUNCEMENT", "Welcome", "New announcement: Welcome"))
                .thenReturn(notification);
        when(dispatcher.dispatch(notification)).thenReturn(dto);

        consumer.onAnnouncementPublished("""
                {
                  "eventId": "70000000-0000-0000-0000-000000000101",
                  "announcementId": "71000000-0000-0000-0000-000000000101",
                  "courseId": "30000000-0000-0000-0000-000000000001",
                  "title": "Welcome"
                }
                """);

        verify(roster).activeStudentIds(COURSE_ID);
        verify(notifications).insertEntity("4", "ANNOUNCEMENT", "Welcome", "New announcement: Welcome");
        verify(notifications, never()).insertEntity(eq("5"), any(), any(), any());
        verify(dispatcher).dispatch(notification);
    }
}
