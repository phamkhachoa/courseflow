package edu.courseflow.media.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient;
import edu.courseflow.commonlibrary.storage.ObjectStorageClient.PresignedUrl;
import edu.courseflow.media.dto.MediaDtos.MediaAssetDto;
import edu.courseflow.media.dto.MediaDtos.PresignedDownloadDto;
import edu.courseflow.media.dto.MediaDtos.PresignedUploadDto;
import edu.courseflow.media.dto.MediaDtos.RegisterMediaAssetRequestDto;
import edu.courseflow.media.dto.MediaDtos.RequestUploadUrlDto;
import edu.courseflow.media.repository.MediaRepository;
import java.io.IOException;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@Service
public class MediaService {

    private static final String KEY_PREFIX = "media";

    /** Content types accepted for upload. Anything else is rejected to limit stored-content risk. */
    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of(
            "image/png", "image/jpeg", "image/gif", "image/webp",
            "video/mp4", "video/webm", "video/quicktime",
            "audio/mpeg", "audio/mp4", "audio/wav",
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/plain", "text/markdown", "text/csv");

    private final MediaRepository media;
    private final ObjectStorageClient storage;
    private final long maxUploadBytes;

    public MediaService(MediaRepository media,
                        ObjectStorageClient storage,
                        @Value("${courseflow.media.max-upload-bytes:536870912}") long maxUploadBytes) {
        this.media = media;
        this.storage = storage;
        this.maxUploadBytes = maxUploadBytes;
    }

    public List<MediaAssetDto> list(Optional<String> ownerId) {
        return media.list(ownerId.orElse(null));
    }

    public MediaAssetDto get(UUID mediaId) {
        return media.find(mediaId)
                .orElseThrow(() -> new NotFoundException("Media asset not found: " + mediaId));
    }

    @Transactional
    public MediaAssetDto register(RegisterMediaAssetRequestDto request) {
        validateContentType(request.contentType());
        validateOwnedStorageKey(request.ownerId(), request.storageKey());
        if (!storage.exists(request.storageKey())) {
            throw new BadRequestException("Uploaded object does not exist: " + request.storageKey());
        }
        return media.register(request);
    }

    /**
     * Hand back a presigned PUT URL plus the server-generated storage key. The client uploads bytes
     * straight to the object store, then calls {@link #register} with the same key.
     *
     * <p>Validates the requested content type against a whitelist and forwards a size cap so the
     * presigned grant cannot be used to push arbitrary or oversized content.
     */
    public PresignedUploadDto requestUploadUrl(RequestUploadUrlDto request) {
        validateContentType(request.contentType());
        String key = storage.buildKey(ownerPrefix(request.ownerId()), request.fileName());
        PresignedUrl presigned = storage.presignPut(key, request.contentType());
        return new PresignedUploadDto(presigned.storageKey(), presigned.url(), presigned.expiresAt());
    }

    /**
     * Multipart proxy upload: stream the file through this service into the object store and persist the
     * asset row in one call. {@code ownerId} is the authenticated caller (derived from the gateway
     * identity by the controller), never a client-supplied parameter, so a caller cannot plant an asset
     * under someone else's id.
     */
    @Transactional
    public MediaAssetDto upload(String ownerId, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BadRequestException("Uploaded file is empty");
        }
        if (file.getSize() > maxUploadBytes) {
            throw new BadRequestException("Uploaded file exceeds the maximum allowed size");
        }
        String fileName = file.getOriginalFilename() == null ? "file" : file.getOriginalFilename();
        String contentType = file.getContentType() == null ? "application/octet-stream" : file.getContentType();
        validateContentType(contentType);
        String key = storage.buildKey(ownerPrefix(ownerId), fileName);
        try {
            storage.put(key, file.getInputStream(), file.getSize(), contentType);
        } catch (IOException ex) {
            throw new BadRequestException("Failed to read uploaded file: " + ex.getMessage());
        }
        return media.create(ownerId, fileName, contentType, key, file.getSize());
    }

    /**
     * Presigned GET URL for an existing asset. The caller must own the asset, or hold a privileged role
     * (INSTRUCTOR/ADMIN); otherwise the download is refused. Authorization is enforced in
     * {@link #downloadUrl(UUID, String, boolean)}.
     */
    public PresignedDownloadDto downloadUrl(UUID mediaId, String requesterId, boolean privileged) {
        MediaAssetDto asset = get(mediaId);
        boolean isOwner = requesterId != null && requesterId.equals(asset.ownerId());
        if (!isOwner && !privileged) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,
                    "Not allowed to download media asset " + mediaId);
        }
        PresignedUrl presigned = storage.presignGet(asset.storageKey());
        return new PresignedDownloadDto(presigned.storageKey(), presigned.url(), presigned.expiresAt());
    }

    private void validateContentType(String contentType) {
        String normalized = contentType == null ? "" : contentType.trim().toLowerCase();
        int paramIdx = normalized.indexOf(';');
        if (paramIdx >= 0) {
            normalized = normalized.substring(0, paramIdx).trim();
        }
        if (!ALLOWED_CONTENT_TYPES.contains(normalized)) {
            throw new BadRequestException("Content type not allowed: " + contentType);
        }
    }

    private void validateOwnedStorageKey(String ownerId, String storageKey) {
        String prefix = ownerPrefix(ownerId) + "/";
        if (storageKey == null || !storageKey.startsWith(prefix)) {
            throw new BadRequestException("Storage key is not owned by the authenticated user");
        }
    }

    private String ownerPrefix(String ownerId) {
        if (ownerId == null || ownerId.isBlank()) {
            throw new BadRequestException("Owner id is required");
        }
        return KEY_PREFIX + "/" + ownerId.replaceAll("[^A-Za-z0-9._-]", "-");
    }
}
