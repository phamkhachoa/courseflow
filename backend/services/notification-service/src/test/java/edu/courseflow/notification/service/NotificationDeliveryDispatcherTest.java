package edu.courseflow.notification.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import edu.courseflow.notification.model.Notification;
import edu.courseflow.notification.push.NotificationStreamRegistry;
import edu.courseflow.notification.repository.NotificationRepository;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@ExtendWith(MockitoExtension.class)
class NotificationDeliveryDispatcherTest {

    @Mock
    private NotificationRepository notifications;
    @Mock
    private NotificationDeliveryService delivery;
    @Mock
    private NotificationStreamRegistry streams;

    @Test
    void dispatchRunsImmediatelyWhenNoTransactionSynchronizationExists() {
        Notification notification = new Notification("4", "SYSTEM", "Welcome", "Hello");
        NotificationDto delivered = dto(notification, "DELIVERED");
        when(notifications.saveEntity(notification)).thenReturn(notification);
        when(notifications.toDto(notification)).thenReturn(delivered);

        NotificationDeliveryDispatcher dispatcher = new NotificationDeliveryDispatcher(
                notifications, delivery, streams);

        NotificationDto response = dispatcher.dispatch(notification);

        assertThat(response).isSameAs(delivered);
        verify(delivery).deliver(notification);
        verify(notifications).saveEntity(notification);
        verify(streams).push("4", delivered);
    }

    @Test
    void dispatchRunsAfterCommitWhenTransactionSynchronizationExists() {
        Notification notification = new Notification("4", "SYSTEM", "Welcome", "Hello");
        NotificationDto pending = dto(notification, "PENDING");
        NotificationDto delivered = dto(notification, "DELIVERED");
        when(notifications.toDto(notification)).thenReturn(pending, delivered);
        when(notifications.saveEntity(notification)).thenReturn(notification);

        NotificationDeliveryDispatcher dispatcher = new NotificationDeliveryDispatcher(
                notifications, delivery, streams);

        TransactionSynchronizationManager.initSynchronization();
        try {
            NotificationDto response = dispatcher.dispatch(notification);

            assertThat(response).isSameAs(pending);
            verify(delivery, never()).deliver(notification);
            verify(notifications, never()).saveEntity(notification);
            for (TransactionSynchronization synchronization : TransactionSynchronizationManager.getSynchronizations()) {
                synchronization.afterCommit();
            }
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }

        verify(delivery).deliver(notification);
        verify(notifications).saveEntity(notification);
        verify(streams).push("4", delivered);
    }

    @Test
    void dispatchClaimsFailedRowsBeforeAfterCommitRetry() {
        Notification notification = new Notification("4", "SYSTEM", "Welcome", "Hello");
        notification.markDeliveryFailed("temporary outage");
        NotificationDto dispatching = dto(notification, "DISPATCHING");
        NotificationDto delivered = dto(notification, "DELIVERED");
        when(notifications.toDto(notification)).thenReturn(dispatching, delivered);
        when(notifications.saveEntity(notification)).thenReturn(notification);

        NotificationDeliveryDispatcher dispatcher = new NotificationDeliveryDispatcher(
                notifications, delivery, streams);

        TransactionSynchronizationManager.initSynchronization();
        try {
            NotificationDto response = dispatcher.dispatch(notification);

            assertThat(response).isSameAs(dispatching);
            assertThat(notification.getDeliveryStatus()).isEqualTo("DISPATCHING");
            assertThat(notification.getDeliveryAttempts()).isEqualTo(1);
            for (TransactionSynchronization synchronization : TransactionSynchronizationManager.getSynchronizations()) {
                synchronization.afterCommit();
            }
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }

        verify(delivery).deliver(notification);
        assertThat(notification.getDeliveryAttempts()).isEqualTo(1);
        verify(notifications).saveEntity(notification);
        verify(streams).push("4", delivered);
    }

    private static NotificationDto dto(Notification notification, String status) {
        return new NotificationDto(
                notification.getId().toString(),
                notification.getUserId(),
                notification.getNotificationType(),
                notification.getTitle(),
                notification.getBody(),
                null,
                status,
                null,
                null,
                Instant.parse("2026-06-15T00:00:00Z"));
    }
}
