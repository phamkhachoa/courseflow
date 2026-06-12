package edu.courseflow.livesession.repository;

import edu.courseflow.livesession.dto.LiveSessionDtos.CreateLiveSessionRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.LiveSessionDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.RegistrationDto;
import edu.courseflow.livesession.mapper.LiveSessionMapper;
import edu.courseflow.livesession.model.LiveSession;
import edu.courseflow.livesession.model.LiveSessionRegistration;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class LiveSessionRepository {

    private final LiveSessionJpaRepository sessions;
    private final LiveSessionRegistrationJpaRepository registrations;
    private final LiveSessionMapper mapper;

    public LiveSessionRepository(LiveSessionJpaRepository sessions,
            LiveSessionRegistrationJpaRepository registrations,
            LiveSessionMapper mapper) {
        this.sessions = sessions;
        this.registrations = registrations;
        this.mapper = mapper;
    }

    public LiveSessionDto create(CreateLiveSessionRequestDto request) {
        return mapper.toDto(sessions.save(new LiveSession(request)));
    }

    public Optional<LiveSessionDto> find(UUID sessionId) {
        return sessions.findById(sessionId).map(mapper::toDto);
    }

    public Optional<LiveSessionDto> findLocked(UUID sessionId) {
        return sessions.lockById(sessionId).map(mapper::toDto);
    }

    public List<LiveSessionDto> listByCourse(UUID courseId) {
        List<LiveSession> rows = courseId == null
                ? sessions.findAllByOrderByScheduledStartAsc()
                : sessions.findByCourseIdOrderByScheduledStartAsc(courseId);
        return rows.stream().map(mapper::toDto).toList();
    }

    public void updateStatus(UUID sessionId, String status, boolean setStart, boolean setEnd, String recordingKey) {
        sessions.findById(sessionId).ifPresent(session -> {
            session.updateStatus(status, setStart, setEnd, recordingKey);
            sessions.save(session);
        });
    }

    public int countRegistrations(UUID sessionId) {
        return registrations.countBySessionId(sessionId);
    }

    public RegistrationDto register(UUID sessionId, String userId) {
        LiveSessionRegistration registration = registrations.findBySessionIdAndUserId(sessionId, userId)
                .orElseGet(() -> registrations.save(new LiveSessionRegistration(sessionId, userId)));
        return mapper.toDto(registration);
    }

    public Optional<RegistrationDto> findRegistration(UUID sessionId, String userId) {
        return registrations.findBySessionIdAndUserId(sessionId, userId).map(mapper::toDto);
    }

    public void markAttended(UUID sessionId, String userId) {
        registrations.findBySessionIdAndUserId(sessionId, userId).ifPresent(registration -> {
            registration.markAttended();
            registrations.save(registration);
        });
    }

}
