package edu.courseflow.livesession.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.livesession.dto.LiveSessionDtos.CreateLiveSessionRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.EndSessionRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.JoinInfoDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.LiveSessionDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.RegisterRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.RegistrationDto;
import edu.courseflow.livesession.model.OutboxEvent;
import edu.courseflow.livesession.repository.LiveSessionRepository;
import edu.courseflow.livesession.repository.OutboxEventRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LiveSessionService {

    private final LiveSessionRepository sessions;
    private final OutboxEventRepository outboxEvents;
    private final ObjectMapper objectMapper;
    private final CourseAccessClient courseAccess;
    private final String joinBaseUrl;

    public LiveSessionService(LiveSessionRepository sessions,
                              OutboxEventRepository outboxEvents,
                              ObjectMapper objectMapper,
                              CourseAccessClient courseAccess,
                              @Value("${courseflow.live.join-base-url:https://live.local/join}") String joinBaseUrl) {
        this.sessions = sessions;
        this.outboxEvents = outboxEvents;
        this.objectMapper = objectMapper;
        this.courseAccess = courseAccess;
        this.joinBaseUrl = joinBaseUrl;
    }

    public List<LiveSessionDto> listByCourse(String courseId) {
        return sessions.listByCourse(courseId == null ? null : UUID.fromString(courseId));
    }

    public LiveSessionDto get(UUID sessionId) {
        return sessions.find(sessionId)
                .orElseThrow(() -> new NotFoundException("Live session not found: " + sessionId));
    }

    @Transactional
    public LiveSessionDto create(CreateLiveSessionRequestDto request) {
        LiveSessionDto created = sessions.create(request);
        saveOutbox(UUID.fromString(created.id()), "live.session.scheduled", Map.of(
                "sessionId", created.id(),
                "courseId", created.courseId(),
                "hostId", created.hostId(),
                "scheduledStart", created.scheduledStart().toString()));
        return created;
    }

    @Transactional
    public RegistrationDto register(UUID sessionId, RegisterRequestDto request) {
        LiveSessionDto session = sessions.findLocked(sessionId)
                .orElseThrow(() -> new NotFoundException("Live session not found: " + sessionId));
        courseAccess.requireStudentCourseAccess(request.userId(), UUID.fromString(session.courseId()));
        if (session.capacity() != null && sessions.countRegistrations(sessionId) >= session.capacity()
                && sessions.findRegistration(sessionId, request.userId()).isEmpty()) {
            throw new BadRequestException("LIVE_SESSION_FULL");
        }
        return sessions.register(sessionId, request.userId());
    }

    @Transactional
    public LiveSessionDto start(UUID sessionId, String actorId, boolean admin) {
        LiveSessionDto session = get(sessionId);
        requireHostOrAdmin(session, actorId, admin);
        if (!"SCHEDULED".equals(session.status())) {
            throw new BadRequestException("LIVE_SESSION_NOT_STARTABLE");
        }
        sessions.updateStatus(sessionId, "LIVE", true, false, null);
        saveOutbox(sessionId, "live.session.started", Map.of(
                "sessionId", sessionId.toString(),
                "courseId", session.courseId()));
        return get(sessionId);
    }

    @Transactional
    public LiveSessionDto end(UUID sessionId, EndSessionRequestDto request, String actorId, boolean admin) {
        LiveSessionDto session = get(sessionId);
        requireHostOrAdmin(session, actorId, admin);
        sessions.updateStatus(sessionId, "ENDED", false, true,
                request == null ? null : request.recordingStorageKey());
        return get(sessionId);
    }

    @Transactional
    public JoinInfoDto join(UUID sessionId, String userId) {
        LiveSessionDto session = get(sessionId);
        if (sessions.findRegistration(sessionId, userId).isEmpty()) {
            throw new BadRequestException("NOT_REGISTERED");
        }
        sessions.markAttended(sessionId, userId);
        String joinUrl = "%s/%s?user=%s".formatted(joinBaseUrl, sessionId, userId);
        return new JoinInfoDto(sessionId.toString(), userId, joinUrl, session.status());
    }

    private void saveOutbox(UUID aggregateId, String eventType, Map<String, ?> payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "live-session", eventType, toJson(payload)));
    }

    private void requireHostOrAdmin(LiveSessionDto session, String actorId, boolean admin) {
        if (!admin && (actorId == null || !actorId.equals(session.hostId()))) {
            throw new BadRequestException("LIVE_SESSION_HOST_REQUIRED");
        }
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
