package edu.courseflow.media.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "video_renditions")
public class VideoRendition {

    @Id
    private UUID id;

    @Column(name = "video_id", nullable = false)
    private UUID videoId;

    @Column(nullable = false, length = 20)
    private String protocol;

    @Column(nullable = false, length = 40)
    private String label;

    private Integer width;
    private Integer height;

    @Column(name = "bitrate_kbps")
    private Integer bitrateKbps;

    @Column(name = "storage_key", nullable = false, length = 512)
    private String storageKey;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected VideoRendition() {
    }

    public UUID getId() { return id; }
    public String getProtocol() { return protocol; }
    public String getLabel() { return label; }
    public Integer getWidth() { return width; }
    public Integer getHeight() { return height; }
    public Integer getBitrateKbps() { return bitrateKbps; }
    public String getStorageKey() { return storageKey; }
}
