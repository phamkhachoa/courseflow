package edu.courseflow.commonlibrary.storage;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Configuration for the shared object store (MinIO / any S3-compatible backend).
 *
 * <p>{@code endpoint} is what the service uses to talk to the store server-to-server
 * (e.g. {@code http://localhost:9000} locally, or an internal DNS name in a cluster).
 * {@code externalEndpoint} is the host baked into presigned URLs handed back to clients;
 * it defaults to {@code endpoint} but can differ when the browser reaches MinIO on a
 * different address than the backend does.
 */
@ConfigurationProperties(prefix = "courseflow.storage")
public class ObjectStorageProperties {

    /** Active provider. Storage beans are only created when this is {@code minio}. */
    private String provider = "minio";

    /** Server-to-server S3 API endpoint. */
    private String endpoint = "http://localhost:9000";

    /** Optional host used when building presigned URLs for clients. Falls back to {@link #endpoint}. */
    private String externalEndpoint;

    private String accessKey;

    private String secretKey;

    private boolean allowDemoCredentials = false;

    /** Default bucket this service reads/writes. */
    private String bucket = "courseflow-media";

    /** S3 signing region. MinIO commonly uses us-east-1 for local deployments. */
    private String region = "us-east-1";

    /** Lifetime of presigned upload/download URLs. */
    private int presignTtlSeconds = 3600;

    public String getProvider() {
        return provider;
    }

    public void setProvider(String provider) {
        this.provider = provider;
    }

    public String getEndpoint() {
        return endpoint;
    }

    public void setEndpoint(String endpoint) {
        this.endpoint = endpoint;
    }

    public String getExternalEndpoint() {
        return externalEndpoint == null || externalEndpoint.isBlank() ? endpoint : externalEndpoint;
    }

    public void setExternalEndpoint(String externalEndpoint) {
        this.externalEndpoint = externalEndpoint;
    }

    public String getAccessKey() {
        return accessKey;
    }

    public void setAccessKey(String accessKey) {
        this.accessKey = accessKey;
    }

    public String getSecretKey() {
        return secretKey;
    }

    public void setSecretKey(String secretKey) {
        this.secretKey = secretKey;
    }

    public boolean isAllowDemoCredentials() {
        return allowDemoCredentials;
    }

    public void setAllowDemoCredentials(boolean allowDemoCredentials) {
        this.allowDemoCredentials = allowDemoCredentials;
    }

    public String getBucket() {
        return bucket;
    }

    public void setBucket(String bucket) {
        this.bucket = bucket;
    }

    public String getRegion() {
        return region;
    }

    public void setRegion(String region) {
        this.region = region;
    }

    public int getPresignTtlSeconds() {
        return presignTtlSeconds;
    }

    public void setPresignTtlSeconds(int presignTtlSeconds) {
        this.presignTtlSeconds = presignTtlSeconds;
    }
}
