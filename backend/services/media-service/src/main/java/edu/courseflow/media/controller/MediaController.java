package edu.courseflow.media.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.media.dto.MediaDtos.MediaAssetDto;
import edu.courseflow.media.dto.MediaDtos.PresignedDownloadDto;
import edu.courseflow.media.dto.MediaDtos.PresignedUploadDto;
import edu.courseflow.media.dto.MediaDtos.RegisterMediaAssetRequestDto;
import edu.courseflow.media.dto.MediaDtos.RequestUploadUrlDto;
import edu.courseflow.media.service.MediaService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class MediaController {

    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_INSTRUCTOR = "INSTRUCTOR";

    private final MediaService media;

    public MediaController(MediaService media) {
        this.media = media;
    }

    @GetMapping("/internal/media/assets")
    public List<MediaAssetDto> list(@RequestParam Optional<String> ownerId, CurrentUser user) {
        String callerId = requireUserId(user);
        if (!user.hasAnyRole(ROLE_ADMIN, ROLE_INSTRUCTOR)) {
            return media.list(Optional.of(callerId));
        }
        return media.list(ownerId);
    }

    @PostMapping("/internal/media/assets")
    public MediaAssetDto register(@Valid @RequestBody RegisterMediaAssetRequestDto request, CurrentUser user) {
        RegisterMediaAssetRequestDto trusted = new RegisterMediaAssetRequestDto(
                requireUserId(user),
                request.fileName(),
                request.contentType(),
                request.storageKey(),
                request.sizeBytes());
        return media.register(trusted);
    }

    @GetMapping("/internal/media/assets/{mediaId}")
    public MediaAssetDto get(@PathVariable UUID mediaId, CurrentUser user) {
        MediaAssetDto asset = media.get(mediaId);
        String requesterId = requireUserId(user);
        if (!requesterId.equals(asset.ownerId()) && !user.hasAnyRole(ROLE_ADMIN, ROLE_INSTRUCTOR)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to read media asset " + mediaId);
        }
        return asset;
    }

    /** Presigned PUT URL: client uploads bytes directly to the object store, then registers. */
    @PostMapping("/internal/media/assets/upload-url")
    public PresignedUploadDto uploadUrl(@Valid @RequestBody RequestUploadUrlDto request, CurrentUser user) {
        RequestUploadUrlDto trusted = new RequestUploadUrlDto(requireUserId(user), request.fileName(), request.contentType());
        return media.requestUploadUrl(trusted);
    }

    /**
     * Multipart proxy upload: stream the file through the service and persist the asset. The owner is the
     * authenticated caller from the gateway identity, never a client-supplied parameter, so an asset
     * cannot be planted under another user's id.
     */
    @PostMapping(value = "/internal/media/assets/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public MediaAssetDto upload(@RequestPart("file") MultipartFile file, CurrentUser user) {
        return media.upload(requireUserId(user), file);
    }

    /**
     * Presigned GET URL for downloading an existing asset. Only the owner or a privileged role
     * (INSTRUCTOR/ADMIN) may obtain it; the service enforces the ownership/role check.
     */
    @GetMapping("/internal/media/assets/{mediaId}/download-url")
    public PresignedDownloadDto downloadUrl(@PathVariable UUID mediaId, CurrentUser user) {
        String requesterId = requireUserId(user);
        boolean privileged = user.hasAnyRole(ROLE_ADMIN, ROLE_INSTRUCTOR);
        return media.downloadUrl(mediaId, requesterId, privileged);
    }

    private String requireUserId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated user required");
        }
        return String.valueOf(user.id());
    }
}
