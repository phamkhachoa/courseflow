package edu.courseflow.media.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.CourseAccessClient;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient.PresignedUrl;
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
import edu.courseflow.media.dto.VideoDtos.VideoRenditionDto;
import edu.courseflow.media.model.OutboxEvent;
import edu.courseflow.media.repository.OutboxEventRepository;
import edu.courseflow.media.repository.VideoRepository;
import jakarta.annotation.PostConstruct;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClient;

@Service
public class VideoService {

    private static final Logger log = LoggerFactory.getLogger(VideoService.class);
    private static final String KEY_PREFIX = "videos";
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final double COMPLETION_THRESHOLD = 0.9;
    private static final int COMPLETION_GRACE_SECONDS = 5;
    private static final Set<String> ALLOWED_SOURCE_CONTENT_TYPES = Set.of(
            "video/mp4", "video/webm", "video/quicktime");

    private final VideoRepository videos;
    private final OutboxEventRepository outboxEvents;
    private final ObjectMapper objectMapper;
    private final ObjectStorageClient storage;
    private final CourseAccessClient courseAccess;
    private final RestClient courseClient;
    private final InternalJwtService internalJwt;
    private final String storageProvider;
    private final String cdnBaseUrl;
    private final long signedUrlTtlSeconds;
    private final String signingSecret;
    private final boolean directSourcePlaybackEnabled;

    public VideoService(VideoRepository videos,
                        OutboxEventRepository outboxEvents,
                        ObjectMapper objectMapper,
                        ObjectStorageClient storage,
                        CourseAccessClient courseAccess,
                        RestClient.Builder restClientBuilder,
                        @Value("${courseflow.entitlement.course-service-url:http://course-service:8080}") String courseServiceUrl,
                        InternalJwtService internalJwt,
                        @Value("${courseflow.storage.provider:minio}") String storageProvider,
                        @Value("${courseflow.media.cdn-base-url:https://cdn.local/media}") String cdnBaseUrl,
                        @Value("${courseflow.media.signed-url-ttl-seconds:3600}") long signedUrlTtlSeconds,
                        @Value("${courseflow.media.signing-secret:}") String signingSecret,
                        @Value("${courseflow.media.direct-source-playback-enabled:true}") boolean directSourcePlaybackEnabled) {
        this.videos = videos;
        this.outboxEvents = outboxEvents;
        this.objectMapper = objectMapper;
        this.storage = storage;
        this.courseAccess = courseAccess;
        this.courseClient = restClientBuilder.baseUrl(courseServiceUrl).build();
        this.internalJwt = internalJwt;
        this.storageProvider = storageProvider;
        this.cdnBaseUrl = cdnBaseUrl;
        this.signedUrlTtlSeconds = signedUrlTtlSeconds;
        this.signingSecret = signingSecret == null ? "" : signingSecret.trim();
        this.directSourcePlaybackEnabled = directSourcePlaybackEnabled;
    }

    /**
     * Fail fast when the CDN fallback path could be used without a configured signing secret. Only the
     * non-MinIO provider mints HMAC tokens here, so we only hard-require the secret in that case — for
     * MinIO the object store issues real presigned URLs and no app-level secret is needed.
     */
    @PostConstruct
    void validateSigningSecret() {
        if (!"minio".equalsIgnoreCase(storageProvider) && signingSecret.isEmpty()) {
            throw new IllegalStateException(
                    "courseflow.media.signing-secret must be set when storage provider is '" + storageProvider
                            + "' (it signs playback URLs). Set MEDIA_SIGNING_SECRET.");
        }
    }

    @Transactional
    public VideoAssetDto register(RegisterVideoRequestDto request, String ownerId) {
        validateOwnedStorageKey(ownerId, request.sourceStorageKey());
        if (!storage.exists(request.sourceStorageKey())) {
            throw new BadRequestException("Uploaded source video does not exist: " + request.sourceStorageKey());
        }
        VideoAssetDto video = videos.register(request);
        if (canPlaySourceDirectly(video)) {
            videos.updateStatus(UUID.fromString(video.id()), "READY");
            return get(UUID.fromString(video.id()));
        }
        return video;
    }

