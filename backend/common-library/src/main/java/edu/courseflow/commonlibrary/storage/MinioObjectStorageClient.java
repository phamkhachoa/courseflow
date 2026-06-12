package edu.courseflow.commonlibrary.storage;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import io.minio.GetPresignedObjectUrlArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.RemoveObjectArgs;
import io.minio.StatObjectArgs;
import io.minio.errors.ErrorResponseException;
import io.minio.http.Method;
import java.io.InputStream;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * MinIO-backed {@link ObjectStorageClient}. Server-side object operations use the
 * internal endpoint, while presigned URLs are signed directly against the external
 * endpoint so the signed {@code host} header matches what the browser calls.
 */
public class MinioObjectStorageClient implements ObjectStorageClient {

    private static final Logger log = LoggerFactory.getLogger(MinioObjectStorageClient.class);

    private final MinioClient client;
    private final MinioClient presignClient;
    private final ObjectStorageProperties props;

    public MinioObjectStorageClient(MinioClient client, MinioClient presignClient, ObjectStorageProperties props) {
        this.client = client;
        this.presignClient = presignClient;
        this.props = props;
    }

    @Override
    public String put(String key, InputStream data, long size, String contentType) {
        try {
            client.putObject(PutObjectArgs.builder()
                    .bucket(props.getBucket())
                    .object(key)
                    // size known -> single part; -1 size would need a part size, which we avoid here.
                    .stream(data, size, -1)
                    .contentType(contentType == null ? "application/octet-stream" : contentType)
                    .build());
            return key;
        } catch (Exception ex) {
            throw new BadRequestException("Failed to store object " + key + ": " + ex.getMessage());
        }
    }

    @Override
    public PresignedUrl presignPut(String key, String contentType) {
        return presign(Method.PUT, key, contentType);
    }

    @Override
    public PresignedUrl presignGet(String key) {
        return presign(Method.GET, key, null);
    }

    private PresignedUrl presign(Method method, String key, String contentType) {
        int ttl = props.getPresignTtlSeconds();
        try {
            GetPresignedObjectUrlArgs.Builder builder = GetPresignedObjectUrlArgs.builder()
                    .method(method)
                    .bucket(props.getBucket())
                    .object(key)
                    .expiry(ttl, TimeUnit.SECONDS);
            if (method == Method.PUT && contentType != null && !contentType.isBlank()) {
                builder.extraHeaders(Map.of("Content-Type", contentType));
            }
            String url = presignClient.getPresignedObjectUrl(builder.build());
            return new PresignedUrl(key, url, Instant.now().plus(ttl, ChronoUnit.SECONDS));
        } catch (Exception ex) {
            throw new BadRequestException("Failed to presign " + method + " for " + key + ": " + ex.getMessage());
        }
    }

    @Override
    public boolean exists(String key) {
        try {
            client.statObject(StatObjectArgs.builder()
                    .bucket(props.getBucket())
                    .object(key)
                    .build());
            return true;
        } catch (ErrorResponseException ex) {
            return false;
        } catch (Exception ex) {
            throw new BadRequestException("Failed to stat object " + key + ": " + ex.getMessage());
        }
    }

    @Override
    public void delete(String key) {
        try {
            client.removeObject(RemoveObjectArgs.builder()
                    .bucket(props.getBucket())
                    .object(key)
                    .build());
        } catch (Exception ex) {
            log.warn("Failed to delete object {}: {}", key, ex.getMessage());
        }
    }

    @Override
    public String buildKey(String prefix, String fileName) {
        String safe = sanitize(fileName);
        String name = UUID.randomUUID() + "-" + safe;
        if (prefix == null || prefix.isBlank()) {
            return name;
        }
        String cleanPrefix = prefix.replaceAll("^/+|/+$", "");
        return cleanPrefix + "/" + name;
    }

    private static String sanitize(String fileName) {
        String base = fileName == null || fileName.isBlank() ? "file" : fileName;
        // Strip path separators and keep a conservative key-safe charset.
        base = base.replace('\\', '/');
        int slash = base.lastIndexOf('/');
        if (slash >= 0) {
            base = base.substring(slash + 1);
        }
        base = base.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9._-]", "-");
        return base.isBlank() ? "file" : base;
    }
}
