package edu.courseflow.livesession.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.livesession.dto.LiveSessionDtos.CreateLiveSessionRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.EndSessionRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.JoinInfoDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.LiveSessionDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.RegisterRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.RegistrationDto;
import edu.courseflow.livesession.service.LiveSessionService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/internal/live-sessions")
public class LiveSessionController {

    private final LiveSessionService sessions;
    private final CourseAccessClient courseAccess;

    public LiveSessionController(LiveSessionService sessions, CourseAccessClient courseAccess) {
        this.sessions = sessions;
        this.courseAccess = courseAccess;
    }

    @GetMapping
    public List<LiveSessionDto> list(@RequestParam(required = false) String courseId, CurrentUser user) {
        callerId(user);
        if (!isStaff(user)) {
            if (courseId == null || courseId.isBlank()) {
                throw new ResponseStatusException(HttpStatus.FORBIDDEN, "courseId is required for learner access");
            }
            courseAccess.requireCourseAccess(user, UUID.fromString(courseId));
        }
        return sessions.listByCourse(courseId);
    }

    @GetMapping("/{sessionId}")
    public LiveSessionDto get(@PathVariable UUID sessionId, CurrentUser user) {
        callerId(user);
        LiveSessionDto session = sessions.get(sessionId);
        if (!isStaff(user)) {
            courseAccess.requireCourseAccess(user, UUID.fromString(session.courseId()));
        }
        return session;
    }

    @PostMapping
    public LiveSessionDto create(@Valid @RequestBody CreateLiveSessionRequestDto request, CurrentUser user) {
        requireStaff(user);
        CreateLiveSessionRequestDto trusted = new CreateLiveSessionRequestDto(
                request.courseId(),
                request.title(),
                request.description(),
                callerId(user),
                request.provider(),
                request.scheduledStart(),
                request.scheduledEnd(),
                request.capacity());
        return sessions.create(trusted);
    }

    @PostMapping("/{sessionId}/register")
    public RegistrationDto register(@PathVariable UUID sessionId, @Valid @RequestBody RegisterRequestDto request,
                                    CurrentUser user) {
        return sessions.register(sessionId, new RegisterRequestDto(callerId(user)));
    }

    @PostMapping("/{sessionId}/start")
    public LiveSessionDto start(@PathVariable UUID sessionId, CurrentUser user) {
        requireStaff(user);
        return sessions.start(sessionId, callerId(user), user.hasRole("ADMIN"));
    }

    @PostMapping("/{sessionId}/end")
    public LiveSessionDto end(@PathVariable UUID sessionId, @RequestBody(required = false) EndSessionRequestDto request,
                              CurrentUser user) {
        requireStaff(user);
        return sessions.end(sessionId, request, callerId(user), user.hasRole("ADMIN"));
    }

    @GetMapping("/{sessionId}/join")
    public JoinInfoDto join(@PathVariable UUID sessionId, CurrentUser user) {
        return sessions.join(sessionId, callerId(user));
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated user required");
        }
        return String.valueOf(user.id());
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!isStaff(user)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires ADMIN or INSTRUCTOR role");
        }
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("ADMIN", "INSTRUCTOR");
    }
}
