package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "module_items")
public class ModuleItem {

    @Id
    private UUID id;

    @Column(name = "module_id", nullable = false)
    private UUID moduleId;

    @Column(name = "item_type", nullable = false, length = 60)
    private String itemType;

    @Column(name = "item_id", nullable = false, length = 120)
    private String itemId;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "video_media_id")
    private UUID videoMediaId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "document_media_ids", columnDefinition = "jsonb")
    private List<String> documentMediaIds = List.of();

    @Column(name = "content_url")
    private String contentUrl;

    @Column(name = "estimated_minutes")
    private Integer estimatedMinutes;

    @Column(nullable = false)
    private int position;

    @Column(nullable = false)
    private boolean required = true;

    @Column(nullable = false, length = 40)
    private String status = "ACTIVE";

    protected ModuleItem() {
    }

    public ModuleItem(UUID id, UUID moduleId, String itemType, String itemId,
            String title, String description, UUID videoMediaId, List<String> documentMediaIds,
            String contentUrl, Integer estimatedMinutes, int position, boolean required) {
        this.id = id;
        this.moduleId = moduleId;
        this.itemType = itemType;
        this.itemId = itemId;
        this.title = title;
        this.description = description;
        this.videoMediaId = videoMediaId;
        this.documentMediaIds = documentMediaIds == null ? List.of() : List.copyOf(documentMediaIds);
        this.contentUrl = contentUrl;
        this.estimatedMinutes = estimatedMinutes;
        this.position = position;
        this.required = required;
        this.status = "ACTIVE";
    }

    public UUID getId() {
        return id;
    }

    public UUID getModuleId() {
        return moduleId;
    }

    public String getItemType() {
        return itemType;
    }

    public String getItemId() {
        return itemId;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public UUID getVideoMediaId() {
        return videoMediaId;
    }

    public List<String> getDocumentMediaIds() {
        return documentMediaIds == null ? List.of() : documentMediaIds;
    }

    public String getContentUrl() {
        return contentUrl;
    }

    public Integer getEstimatedMinutes() {
        return estimatedMinutes;
    }

    public int getPosition() {
        return position;
    }

    public void setPosition(int position) {
        this.position = position;
    }

    public boolean isRequired() {
        return required;
    }

    public String getStatus() {
        return status;
    }

    public void restoreDraft(UUID moduleId, String itemType, String itemId, String title, String description,
            UUID videoMediaId, List<String> documentMediaIds, String contentUrl,
            Integer estimatedMinutes, int position, boolean required) {
        this.moduleId = moduleId;
        this.itemType = itemType;
        this.itemId = itemId;
        this.title = title;
        this.description = description;
        this.videoMediaId = videoMediaId;
        this.documentMediaIds = documentMediaIds == null ? List.of() : List.copyOf(documentMediaIds);
        this.contentUrl = contentUrl;
        this.estimatedMinutes = estimatedMinutes;
        this.position = position;
        this.required = required;
        this.status = "ACTIVE";
    }

    public void updateDraft(String itemType, String itemId, String title, String description,
            UUID videoMediaId, List<String> documentMediaIds, String contentUrl,
            Integer estimatedMinutes, boolean required) {
        restoreDraft(
                this.moduleId,
                itemType,
                itemId,
                title,
                description,
                videoMediaId,
                documentMediaIds,
                contentUrl,
                estimatedMinutes,
                this.position,
                required);
    }

    public void archive(int position) {
        this.position = position;
        this.status = "ARCHIVED";
    }
}
