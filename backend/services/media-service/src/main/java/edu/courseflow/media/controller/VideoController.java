package edu.courseflow.media.controller;

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

    public VideoController(VideoService videos) {
        this.videos = videos;
    }

    @PostMapping("/internal/media/videos")
    public VideoAssetDto register(@Valid @RequestBody RegisterVideoRequestDto request, CurrentUser user) {
        requireStaff(user);
        return videos.register(request, callerId(user));
    }

    @GetMapping("/internal/media/videos")
    public List<VideoAssetDto> list(@RequestParam(required = false) UUID courseId, CurrentUser user) {
        requireStaff(user);
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
        return videos.get(videoId, callerId(user), isStaff(user));
    }

    @PostMapping("/internal/media/videos/{videoId}/transcode")
    public VideoAssetDto transcode(@PathVariable UUID videoId, @Valid @RequestBody StartTranscodeRequestDto request,
                                   CurrentUser user) {
        requireStaff(user);
        return videos.startTranscode(videoId, new StartTranscodeRequestDto(callerId(user)));
    }

    @GetMapping("/internal/media/videos/{videoId}/manifest")
    public VideoManifestDto manifest(@PathVariable UUID videoId, @RequestParam(required = false) String protocol,
                                     CurrentUser user) {
        return videos.manifest(videoId, protocol, callerId(user), isStaff(user));
    }

    @GetMapping("/internal/media/videos/{videoId}/captions")
    public List<VideoCaptionDto> captions(@PathVariable UUID videoId, CurrentUser user) {
        return videos.captions(videoId, callerId(user), isStaff(user));
    }

    @GetMapping("/internal/media/videos/{videoId}/progress")
    public VideoProgressDto getProgress(@PathVariable UUID videoId, CurrentUser user) {
        return videos.getProgress(videoId, callerId(user), isStaff(user));
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
        return videos.updateProgress(videoId, trusted, isStaff(user));
    }

    @GetMapping("/internal/media/videos/{videoId}/playback-url")
    public PlaybackUrlDto playbackUrl(@PathVariable UUID videoId, @RequestParam(required = false) String protocol,
                                      CurrentUser user) {
        return videos.playbackUrl(videoId, protocol, callerId(user), isStaff(user));
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