    public VideoAssetDto get(UUID videoId) {
        return videos.find(videoId)
                .map(this::withEffectiveStatus)
                .orElseThrow(() -> new NotFoundException("Video not found: " + videoId));
    }

    public VideoReadinessDto readiness(UUID videoId) {
        VideoAssetDto video = get(videoId);
        String status = effectiveStatus(video);
        return new VideoReadinessDto(
                video.id(),
                video.courseId(),
                status,
                "READY".equalsIgnoreCase(status));
    }

    public List<VideoAssetDto> list(UUID courseId) {
        return videos.list(courseId == null ? Optional.empty() : Optional.of(courseId)).stream()
                .map(this::withEffectiveStatus)
                .toList();
    }

    public VideoAssetDto get(UUID videoId, String requesterId, boolean privileged) {
        VideoAssetDto video = get(videoId);
        requireVideoAccess(video, requesterId, privileged);
        return video;
    }

    /**
     * Queue an async transcode job. A separate transcode worker consumes transcode_jobs,
     * produces HLS/DASH renditions, persists them, then marks the video READY and emits
     * media.transcode.completed. Here we only enqueue and flip status to TRANSCODING.
     */
    @Transactional
    public VideoAssetDto startTranscode(UUID videoId, StartTranscodeRequestDto request) {
        VideoAssetDto video = get(videoId);
        UUID jobId = videos.createTranscodeJob(videoId, request.requestedBy());
        videos.updateStatus(videoId, "TRANSCODING");
        saveOutbox(videoId, "media.transcode.requested", Map.of(
                "videoId", videoId.toString(),
                "jobId", jobId.toString(),
                "courseId", video.courseId() == null ? "" : video.courseId(),
                "sourceStorageKey", video.sourceStorageKey()));
        return get(videoId);
    }

    public VideoManifestDto manifest(UUID videoId, String protocol, String requesterId, boolean privileged) {
        VideoAssetDto video = get(videoId, requesterId, privileged);
        String proto = protocol == null ? "HLS" : protocol.toUpperCase();
        List<edu.courseflow.media.dto.VideoDtos.VideoRenditionDto> renditions = video.renditions().stream()
                .filter(r -> r.protocol().equalsIgnoreCase(proto))
                .toList();
        return new VideoManifestDto(video.id(), proto, effectiveStatus(video), renditions, video.captions());
    }

    public List<VideoCaptionDto> captions(UUID videoId, String requesterId, boolean privileged) {
        return get(videoId, requesterId, privileged).captions();
    }

    @Transactional
    public VideoProgressDto updateProgress(UUID videoId, UpdateProgressRequestDto request, boolean privileged) {
        VideoAssetDto video = get(videoId, request.userId(), privileged);
        UpdateProgressRequestDto trusted = trustedProgress(video, request);
        VideoProgressDto progress = videos.upsertProgress(videoId, trusted);
        if (progress.completed()) {
            saveOutbox(videoId, "video.progress.updated", Map.of(
                    "eventId", UUID.randomUUID().toString(),
                    "videoId", videoId.toString(),
                    "courseId", video.courseId() == null ? "" : video.courseId(),
                    "userId", trusted.userId(),
                    "positionSeconds", progress.positionSeconds(),
                    "durationSeconds", progress.durationSeconds() == null ? 0 : progress.durationSeconds(),
                    "completed", true,
                    "completedAt", progress.updatedAt().toString()));
            recordCourseVideoCompletion(video, trusted.userId(), progress.updatedAt());
        }
        return progress;
    }

    public VideoProgressDto getProgress(UUID videoId, String userId, boolean privileged) {
        get(videoId, userId, privileged);
        return videos.findProgress(videoId, userId)
                .orElse(new VideoProgressDto(videoId.toString(), userId, 0, null, 1.0, false, Instant.now()));
    }

    private UpdateProgressRequestDto trustedProgress(VideoAssetDto video, UpdateProgressRequestDto request) {
        int positionSeconds = Math.max(0, request.positionSeconds() == null ? 0 : request.positionSeconds());
        Integer durationSeconds = request.durationSeconds() == null ? video.durationSeconds() : request.durationSeconds();
        double playbackRate = request.playbackRate() == null || request.playbackRate() <= 0
                ? 1.0
                : request.playbackRate();
        boolean completed = Boolean.TRUE.equals(request.completed())
                && completionThresholdMet(positionSeconds, durationSeconds);
        return new UpdateProgressRequestDto(
                request.userId(),
                positionSeconds,
                durationSeconds,
                playbackRate,
                completed);
    }

