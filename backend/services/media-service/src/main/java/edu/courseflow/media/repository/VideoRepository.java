package edu.courseflow.media.repository;

import edu.courseflow.media.dto.VideoDtos.RegisterVideoRequestDto;
import edu.courseflow.media.dto.VideoDtos.UpdateProgressRequestDto;
import edu.courseflow.media.dto.VideoDtos.VideoAssetDto;
import edu.courseflow.media.dto.VideoDtos.VideoCaptionDto;
import edu.courseflow.media.dto.VideoDtos.VideoProgressDto;
import edu.courseflow.media.dto.VideoDtos.VideoRenditionDto;
import edu.courseflow.media.mapper.MediaMapper;
import edu.courseflow.media.model.TranscodeJob;
import edu.courseflow.media.model.VideoAsset;
import edu.courseflow.media.model.VideoProgress;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class VideoRepository {

    private final VideoAssetJpaRepository videos;
    private final VideoRenditionJpaRepository renditions;
    private final VideoCaptionJpaRepository captions;
    private final VideoProgressJpaRepository progress;
    private final TranscodeJobJpaRepository transcodeJobs;
    private final MediaMapper mapper;

    public VideoRepository(VideoAssetJpaRepository videos,
            VideoRenditionJpaRepository renditions,
            VideoCaptionJpaRepository captions,
            VideoProgressJpaRepository progress,
            TranscodeJobJpaRepository transcodeJobs,
            MediaMapper mapper) {
        this.videos = videos;
        this.renditions = renditions;
        this.captions = captions;
        this.progress = progress;
        this.transcodeJobs = transcodeJobs;
        this.mapper = mapper;
    }

    public VideoAssetDto register(RegisterVideoRequestDto request) {
        return toVideoAssetDto(videos.save(new VideoAsset(request)));
    }

    public List<VideoAssetDto> list(Optional<UUID> courseId) {
        List<VideoAsset> rows = courseId
                .map(videos::findByCourseIdOrderByCreatedAtDesc)
                .orElseGet(videos::findAllByOrderByCreatedAtDesc);
        return rows.stream().map(this::toVideoAssetDto).toList();
    }

    public Optional<VideoAssetDto> find(UUID videoId) {
        return videos.findById(videoId).map(this::toVideoAssetDto);
    }

    public List<VideoRenditionDto> listRenditions(UUID videoId) {
        return renditions.findByVideoIdOrderByBitrateKbpsAsc(videoId).stream()
                .map(mapper::toDto)
                .toList();
    }

    public List<VideoCaptionDto> listCaptions(UUID videoId) {
        return captions.findByVideoIdOrderByLanguageAsc(videoId).stream()
                .map(mapper::toDto)
                .toList();
    }

    public void updateStatus(UUID videoId, String status) {
        videos.findById(videoId).ifPresent(video -> {
            video.updateStatus(status);
            videos.save(video);
        });
    }

    public UUID createTranscodeJob(UUID videoId, String requestedBy) {
        return transcodeJobs.save(new TranscodeJob(videoId, requestedBy)).getId();
    }

    public VideoProgressDto upsertProgress(UUID videoId, UpdateProgressRequestDto request) {
        VideoProgress row = progress.findByVideoIdAndUserId(videoId, request.userId())
                .orElseGet(() -> new VideoProgress(videoId, request));
        row.updateFrom(request);
        return mapper.toDto(progress.save(row));
    }

    public Optional<VideoProgressDto> findProgress(UUID videoId, String userId) {
        return progress.findByVideoIdAndUserId(videoId, userId).map(mapper::toDto);
    }

    private VideoAssetDto toVideoAssetDto(VideoAsset video) {
        return mapper.toDto(video, listRenditions(video.getId()), listCaptions(video.getId()));
    }
}
