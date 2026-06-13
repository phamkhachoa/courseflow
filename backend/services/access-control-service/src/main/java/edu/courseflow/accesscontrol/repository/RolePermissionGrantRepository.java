package edu.courseflow.accesscontrol.repository;

import edu.courseflow.accesscontrol.model.RolePermissionGrant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RolePermissionGrantRepository extends JpaRepository<RolePermissionGrant, UUID> {

    @EntityGraph(attributePaths = "permission")
    List<RolePermissionGrant> findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(UUID roleId);

    @EntityGraph(attributePaths = "permission")
    Optional<RolePermissionGrant> findByRole_IdAndPermission_Code(UUID roleId, String permissionCode);

    @Modifying
    @Query("delete from RolePermissionGrant grant where grant.role.id = :roleId and grant.permission.code = :permissionCode")
    int deleteByRoleIdAndPermissionCode(@Param("roleId") UUID roleId,
            @Param("permissionCode") String permissionCode);
}
