package edu.courseflow.search.model;

import java.time.Instant;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.DateFormat;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;
import org.springframework.data.elasticsearch.annotations.Setting;

/**
 * Elasticsearch read model for public course discovery.
 *
 * <p>The index name {@code courseflow-course-search} matches the one declared in the backend
 * architecture doc ("Elasticsearch: courseflow-course-search, courseflow-content-search").
 *
 * <p>Mapping is declared explicitly rather than relying on dynamic mapping so the full-text fields
 * use the analyzed {@code Text} type (with a lowercase + asciifolding analyzer defined in
 * {@code course-search-settings.json}) while exact-match facets/sort fields stay {@code Keyword}.
 * Dynamic mapping would, for example, map every string as a {@code text} + {@code keyword} multi-field
 * with the default analyzer, which gives no control over analysis and silently drifts per-field.
 */
@Document(indexName = "courseflow-course-search")
@Setting(settingPath = "elasticsearch/course-search-settings.json")
public class CourseSearchDocument {

    @Id
    private String id;

    /** Course code, e.g. "CS101". Searchable as full text but also kept as a keyword for exact match. */
    @Field(type = FieldType.Text, analyzer = "course_text")
    private String code;

    @Field(type = FieldType.Text, analyzer = "course_text")
    private String title;

    /** Stable URL slug; exact-match / not analyzed. */
    @Field(type = FieldType.Keyword)
    private String slug;

    @Field(type = FieldType.Text, analyzer = "course_text")
    private String summary;

    @Field(type = FieldType.Keyword)
    private String departmentId;

    @Field(type = FieldType.Keyword)
    private String level;

    /** PUBLISHED / ARCHIVED / ... — filtered on, never full-text searched. */
    @Field(type = FieldType.Keyword)
    private String status;

    @Field(type = FieldType.Date, format = DateFormat.date_time)
    private Instant updatedAt;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getSlug() {
        return slug;
    }

    public void setSlug(String slug) {
        this.slug = slug;
    }

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getDepartmentId() {
        return departmentId;
    }

    public void setDepartmentId(String departmentId) {
        this.departmentId = departmentId;
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = level;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
