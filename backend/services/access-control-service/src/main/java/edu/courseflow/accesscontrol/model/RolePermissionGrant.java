package edu.courseflow.accesscontrol.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "role_permission_grants")
public class RolePermissionGrant {

    @Id
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "role_id", nullable = false)
    private Role role;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "permission_code", nullable = false)
    private Permission permission;

    @Column(nullable = false, length = 10)
    private String effect = "ALLOW";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "created_by")
    private String createdBy;

    protected RolePermissionGrant() {
    }

    public RolePermissionGrant(Role role, Permission permission, String effect, String createdBy) {
        this.id = UUID.randomUUID();
        this.role = role;
        this.permission = permission;
        this.effect = effect;
        this.createdBy = createdBy;
        this.createdAt = Instant.now();
    }

    public Role getRole() {
        return role;
    }

    public Permission getPermission() {
        return permission;
    }

    public String getEffect() {
        return effect;
    }

    public void setEffect(String effect) {
        this.effect = effect;
    }
}
