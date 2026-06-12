package edu.courseflow.media.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import java.time.Instant;

public final class MediaDtos {

    private MediaDtos() {
    }

    public record MediaAssetDto(
            String id,
            String ownerId,
            String fileName,
            String contentType,
            String storageKey,
            long sizeBytes,
            Instant createdAt
    ) {
    }

    public record RegisterMediaAssetRequestDto(
            String ownerId,
            @NotBlank String fileName,
            @NotBlank String contentType,
            @NotBlank String storageKey,
            @NotNull @PositiveOrZero Long sizeBytes
    ) {
    }

    /** Request a presigned PUT URL; the client uploads bytes directly to the object store. */
    public record RequestUploadUrlDto(
            String ownerId,
            @NotBlank String fileName,
            @NotBlank String contentType
    ) {
    }

    /** Presigned upload grant: the pre-generated {@code storageKey} plus the URL to PUT to. */
    public record PresignedUploadDto(
            String storageKey,
            String uploadUrl,
            Instant expiresAt
    ) {
    }

    /** Presigned download grant for an existing asset. */
    public record PresignedDownloadDto(
            String storageKey,
            String downloadUrl,
            Instant expiresAt
    ) {
    }
}
