package edu.courseflow.commonlibrary.storage;

import java.io.InputStream;
import java.time.Instant;

/**
 * Minimal object-storage abstraction shared by services that own file/media pointers
 * ({@code storage_key} columns). Backed by MinIO today; the interface stays S3-agnostic
 * so the backend can move to S3/GCS without touching callers.
 */
public interface ObjectStorageClient {

    /** Result of a presign operation: the object key plus a time-limited URL. */
    record PresignedUrl(String storageKey, String url, Instant expiresAt) {
    }

    /**
     * Stream bytes into the default bucket under {@code key} and return the stored key.
     * Used by the multipart upload proxy path.
     */
    String put(String key, InputStream data, long size, String contentType);

    /** Issue a time-limited URL the client can PUT to directly (browser/CLI upload). */
    PresignedUrl presignPut(String key, String contentType);

    /** Issue a time-limited URL the client can GET to download the object directly. */
    PresignedUrl presignGet(String key);

    /** True if an object exists at {@code key}. */
    boolean exists(String key);

    /** Remove the object at {@code key} (no-op if absent). */
    void delete(String key);

    /**
     * Build a collision-resistant storage key like {@code prefix/<uuid>-<safeFileName>}.
     * {@code prefix} groups objects (e.g. {@code media}, {@code submissions}); a null/blank
     * prefix omits the leading segment.
     */
    String buildKey(String prefix, String fileName);
}
