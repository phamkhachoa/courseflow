package edu.courseflow.media.controller;

import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.media.dto.MediaDtos.PresignedUploadDto;
import edu.courseflow.media.dto.MediaDtos.RequestUploadUrlDto;
import edu.courseflow.media.dto.VideoDtos.PlaybackUrlDto;
import edu.courseflow.media.dto.VideoDtos.RegisterVideoRequestDto;
import edu.courseflow.media.dto.VideoDtos.StartTranscodeRequestDto;
import edu.courseflow.media.dto.VideoDtos.UpdateProgressRequestDto;
import edu.courseflow.media.dto.VideoDtos.VideoAssetDto;
import edu.courseflow.media.dto.VideoDtos.VideoCaptionDto;
import edu.courseflow.media.dto.VideoDtos.VideoManifestDto;
import edu.courseflow.media.dto.VideoDtos.VideoProgressDto;
import edu.courseflow.media.dto.VideoDtos.VideoReadinessDto;
import edu.courseflow.media.service.VideoService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class VideoController {

    private final VideoService videos;
    private final CourseAccessClient courseAccess;

    public VideoController(VideoService videos,
            CourseAccessClient courseAccess) {
        this.videos = videos;
        this.courseAccess = courseAccess;
    }

    @PostMapping("/internal/media/videos")
    public VideoAssetDto register(@Valid @RequestBody RegisterVideoRequestDto request, CurrentUser user) {
        requireStaff(user);
        requireVideoCourseStaffAccess(user, request.courseId());
        return videos.register(request, callerId(user));
    }

    @GetMapping("/internal/media/videos")
    public List<VideoAssetDto> list(@RequestParam(required = false) UUID courseId, CurrentUser user) {
        requireStaff(user);
        if (courseId == null) {
            requirePlatformAdmin(user);
        } else {
            courseAccess.requireCourseStaffAccess(user, courseId);
        }
        return videos.list(courseId);
    }

    /** Presigned PUT URL for uploading a source video file directly to the object store. */
    @PostMapping("/internal/media/videos/upload-url")
    public PresignedUploadDto uploadUrl(@Valid @RequestBody RequestUploadUrlDto request, CurrentUser user) {
        requireStaff(user);
        return videos.requestSourceUploadUrl(request, callerId(user));
    }

    @GetMapping("/internal/media/videos/{videoId}")
    public VideoAssetDto get(@PathVariable UUID videoId, CurrentUser user) {
        VideoAssetDto video = videos.get(videoId);
        if (isStaff(user)) {
            requireVideoCourseStaffAccess(user, video.courseId());
            return video;
        }
        return videos.get(videoId, callerId(user), false);
    }

    @GetMapping("/internal/media/videos/{videoId}/readiness")
    public VideoReadinessDto readiness(@PathVariable UUID videoId) {
        return videos.readiness(videoId);
    }

    @PostMapping("/internal/media/videos/{videoId}/transcode")
    public VideoAssetDto transcode(@PathVariable UUID videoId, @Valid @RequestBody StartTranscodeRequestDto request,
                                   CurrentUser user) {
        requireStaff(user);
        requireVideoCourseStaffAccess(user, videos.get(videoId).courseId());
        return videos.startTranscode(videoId, new StartTranscodeRequestDto(callerId(user)));
    }

    @GetMapping("/internal/media/videos/{videoId}/manifest")
    public VideoManifestDto manifest(@PathVariable UUID videoId, @RequestParam(required = false) String protocol,
                                     CurrentUser user) {
        boolean privileged = scopedVideoPrivilege(videoId, user);
        return videos.manifest(videoId, protocol, callerId(user), privileged);
    }

    @GetMapping("/internal/media/videos/{videoId}/captions")
    public List<VideoCaptionDto> captions(@PathVariable UUID videoId, CurrentUser user) {
        boolean privileged = scopedVideoPrivilege(videoId, user);
        return videos.captions(videoId, callerId(user), privileged);
    }

    @GetMapping("/internal/media/videos/{videoId}/progress")
    public VideoProgressDto getProgress(@PathVariable UUID videoId, CurrentUser user) {
        boolean privileged = scopedVideoPrivilege(videoId, user);
        return videos.getProgress(videoId, callerId(user), privileged);
    }

    @PutMapping("/internal/media/videos/{videoId}/progress")
    public VideoProgressDto updateProgress(@PathVariable UUID videoId, @Valid @RequestBody UpdateProgressRequestDto request,
                                           CurrentUser user) {
        UpdateProgressRequestDto trusted = new UpdateProgressRequestDto(
                callerId(user),
                request.positionSeconds(),
                request.durationSeconds(),
                request.playbackRate(),
                request.completed());
        boolean privileged = scopedVideoPrivilege(videoId, user);
        return videos.updateProgress(videoId, trusted, privileged);
    }

    @GetMapping("/internal/media/videos/{videoId}/playback-url")
    public PlaybackUrlDto playbackUrl(@PathVariable UUID videoId, @RequestParam(required = false) String protocol,
                                      CurrentUser user) {
        boolean privileged = scopedVideoPrivilege(videoId, user);
        return videos.playbackUrl(videoId, protocol, callerId(user), privileged);
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
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires course staff role");
        }
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole("ADMIN", "ORG_ADMIN", "TA", "INSTRUCTOR", "PROFESSOR");
    }

    private void requireVideoCourseStaffAccess(CurrentUser user, String courseId) {
        if (courseId == null || courseId.isBlank()) {
            requirePlatformAdmin(user);
            return;
        }
        courseAccess.requireCourseStaffAccess(user, UUID.fromString(courseId));
    }

    private boolean scopedVideoPrivilege(UUID videoId, CurrentUser user) {
        if (!isStaff(user)) {
            return false;
        }
        requireVideoCourseStaffAccess(user, videos.get(videoId).courseId());
        return true;
    }

    private void requirePlatformAdmin(CurrentUser user) {
        callerId(user);
        if (!user.hasRole("ADMIN")) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "courseId is required for course staff access");
        }
    }

}
