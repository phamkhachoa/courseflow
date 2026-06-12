package edu.courseflow.identity.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.AuthzDtos.AssignRoleRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.AssignmentDto;
import edu.courseflow.identity.dto.AuthzDtos.AuthzCheckRequestDto;
import edu.courseflow.identity.dto.AuthzDtos.AuthzCheckResultDto;
import edu.courseflow.identity.dto.AuthzDtos.PermissionDto;
import edu.courseflow.identity.service.AuthzService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AuthzController {

    private final AuthzService authz;

    public AuthzController(AuthzService authz) {
        this.authz = authz;
    }

    @GetMapping("/internal/permissions")
    public List<PermissionDto> permissions() {
        return authz.listPermissions();
    }

    @GetMapping("/internal/users/{userId}/assignments")
    public List<AssignmentDto> assignments(@PathVariable Long userId) {
        return authz.listAssignments(userId);
    }

    @PostMapping("/internal/users/{userId}/assignments")
    public AssignmentDto assign(@PathVariable Long userId,
            @Valid @RequestBody AssignRoleRequestDto request,
            CurrentUser caller) {
        // grantedBy in the request body is ignored; the trustworthy value is the
        // verified caller.
        AssignRoleRequestDto effective = new AssignRoleRequestDto(
                request.roleId(), request.scopeType(), request.scopeId(),
                callerTag(caller), request.expiresAt());
        return authz.assignRole(userId, effective, caller);
    }

    @DeleteMapping("/internal/users/{userId}/assignments/{assignmentId}")
    public void revoke(@PathVariable Long userId,
            @PathVariable Long assignmentId,
            CurrentUser caller) {
        authz.revokeAssignment(userId, assignmentId, callerTag(caller), caller);
    }

    @PostMapping("/internal/authz/check")
    public AuthzCheckResultDto check(@Valid @RequestBody AuthzCheckRequestDto request) {
        return authz.check(request);
    }

    private String callerTag(CurrentUser caller) {
        if (caller == null)
            return "system";
        if (caller.id() != null)
            return "user:" + caller.id();
        return caller.email() == null ? "system" : caller.email();
    }
}
