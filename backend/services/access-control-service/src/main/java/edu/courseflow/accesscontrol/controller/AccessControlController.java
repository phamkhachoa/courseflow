package edu.courseflow.accesscontrol.controller;

import edu.courseflow.accesscontrol.dto.AccessControlDtos.AccessUserDirectoryBatchRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AccessUserDirectoryItemDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AccessRoleGrantExportDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AssignRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckResultDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.CreateRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.DeactivateAccessUserRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.GrantPermissionRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.PermissionDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.PermissionGrantDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ProvisionIdentityRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ProvisionKeycloakUserRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ResolveIdentityRequest;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ResolvedIdentityDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.RoleAssignmentDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.RoleDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.UpdateRoleRequestDto;
import edu.courseflow.accesscontrol.service.AccessControlService;
import edu.courseflow.commonlibrary.web.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AccessControlController {

    private final AccessControlService accessControl;

    public AccessControlController(AccessControlService accessControl) {
        this.accessControl = accessControl;
    }

    @PostMapping("/internal/identities/resolve")
    public ResolvedIdentityDto resolveIdentity(@Valid @RequestBody ResolveIdentityRequest request) {
        return accessControl.resolveIdentity(request);
    }

    @PostMapping("/internal/identities/provision")
    public ResolvedIdentityDto provisionIdentity(@Valid @RequestBody ProvisionIdentityRequest request,
            CurrentUser caller) {
        return accessControl.provisionIdentity(request, caller);
    }

    @PostMapping("/internal/identities/provision-keycloak-user")
    public ResolvedIdentityDto provisionKeycloakUser(@Valid @RequestBody ProvisionKeycloakUserRequest request,
            CurrentUser caller) {
        return accessControl.provisionKeycloakUser(request, caller);
    }

    @PostMapping("/internal/authz/check")
    public AuthzCheckResultDto check(@Valid @RequestBody AuthzCheckRequestDto request, CurrentUser caller) {
        return accessControl.check(request, caller);
    }

    @GetMapping("/internal/permissions")
    public List<PermissionDto> permissions(CurrentUser caller) {
        return accessControl.permissions(caller);
    }

    @GetMapping("/internal/users/{userId}/assignments")
    public List<RoleAssignmentDto> assignments(@PathVariable Long userId, CurrentUser caller) {
        return accessControl.listAssignments(userId, caller);
    }

    @GetMapping("/internal/users/{userId}/assignments:export")
    public List<AccessRoleGrantExportDto> exportAssignments(@PathVariable Long userId, CurrentUser caller) {
        return accessControl.exportAssignments(userId, caller);
    }

    @GetMapping("/internal/users")
    public List<AccessUserDirectoryItemDto> userDirectory(
            @RequestParam(name = "q", required = false) String query,
            @RequestParam(name = "limit", defaultValue = "100") int limit,
            CurrentUser caller) {
        return accessControl.userDirectory(query, limit, caller);
    }

    @GetMapping("/internal/users/{userId}")
    public AccessUserDirectoryItemDto userDirectoryItem(@PathVariable Long userId, CurrentUser caller) {
        return accessControl.userDirectoryItem(userId, caller);
    }

    @PostMapping("/internal/users/{userId}/deactivate")
    public AccessUserDirectoryItemDto deactivateUser(@PathVariable Long userId,
            @Valid @RequestBody DeactivateAccessUserRequest request,
            CurrentUser caller) {
        return accessControl.deactivateUser(userId, request, caller);
    }

    @PostMapping("/internal/users/summary:batch")
    public List<AccessUserDirectoryItemDto> userDirectoryBatch(
            @Valid @RequestBody AccessUserDirectoryBatchRequest request) {
        return accessControl.userDirectoryBatch(request.userIds());
    }

    @PostMapping("/internal/users/{userId}/assignments")
    public RoleAssignmentDto assign(@PathVariable Long userId,
            @Valid @RequestBody AssignRoleRequestDto request,
            CurrentUser caller) {
        return accessControl.assignRole(userId, request, caller);
    }

    @DeleteMapping("/internal/users/{userId}/assignments/{assignmentId}")
    public void revoke(@PathVariable Long userId,
            @PathVariable Long assignmentId,
            CurrentUser caller) {
        accessControl.revokeAssignment(userId, assignmentId, caller);
    }

    @GetMapping("/internal/roles")
    public List<RoleDto> roles(CurrentUser caller) {
        return accessControl.roles(caller);
    }

    @GetMapping("/internal/roles/{roleId}")
    public RoleDto role(@PathVariable UUID roleId, CurrentUser caller) {
        return accessControl.role(roleId, caller);
    }

    @GetMapping("/internal/roles/{roleId}/effective-permissions")
    public List<PermissionGrantDto> effectivePermissions(@PathVariable UUID roleId, CurrentUser caller) {
        return accessControl.effectivePermissions(roleId, caller);
    }

    @PostMapping("/internal/roles")
    public RoleDto createRole(@Valid @RequestBody CreateRoleRequestDto request, CurrentUser caller) {
        return accessControl.createRole(request, caller);
    }

    @PutMapping("/internal/roles/{roleId}")
    public RoleDto updateRole(@PathVariable UUID roleId,
            @Valid @RequestBody UpdateRoleRequestDto request,
            CurrentUser caller) {
        return accessControl.updateRole(roleId, request, caller);
    }

    @DeleteMapping("/internal/roles/{roleId}")
    public void deleteRole(@PathVariable UUID roleId, CurrentUser caller) {
        accessControl.deleteRole(roleId, caller);
    }

    @PostMapping("/internal/roles/{roleId}/permissions")
    public RoleDto grantPermission(@PathVariable UUID roleId,
            @Valid @RequestBody GrantPermissionRequestDto request,
            CurrentUser caller) {
        return accessControl.grantPermission(roleId, request, caller);
    }

    @DeleteMapping("/internal/roles/{roleId}/permissions/{permCode}")
    public RoleDto revokePermission(@PathVariable UUID roleId,
            @PathVariable String permCode,
            CurrentUser caller) {
        return accessControl.revokePermission(roleId, permCode, caller);
    }
}
