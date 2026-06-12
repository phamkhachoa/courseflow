package edu.courseflow.course.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "course_materials")
public class CourseMaterial {

    @Id
    private UUID id;

    @Column(name = "course_id", nullable = false)
    private UUID courseId;

    @Column(nullable = false)
    private String title;

    @Column(name = "material_type", nullable = false, length = 40)
    private String materialType;

    @Column(name = "media_id")
    private UUID mediaId;

    @Column(nullable = false)
    private int position;

    protected CourseMaterial() {
    }

    public CourseMaterial(UUID id, UUID courseId, String title, String materialType, UUID mediaId, int position) {
        this.id = id;
        this.courseId = courseId;
        this.title = title;
        this.materialType = materialType;
        this.mediaId = mediaId;
        this.position = position;
    }

    public UUID getId() {
        return id;
    }

    public UUID getCourseId() {
        return courseId;
    }

    public String getTitle() {
        return title;
    }

    public String getMaterialType() {
        return materialType;
    }

    public UUID getMediaId() {
        return mediaId;
    }

    public int getPosition() {
        return position;
    }
}
