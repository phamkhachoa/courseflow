package edu.courseflow.commonlibrary.storage;

import io.minio.MinioClient;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Wires a {@link MinioObjectStorageClient} when MinIO is on the classpath and
 * {@code courseflow.storage.provider=minio} (the default). Services on the shared
 * component scan ({@code edu.courseflow}) pick this up automatically; services that
 * don't depend on the MinIO SDK skip it via {@link ConditionalOnClass}.
 */
@Configuration
@ConditionalOnClass(MinioClient.class)
@ConditionalOnProperty(prefix = "courseflow.storage", name = "provider", havingValue = "minio", matchIfMissing = true)
@EnableConfigurationProperties(ObjectStorageProperties.class)
public class StorageAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public MinioClient minioClient(ObjectStorageProperties props) {
        validateCredentials(props);
        return MinioClient.builder()
                .endpoint(props.getEndpoint())
                .region(props.getRegion())
                .credentials(props.getAccessKey(), props.getSecretKey())
                .build();
    }

    @Bean
    @ConditionalOnMissingBean
    public ObjectStorageClient objectStorageClient(MinioClient client, ObjectStorageProperties props) {
        MinioClient presignClient = MinioClient.builder()
                .endpoint(props.getExternalEndpoint())
                .region(props.getRegion())
                .credentials(props.getAccessKey(), props.getSecretKey())
                .build();
        return new MinioObjectStorageClient(client, presignClient, props);
    }

    private void validateCredentials(ObjectStorageProperties props) {
        String accessKey = props.getAccessKey();
        String secretKey = props.getSecretKey();
        if (accessKey == null || accessKey.isBlank() || secretKey == null || secretKey.isBlank()) {
            throw new IllegalStateException("MinIO credentials must be configured explicitly");
        }
        boolean demoPair = "courseflow".equals(accessKey) && "courseflow".equals(secretKey);
        if (demoPair && !props.isAllowDemoCredentials()) {
            throw new IllegalStateException(
                    "Refusing demo MinIO credentials; set courseflow.storage.allow-demo-credentials=true only for local/demo");
        }
    }
}