    private boolean completionThresholdMet(int positionSeconds, Integer durationSeconds) {
        if (durationSeconds == null || durationSeconds <= 0) {
            return false;
        }
        int remaining = Math.max(0, durationSeconds - positionSeconds);
        return remaining <= COMPLETION_GRACE_SECONDS
                || positionSeconds >= Math.ceil(durationSeconds * COMPLETION_THRESHOLD);
    }

    private void recordCourseVideoCompletion(VideoAssetDto video, String userId, Instant completedAt) {
        if (video.courseId() == null || video.courseId().isBlank()) {
            return;
        }
        try {
            courseClient.post()
                    .uri("/internal/courses/{courseId}/modules/items/progress/verified", video.courseId())
                    .headers(internalJwt::applyServiceToken)
                    .body(Map.of(
                            "studentId", userId,
                            "sourceType", "VIDEO",
                            "sourceId", video.id(),
                            "completedAt", completedAt.toString()))
                    .retrieve()
                    .toBodilessEntity();
        } catch (RuntimeException ex) {
            log.warn("Unable to record verified course progress for video {} and learner {}: {}",
                    video.id(), userId, ex.getMessage());
        }
    }

    /**
     * Issue a short-lived playback URL. With the MinIO provider this is a real presigned GET URL
     * for the selected rendition's manifest (or the source object if no rendition exists yet).
     * For any other provider it falls back to a CDN path with a placeholder token.
     */
    public PlaybackUrlDto playbackUrl(UUID videoId, String protocol, String requesterId, boolean privileged) {
        VideoAssetDto video = get(videoId, requesterId, privileged);
        String proto = protocol == null ? "hls" : protocol.toLowerCase();

        if ("minio".equalsIgnoreCase(storageProvider)) {
            String key = resolvePlaybackKey(video, proto);
            PresignedUrl presigned = storage.presignGet(key);
            return new PlaybackUrlDto(video.id(), presigned.url(), presigned.expiresAt());
        }

        Instant expiresAt = Instant.now().plus(Duration.ofSeconds(signedUrlTtlSeconds));
        String manifestName = "hls".equals(proto) ? "master.m3u8" : "manifest.mpd";
        String token = signToken(video.id(), expiresAt.getEpochSecond());
        String url = "%s/%s/%s?token=%s&expires=%d".formatted(
                cdnBaseUrl, video.id(), manifestName, token, expiresAt.getEpochSecond());
        return new PlaybackUrlDto(video.id(), url, expiresAt);
    }

