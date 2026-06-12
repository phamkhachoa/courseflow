package edu.courseflow.identity.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.AuthzDtos.CreateRoleRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.GrantPermissionRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.PermissionGrantDto;
import edu.courseflow.identity.dto.AuthzDtos.RoleDto;
import edu.courseflow.identity.dto.AuthzDtos.UpdateRoleRequestDto;
import edu.courseflow.identity.service.RoleManagementService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/roles")
public class RoleController {

    private final RoleManagementService roles;

    public RoleController(RoleManagementService roles) {
        this.roles = roles;
    }

    @GetMapping
    public List<RoleDto> list() {
        return roles.listRoles();
    }

    @GetMapping("/{roleId}")
    public RoleDto get(@PathVariable UUID roleId) {
        return roles.getRole(roleId);
    }

    @GetMapping("/{roleId}/effective-permissions")
    public List<PermissionGrantDto> effectivePermissions(@PathVariable UUID roleId) {
        return roles.effectivePermissions(roleId);
    }

    @PostMapping
    public RoleDto create(@Valid @RequestBody CreateRoleRequestDto request, CurrentUser caller) {
        return roles.createRole(request, callerTag(caller));
    }

    @PutMapping("/{roleId}")
    public RoleDto update(@PathVariable UUID roleId,
            @Valid @RequestBody UpdateRoleRequestDto request,
            CurrentUser caller) {
        return roles.updateRole(roleId, request, callerTag(caller));
    }

    @DeleteMapping("/{roleId}")
    public void delete(@PathVariable UUID roleId) {
        roles.deleteRole(roleId);
    }

    @PostMapping("/{roleId}/permissions")
    public RoleDto grantPermission(@PathVariable UUID roleId,
            @Valid @RequestBody GrantPermissionRequestDto request,
            CurrentUser caller) {
        return roles.grantPermission(roleId, request, callerTag(caller));
    }

    @DeleteMapping("/{roleId}/permissions/{permCode}")
    public RoleDto revokePermission(@PathVariable UUID roleId, @PathVariable String permCode) {
        return roles.revokePermission(roleId, permCode);
    }

    private String callerTag(CurrentUser caller) {
        if (caller == null)
            return "system";
        if (caller.id() != null)
            return "user:" + caller.id();
        return caller.email() == null ? "system" : caller.email();
    }
}
