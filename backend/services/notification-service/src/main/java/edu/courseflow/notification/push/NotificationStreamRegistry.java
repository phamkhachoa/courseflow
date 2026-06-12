package edu.courseflow.notification.push;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.notification.dto.NotificationDtos.NotificationDto;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * In-memory registry of Server-Sent Events emitters, keyed by {@code userId}. Backs the realtime
 * push channel: a user subscribes to their own notification stream and, when a notification row is
 * created for them, the row is pushed to every emitter that user currently has open (multiple tabs
 * or devices each hold an emitter).
 *
 * <p>SSE was chosen over STOMP/WebSocket here because notification push is one-directional
 * (server&rarr;client) and fits Spring MVC's {@link SseEmitter} with no extra broker or handshake
 * machinery.
 *
 * <p><b>Single-instance limitation:</b> the registry lives in this JVM's heap, so an emitter is only
 * reachable from the instance that holds it. With more than one notification-service replica, a row
 * created on instance A cannot be pushed to a client connected to instance B. Making push work across
 * replicas would require a shared fan-out bus (e.g. Redis pub/sub: each instance publishes the push
 * payload to a channel and every instance relays to its local emitters). That is intentionally out of
 * scope; the inbox REST endpoint remains the durable source of truth regardless of which instance a
 * client polls.
 */
@Component
public class NotificationStreamRegistry {

    private static final Logger log = LoggerFactory.getLogger(NotificationStreamRegistry.class);

    /** How long an idle SSE connection is held open before the client is expected to reconnect. */
    private static final long EMITTER_TIMEOUT_MS = 30 * 60 * 1000L;

    private final Map<String, CopyOnWriteArrayList<SseEmitter>> emitters = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper;

    public NotificationStreamRegistry(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    /**
     * Register a new emitter for {@code userId} and wire its lifecycle callbacks so it is removed from
     * the registry on completion, timeout, or error. Callers must have already verified that the
     * subscriber owns this stream.
     */
    public SseEmitter subscribe(String userId) {
        SseEmitter emitter = new SseEmitter(EMITTER_TIMEOUT_MS);
        CopyOnWriteArrayList<SseEmitter> userEmitters =
                emitters.computeIfAbsent(userId, k -> new CopyOnWriteArrayList<>());
        userEmitters.add(emitter);

        emitter.onCompletion(() -> remove(userId, emitter));
        emitter.onTimeout(() -> {
            emitter.complete();
            remove(userId, emitter);
        });
        emitter.onError(e -> remove(userId, emitter));

        // An initial comment-style event lets the client confirm the stream is live and primes some
        // proxies that buffer until first byte. Failure here just drops this one emitter.
        try {
            emitter.send(SseEmitter.event().name("subscribed").data("ok"));
        } catch (IOException e) {
            remove(userId, emitter);
        }
        return emitter;
    }

    /**
     * Push a notification to every emitter the user currently has open. Best-effort: an emitter that
     * fails to receive (client gone) is dropped and the rest still get the event. Returns the number of
     * emitters successfully delivered to (0 when the user has no active stream — the row is still in
     * their inbox and will be seen on next poll/reconnect).
     */
    public int push(String userId, NotificationDto notification) {
        CopyOnWriteArrayList<SseEmitter> userEmitters = emitters.get(userId);
        if (userEmitters == null || userEmitters.isEmpty()) {
            return 0;
        }
        String json;
        try {
            json = objectMapper.writeValueAsString(notification);
        } catch (Exception e) {
            log.warn("notification-push: failed to serialize notification {} for user {}; not pushing",
                    notification.id(), userId, e);
            return 0;
        }
        int delivered = 0;
        for (SseEmitter emitter : userEmitters) {
            try {
                emitter.send(SseEmitter.event().name("notification").id(notification.id()).data(json));
                delivered++;
            } catch (Exception e) {
                // Client disconnected between our check and the send; drop just this emitter.
                remove(userId, emitter);
            }
        }
        return delivered;
    }

    private void remove(String userId, SseEmitter emitter) {
        CopyOnWriteArrayList<SseEmitter> userEmitters = emitters.get(userId);
        if (userEmitters == null) {
            return;
        }
        userEmitters.remove(emitter);
        // Drop the bucket once empty so the map does not grow unbounded with one-shot subscribers.
        emitters.computeIfPresent(userId, (k, v) -> v.isEmpty() ? null : v);
    }

    /** Active emitter count for a user (test/observability helper). */
    public int activeEmitters(String userId) {
        List<SseEmitter> userEmitters = emitters.get(userId);
        return userEmitters == null ? 0 : userEmitters.size();
    }
}