    /**
     * Verify a playback token previously minted by {@link #signToken}. Used by the edge/CDN-facing
     * handler before serving bytes on the non-MinIO path. Returns false for a tampered token or one
     * whose {@code expires} timestamp is in the past. Constant-time comparison avoids timing oracles.
     */
    public boolean verifyPlaybackToken(String videoId, long expiresEpochSeconds, String token) {
        if (token == null || token.isBlank()) {
            return false;
        }
        if (Instant.now().getEpochSecond() > expiresEpochSeconds) {
            return false;
        }
        String expected = signToken(videoId, expiresEpochSeconds);
        return MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8), token.getBytes(StandardCharsets.UTF_8));
    }

    /** Prefer a rendition manifest for the requested protocol; otherwise serve the source object. */
    private String resolvePlaybackKey(VideoAssetDto video, String proto) {
        return video.renditions().stream()
                .filter(r -> r.protocol().equalsIgnoreCase(proto))
                .map(VideoRenditionDto::storageKey)
                .findFirst()
                .orElse(video.sourceStorageKey());
    }

    private String effectiveStatus(VideoAssetDto video) {
        if (canServeSourceAsReady(video)) {
            return "READY";
        }
        return video.status();
    }

    private VideoAssetDto withEffectiveStatus(VideoAssetDto video) {
        String status = effectiveStatus(video);
        if (status.equals(video.status())) {
            return video;
        }
        return new VideoAssetDto(
                video.id(),
                video.mediaAssetId(),
                video.courseId(),
                video.title(),
                video.sourceStorageKey(),
                video.durationSeconds(),
                status,
                video.createdAt(),
                video.renditions(),
                video.captions());
    }

    private boolean canServeSourceAsReady(VideoAssetDto video) {
        return video != null
                && !"FAILED".equalsIgnoreCase(video.status())
                && canPlaySourceDirectly(video);
    }

    private boolean canPlaySourceDirectly(VideoAssetDto video) {
        if (!directSourcePlaybackEnabled || video == null || video.sourceStorageKey() == null) {
            return false;
        }
        String key = video.sourceStorageKey().toLowerCase();
        return key.endsWith(".mp4") || key.endsWith(".m4v") || key.endsWith(".webm");
    }

    /** Presigned PUT URL for uploading a source video file directly to the object store. */
    public PresignedUploadDto requestSourceUploadUrl(RequestUploadUrlDto request, String ownerId) {
        validateContentType(request.contentType());
        String key = storage.buildKey(ownerPrefix(ownerId), request.fileName());
        PresignedUrl presigned = storage.presignPut(key, request.contentType());
        return new PresignedUploadDto(presigned.storageKey(), presigned.url(), presigned.expiresAt());
    }

    private void requireVideoAccess(VideoAssetDto video, String requesterId, boolean privileged) {
        if (privileged) {
            return;
        }
        if (isOwnedStorageKey(requesterId, video.sourceStorageKey())) {
            return;
        }
        if (video.courseId() != null && !video.courseId().isBlank()) {
            courseAccess.requireStudentCourseAccess(requesterId, UUID.fromString(video.courseId()));
            return;
        }
        throw new ForbiddenException("Not allowed to access video " + video.id());
    }

    private void validateContentType(String contentType) {
        String normalized = normalizeContentType(contentType);
        if (!ALLOWED_SOURCE_CONTENT_TYPES.contains(normalized)) {
            throw new BadRequestException("Video content type not allowed: " + contentType);
        }
    }

    private String normalizeContentType(String contentType) {
        String normalized = contentType == null ? "" : contentType.trim().toLowerCase();
        int paramIdx = normalized.indexOf(';');
        return paramIdx >= 0 ? normalized.substring(0, paramIdx).trim() : normalized;
    }

    private void validateOwnedStorageKey(String ownerId, String storageKey) {
        String prefix = ownerPrefix(ownerId) + "/";
        if (storageKey == null || !storageKey.startsWith(prefix)) {
            throw new BadRequestException("Video storage key is not owned by the authenticated user");
        }
    }

    private boolean isOwnedStorageKey(String ownerId, String storageKey) {
        if (ownerId == null || ownerId.isBlank() || storageKey == null) {
            return false;
        }
        return storageKey.startsWith(ownerPrefix(ownerId) + "/");
    }

    private String ownerPrefix(String ownerId) {
        if (ownerId == null || ownerId.isBlank()) {
            throw new BadRequestException("Owner id is required");
        }
        return KEY_PREFIX + "/" + ownerId.replaceAll("[^A-Za-z0-9._-]", "-");
    }

    /**
     * Mint an unforgeable playback token by HMAC-SHA256 over the canonical "videoId:expires" string,
     * keyed with a server-side secret. The previous implementation used {@code hashCode()} of the same
     * inputs, which any client can recompute — so anyone could forge a valid token for any video and any
     * expiry. HMAC requires the secret to produce or verify a token, closing that hole.
     */
    private String signToken(String videoId, long expiresEpochSeconds) {
        String canonical = videoId + ":" + expiresEpochSeconds;
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(signingSecret.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
            byte[] raw = mac.doFinal(canonical.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(raw);
        } catch (GeneralSecurityException ex) {
            throw new IllegalStateException("Unable to sign playback token", ex);
        }
    }

    private void saveOutbox(UUID aggregateId, String eventType, Map<String, ?> payload) {
        outboxEvents.save(new OutboxEvent(aggregateId, "video", eventType, toJson(payload)));
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }
}
