package edu.courseflow.notification.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.notification.push.NotificationStreamRegistry;
import edu.courseflow.notification.service.NotificationService;
import edu.courseflow.notification.web.ForbiddenException;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@ExtendWith(MockitoExtension.class)
class NotificationControllerTest {

    @Mock
    private NotificationService notifications;
    @Mock
    private NotificationStreamRegistry streams;

    @Test
    void streamSubscribesOnlyToCallerOwnNotificationFeed() {
        NotificationController controller = new NotificationController(notifications, streams);
        CurrentUser learner = new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
        SseEmitter emitter = new SseEmitter();
        when(streams.subscribe("4")).thenReturn(emitter);

        SseEmitter response = controller.stream("4", learner);

        assertThat(response).isSameAs(emitter);
        verify(streams).subscribe("4");
    }

    @Test
    void streamRejectsCrossUserSubscriptionEvenForAdmins() {
        NotificationController controller = new NotificationController(notifications, streams);
        CurrentUser admin = new CurrentUser(7L, "admin@courseflow.local", "ADMIN", Set.of("ADMIN"));

        assertThatThrownBy(() -> controller.stream("4", admin))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("FORBIDDEN_NOT_OWNER");
    }
}
