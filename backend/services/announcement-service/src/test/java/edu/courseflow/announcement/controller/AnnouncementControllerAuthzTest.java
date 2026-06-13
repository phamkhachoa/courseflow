package edu.courseflow.announcement.controller;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.announcement.dto.AnnouncementDtos.AnnouncementDto;
import edu.courseflow.announcement.dto.AnnouncementDtos.CreateAnnouncementRequestDto;
import edu.courseflow.announcement.service.AnnouncementService;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import java.time.Instant;
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
class AnnouncementControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID ANNOUNCEMENT_ID = UUID.fromString("80000000-0000-0000-0000-000000000001");

    @Mock
    private AnnouncementService announcements;
    @Mock
    private CourseAccessClient courseAccess;

    private AnnouncementController controller;

    @BeforeEach
    void setUp() {
        controller = new AnnouncementController(announcements, courseAccess);
    }

    @Test
    void staffListingCourseAnnouncementsRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(announcements.list(Optional.of(COURSE_ID), Optional.empty())).thenReturn(java.util.List.of());

        controller.list(Optional.of(COURSE_ID), Optional.empty(), instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void createRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        CreateAnnouncementRequestDto request = new CreateAnnouncementRequestDto(
                COURSE_ID.toString(), null, "Welcome", "Hello", "COURSE", null);
        when(announcements.create(new CreateAnnouncementRequestDto(
                COURSE_ID.toString(), "9", "Welcome", "Hello", "COURSE", null))).thenReturn(published());

        controller.create(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void learnerCannotReadUnpublishedAnnouncementById() {
        CurrentUser learner = learner();
        when(announcements.get(ANNOUNCEMENT_ID)).thenReturn(draft());

        assertThatThrownBy(() -> controller.get(ANNOUNCEMENT_ID, learner))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("404 NOT_FOUND");
        verify(courseAccess).requireCourseAccess(learner, COURSE_ID);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static CurrentUser learner() {
        return new CurrentUser(4L, "learner@courseflow.local", "STUDENT", Set.of("STUDENT"));
    }

    private static AnnouncementDto published() {
        return new AnnouncementDto(ANNOUNCEMENT_ID.toString(), COURSE_ID.toString(), "9",
                "Welcome", "Hello", "COURSE", "PUBLISHED", null, Instant.now());
    }

    private static AnnouncementDto draft() {
        return new AnnouncementDto(ANNOUNCEMENT_ID.toString(), COURSE_ID.toString(), "9",
                "Draft", "Secret", "COURSE", "DRAFT", null, null);
    }
}
