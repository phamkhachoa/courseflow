package edu.courseflow.accesscontrol.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "permissions")
public class Permission {

    @Id
    @Column(length = 80)
    private String code;

    @Column(nullable = false)
    private String description;

    @Column(nullable = false, length = 80)
    private String category = "general";

    @Column(name = "scope_type", nullable = false, length = 40)
    private String scopeType = "ANY";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    protected Permission() {
    }

    public String getCode() {
        return code;
    }

    public String getDescription() {
        return description;
    }

    public String getCategory() {
        return category;
    }

    public String getScopeType() {
        return scopeType;
    }
}
