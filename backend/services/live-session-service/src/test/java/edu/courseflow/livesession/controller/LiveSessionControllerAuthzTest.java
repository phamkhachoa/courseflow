package edu.courseflow.livesession.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.livesession.dto.LiveSessionDtos.CreateLiveSessionRequestDto;
import edu.courseflow.livesession.dto.LiveSessionDtos.LiveSessionDto;
import edu.courseflow.livesession.service.LiveSessionService;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LiveSessionControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID SESSION_ID = UUID.fromString("81000000-0000-0000-0000-000000000001");

    @Mock
    private LiveSessionService sessions;
    @Mock
    private CourseAccessClient courseAccess;

    private LiveSessionController controller;

    @BeforeEach
    void setUp() {
        controller = new LiveSessionController(sessions, courseAccess);
    }

    @Test
    void createRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        CreateLiveSessionRequestDto request = new CreateLiveSessionRequestDto(
                COURSE_ID.toString(),
                "Mentor Q&A",
                null,
                null,
                "INTERNAL",
                Instant.parse("2026-07-01T10:00:00Z"),
                null,
                50);
        when(sessions.create(new CreateLiveSessionRequestDto(
                COURSE_ID.toString(),
                "Mentor Q&A",
                null,
                "9",
                "INTERNAL",
                Instant.parse("2026-07-01T10:00:00Z"),
                null,
                50))).thenReturn(session());

        controller.create(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void startingSessionRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(sessions.get(SESSION_ID)).thenReturn(session());
        when(sessions.start(SESSION_ID, "9", false)).thenReturn(session());

        controller.start(SESSION_ID, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static LiveSessionDto session() {
        return new LiveSessionDto(
                SESSION_ID.toString(),
                COURSE_ID.toString(),
                "Mentor Q&A",
                null,
                "9",
                "INTERNAL",
                null,
                Instant.parse("2026-07-01T10:00:00Z"),
                null,
                null,
                null,
                50,
                "SCHEDULED",
                null);
    }
}
