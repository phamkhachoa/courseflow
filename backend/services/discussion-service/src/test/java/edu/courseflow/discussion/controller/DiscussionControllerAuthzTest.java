package edu.courseflow.discussion.controller;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.discussion.dto.DiscussionDtos.DiscussionThreadDto;
import edu.courseflow.discussion.service.DiscussionService;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class DiscussionControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID THREAD_ID = UUID.fromString("41000000-0000-0000-0000-000000000001");
    private static final UUID COMMENT_ID = UUID.fromString("42000000-0000-0000-0000-000000000001");

    @Mock
    private DiscussionService discussions;
    @Mock
    private CourseAccessClient courseAccess;

    private DiscussionController controller;

    @BeforeEach
    void setUp() {
        controller = new DiscussionController(discussions, courseAccess);
    }

    @Test
    void instructorListRequiresCourseIdInsteadOfGlobalAccess() {
        assertThrows(ResponseStatusException.class,
                () -> controller.listThreads(Optional.empty(), Optional.empty(), instructor()));
    }

    @Test
    void staffListWithCourseIdRequiresScopedCourseStaffAccess() {
        when(discussions.listThreads(Optional.of(COURSE_ID), Optional.empty())).thenReturn(List.of());

        controller.listThreads(Optional.of(COURSE_ID), Optional.empty(), instructor());

        verify(courseAccess).requireCourseStaffAccess(instructor(), COURSE_ID);
    }

    @Test
    void acceptCommentRequiresScopedCourseStaffAccess() {
        when(discussions.getThread(THREAD_ID)).thenReturn(thread());
        when(discussions.acceptComment(THREAD_ID, COMMENT_ID)).thenReturn(thread());

        controller.acceptComment(THREAD_ID, COMMENT_ID, instructor());

        verify(courseAccess).requireCourseStaffAccess(instructor(), COURSE_ID);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static DiscussionThreadDto thread() {
        return new DiscussionThreadDto(
                THREAD_ID.toString(),
                COURSE_ID.toString(),
                null,
                "4",
                "Need help",
                "OPEN",
                Instant.parse("2026-06-13T00:00:00Z"),
                List.of());
    }
}
