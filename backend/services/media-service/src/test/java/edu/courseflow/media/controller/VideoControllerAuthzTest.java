package edu.courseflow.media.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.media.dto.VideoDtos.PlaybackUrlDto;
import edu.courseflow.media.dto.VideoDtos.RegisterVideoRequestDto;
import edu.courseflow.media.dto.VideoDtos.VideoAssetDto;
import edu.courseflow.media.service.VideoService;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class VideoControllerAuthzTest {

    private static final UUID COURSE_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID VIDEO_ID = UUID.fromString("83000000-0000-0000-0000-000000000001");

    @Mock
    private VideoService videos;
    @Mock
    private CourseAccessClient courseAccess;

    private VideoController controller;

    @BeforeEach
    void setUp() {
        controller = new VideoController(videos, courseAccess);
    }

    @Test
    void registerRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        RegisterVideoRequestDto request = new RegisterVideoRequestDto(
                null, COURSE_ID.toString(), "Lesson", "videos/9/lesson.mp4", 120);
        when(videos.register(request, "9")).thenReturn(video());

        controller.register(request, instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    @Test
    void staffPlaybackRequiresScopedCourseStaffAccess() {
        CurrentUser instructor = instructor();
        when(videos.get(VIDEO_ID)).thenReturn(video());
        when(videos.playbackUrl(VIDEO_ID, "hls", "9", true)).thenReturn(
                new PlaybackUrlDto(VIDEO_ID.toString(), "https://cdn.example/video.m3u8", Instant.now()));

        controller.playbackUrl(VIDEO_ID, "hls", instructor);

        verify(courseAccess).requireCourseStaffAccess(instructor, COURSE_ID);
    }

    private static CurrentUser instructor() {
        return new CurrentUser(9L, "instructor@courseflow.local", "INSTRUCTOR", Set.of("INSTRUCTOR"));
    }

    private static VideoAssetDto video() {
        return new VideoAssetDto(
                VIDEO_ID.toString(),
                null,
                COURSE_ID.toString(),
                "Lesson",
                "videos/9/lesson.mp4",
                120,
                "READY",
                Instant.parse("2026-06-13T00:00:00Z"),
                List.of(),
                List.of());
    }
}
