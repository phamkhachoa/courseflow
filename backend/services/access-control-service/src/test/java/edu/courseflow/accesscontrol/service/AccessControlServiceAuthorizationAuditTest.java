package edu.courseflow.accesscontrol.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.accesscontrol.dto.AccessControlDtos.AssignRoleRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzCheckRequestDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.AuthzScopeDto;
import edu.courseflow.accesscontrol.dto.AccessControlDtos.ProvisionKeycloakUserRequest;
import edu.courseflow.accesscontrol.model.AccessControlAuditLog;
import edu.courseflow.accesscontrol.model.AccessUser;
import edu.courseflow.accesscontrol.model.Permission;
import edu.courseflow.accesscontrol.model.Role;
import edu.courseflow.accesscontrol.model.RolePermissionGrant;
import edu.courseflow.accesscontrol.model.UserRoleAssignment;
import edu.courseflow.accesscontrol.repository.AccessControlAuditLogRepository;
import edu.courseflow.accesscontrol.repository.AccessUserRepository;
import edu.courseflow.accesscontrol.repository.ExternalIdentityLinkRepository;
import edu.courseflow.accesscontrol.repository.PermissionRepository;
import edu.courseflow.accesscontrol.repository.RolePermissionGrantRepository;
import edu.courseflow.accesscontrol.repository.RoleRepository;
import edu.courseflow.accesscontrol.repository.UserRoleAssignmentRepository;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.BeanUtils;
import org.springframework.test.util.ReflectionTestUtils;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AccessControlServiceAuthorizationAuditTest {

    @Mock
    AccessUserRepository users;

    @Mock
    ExternalIdentityLinkRepository identityLinks;

    @Mock
    PermissionRepository permissions;

    @Mock
    RoleRepository roles;

    @Mock
    RolePermissionGrantRepository grants;

    @Mock
    UserRoleAssignmentRepository assignments;

    @Mock
    AccessControlAuditLogRepository auditLogs;

    @Mock
    InternalJwtService internalJwtService;

    AccessUser learner;

    @BeforeEach
    void setUp() {
        learner = new AccessUser(42L, "learner@courseflow.local");
    }

    @Test
    void auditsDeniedAuthorizationCheckWhenNoRoleAllowsPermission() {
        AccessControlService accessControl = service(false);
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of());

        var result = accessControl.check(new AuthzCheckRequestDto(
                "42", "course:publish", "COURSE", "course-1"));

        assertThat(result.allowed()).isFalse();
        AccessControlAuditLog audit = captureAudit();
        assertThat(audit.getEventType()).isEqualTo("AUTHZ_CHECK_DENIED");
        assertThat(audit.getUser()).isSameAs(learner);
        assertThat(audit.getActorId()).isEqualTo("authz-check");
        assertThat(audit.isSuccess()).isFalse();
        assertThat(audit.getDetail())
                .contains("userId=42", "permission=course:publish", "scopeType=COURSE",
                        "scopeId=course-1", "reason=no_allow");
    }

    @Test
    void auditsExplicitDenyAsDeniedAuthorizationReason() {
        AccessControlService accessControl = service(false);
        Role role = role("SUSPENDED_LEARNER");
        RolePermissionGrant denyGrant = grant(role, "course:view", "DENY");
        when(permissions.findById("course:view")).thenReturn(Optional.of(permissionDefinition(
                "course:view", "COURSE")));
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(learner, role, "COURSE", "course-1", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(denyGrant));

        var result = accessControl.check(new AuthzCheckRequestDto("42", "course:view", "COURSE", "course-1"));

        assertThat(result.allowed()).isFalse();
        AccessControlAuditLog audit = captureAudit();
        assertThat(audit.getEventType()).isEqualTo("AUTHZ_CHECK_DENIED");
        assertThat(audit.getDetail()).contains("reason=explicit_deny");
    }

    @Test
    void doesNotAuditAllowedAuthorizationChecksByDefault() {
        AccessControlService accessControl = service(false);
        Role role = role("INSTRUCTOR");
        RolePermissionGrant allowGrant = grant(role, "course:publish", "ALLOW");
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(learner, role, "COURSE", "course-1", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(allowGrant));

        var result = accessControl.check(new AuthzCheckRequestDto(
                "42", "course:publish", "COURSE", "course-1"));

        assertThat(result.allowed()).isTrue();
        verify(auditLogs, never()).save(any(AccessControlAuditLog.class));
    }

    @Test
    void auditsAllowedAuthorizationChecksWhenConfigured() {
        AccessControlService accessControl = service(true);
        Role role = role("INSTRUCTOR");
        RolePermissionGrant allowGrant = grant(role, "course:publish", "ALLOW");
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(learner, role, "COURSE", "course-1", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(allowGrant));

        var result = accessControl.check(new AuthzCheckRequestDto(
                "42", "course:publish", "COURSE", "course-1"));

        assertThat(result.allowed()).isTrue();
        AccessControlAuditLog audit = captureAudit();
        assertThat(audit.getEventType()).isEqualTo("AUTHZ_CHECK_ALLOWED");
        assertThat(audit.isSuccess()).isTrue();
        assertThat(audit.getDetail()).contains("reason=allow_grant");
    }

    @Test
    void recordsAuthorizationDecisionMetrics() {
        SimpleMeterRegistry registry = new SimpleMeterRegistry();
        AccessControlService accessControl = service(false, new AccessControlMetrics(registry));
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of());

        accessControl.check(new AuthzCheckRequestDto("42", "course:publish", "COURSE", "course-1"));

        assertThat(registry
                        .get("courseflow.access_control.authz.checks")
                        .tag("result", "denied")
                        .tag("reason", "no_allow")
                        .tag("scope_type", "course")
                        .counter()
                        .count())
                .isEqualTo(1.0);
    }

    @Test
    void rejectsUnknownScopeTypesBeforeAuthorizationDecision() {
        AccessControlService accessControl = service(false);

        assertThatThrownBy(() -> accessControl.check(new AuthzCheckRequestDto(
                "42", "course:publish", "TEAM", "team-1")))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("INVALID_SCOPE_TYPE");
    }

    @Test
    void rejectsScopedAuthorizationChecksWithoutScopeId() {
        AccessControlService accessControl = service(false);

        assertThatThrownBy(() -> accessControl.check(new AuthzCheckRequestDto(
                "42", "course:publish", "COURSE", null)))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("SCOPE_ID_REQUIRED");
    }

    @Test
    void rejectsPermissionScopeMismatch() {
        AccessControlService accessControl = service(false);
        when(permissions.findById("role:manage")).thenReturn(Optional.of(permissionDefinition(
                "role:manage", "PLATFORM")));

        assertThatThrownBy(() -> accessControl.check(new AuthzCheckRequestDto(
                "42", "role:manage", "COURSE", "course-1")))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("PERMISSION_SCOPE_MISMATCH");
    }

    @Test
    void allowsApplicationScopedIncentivePermission() {
        AccessControlService accessControl = service(false);
        Role role = role("INCENTIVE_REVIEWER");
        RolePermissionGrant allowGrant = grant(role, "incentive:campaign:review", "ALLOW");
        when(permissions.findById("incentive:campaign:review"))
                .thenReturn(Optional.of(permissionDefinition("incentive:campaign:review", "APPLICATION")));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(
                        learner, role, "APPLICATION", "courseflow:lms", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(allowGrant));

        var result = accessControl.check(new AuthzCheckRequestDto(
                "42", "incentive:campaign:review", "APPLICATION", "courseflow:lms"));

        assertThat(result.allowed()).isTrue();
        verify(auditLogs, never()).save(any(AccessControlAuditLog.class));
    }

    @Test
    void allowsCouponImportManageForOperatorButNotReview() {
        AccessControlService accessControl = service(false);
        Role role = role("INCENTIVE_OPERATOR");
        RolePermissionGrant readGrant = grant(role, "incentive:coupon:import:read", "ALLOW");
        RolePermissionGrant manageGrant = grant(role, "incentive:coupon:import:manage", "ALLOW");
        when(permissions.findById("incentive:coupon:import:manage"))
                .thenReturn(Optional.of(permissionDefinition("incentive:coupon:import:manage", "APPLICATION")));
        when(permissions.findById("incentive:coupon:import:review"))
                .thenReturn(Optional.of(permissionDefinition("incentive:coupon:import:review", "APPLICATION")));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(
                        learner, role, "APPLICATION", "courseflow:lms", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(readGrant, manageGrant));

        assertThat(accessControl.check(new AuthzCheckRequestDto(
                "42", "incentive:coupon:import:manage", "APPLICATION", "courseflow:lms")).allowed())
                .isTrue();
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                "42", "incentive:coupon:import:review", "APPLICATION", "courseflow:lms")).allowed())
                .isFalse();
    }

    @Test
    void allowsCouponImportReviewForReviewerButNotManage() {
        AccessControlService accessControl = service(false);
        Role role = role("INCENTIVE_REVIEWER");
        RolePermissionGrant readGrant = grant(role, "incentive:coupon:import:read", "ALLOW");
        RolePermissionGrant reviewGrant = grant(role, "incentive:coupon:import:review", "ALLOW");
        when(permissions.findById("incentive:coupon:import:review"))
                .thenReturn(Optional.of(permissionDefinition("incentive:coupon:import:review", "APPLICATION")));
        when(permissions.findById("incentive:coupon:import:manage"))
                .thenReturn(Optional.of(permissionDefinition("incentive:coupon:import:manage", "APPLICATION")));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(
                        learner, role, "APPLICATION", "courseflow:lms", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(readGrant, reviewGrant));

        assertThat(accessControl.check(new AuthzCheckRequestDto(
                "42", "incentive:coupon:import:review", "APPLICATION", "courseflow:lms")).allowed())
                .isTrue();
        assertThat(accessControl.check(new AuthzCheckRequestDto(
                "42", "incentive:coupon:import:manage", "APPLICATION", "courseflow:lms")).allowed())
                .isFalse();
    }

    @Test
    void allowsTenantScopedIncentivePermissionForApplicationWhenTrustedServiceSuppliesTenantAncestor() {
        AccessControlService accessControl = service(false);
        Role role = role("INCENTIVE_ADMIN");
        RolePermissionGrant allowGrant = grant(role, "incentive:read", "ALLOW");
        when(internalJwtService.verify("service-token")).thenReturn(serviceClaims(
                InternalScopes.AUTHZ_CHECK,
                InternalScopes.AUTHZ_ASSERT_TOPOLOGY));
        when(permissions.findById("incentive:read"))
                .thenReturn(Optional.of(permissionDefinition("incentive:read", "TENANT")));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(
                        learner, role, "TENANT", "courseflow", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(allowGrant));

        var result = accessControl.check(new AuthzCheckRequestDto(
                "42",
                "incentive:read",
                "APPLICATION",
                "courseflow:lms",
                List.of(new AuthzScopeDto("TENANT", "courseflow"))),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token"));

        assertThat(result.allowed()).isTrue();
    }

    @Test
    void rejectsLmsAncestorForApplicationScopedIncentiveAuthorization() {
        AccessControlService accessControl = service(false);
        when(internalJwtService.verify("service-token")).thenReturn(serviceClaims(
                InternalScopes.AUTHZ_CHECK,
                InternalScopes.AUTHZ_ASSERT_TOPOLOGY));
        when(permissions.findById("incentive:read"))
                .thenReturn(Optional.of(permissionDefinition("incentive:read", "TENANT")));

        assertThatThrownBy(() -> accessControl.check(new AuthzCheckRequestDto(
                "42",
                "incentive:read",
                "APPLICATION",
                "courseflow:lms",
                List.of(new AuthzScopeDto("ORG", "org-1"))),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token")))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("INVALID_SCOPE_ANCESTOR");
    }

    @Test
    void rejectsRoleAssignmentReadsForUserCallerWithoutRoleManage() {
        AccessControlService accessControl = service(false);
        when(permissions.findById("role:manage")).thenReturn(Optional.of(permissionDefinition(
                "role:manage", "PLATFORM")));
        when(assignments.findActiveByUserId(eq(2L), any(Instant.class))).thenReturn(List.of());

        assertThatThrownBy(() -> accessControl.listAssignments(
                42L,
                new CurrentUser(2L, "learner@courseflow.local", "STUDENT")))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("role:manage");

        verify(assignments, never()).findLiveByUserId(42L);
    }

    @Test
    void allowsMachineCallerToExportAssignmentsThroughInternalScopeGate() {
        AccessControlService accessControl = service(false);
        Role instructor = role("INSTRUCTOR");
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(assignments.findAllByUserId(42L))
                .thenReturn(List.of(new UserRoleAssignment(learner, instructor, "COURSE", "course-1", "admin", null)));

        var result = accessControl.exportAssignments(
                42L,
                new CurrentUser(null, null, null, java.util.Set.of(), java.util.Set.of(), "service-token"));

        assertThat(result).singleElement()
                .satisfies(assignment -> {
                    assertThat(assignment.roleCode()).isEqualTo("INSTRUCTOR");
                    assertThat(assignment.scopeType()).isEqualTo("COURSE");
                    assertThat(assignment.scopeId()).isEqualTo("course-1");
                });
        verify(permissions, never()).findById("role:manage");
    }

    @Test
    void rejectsAccessUserDeactivateForUserCallerWithoutPlatformAdmin() {
        AccessControlService accessControl = service(false);
        when(permissions.findById("platform:admin")).thenReturn(Optional.of(permissionDefinition(
                "platform:admin", "PLATFORM")));
        when(assignments.findActiveByUserId(eq(2L), any(Instant.class))).thenReturn(List.of());

        assertThatThrownBy(() -> accessControl.deactivateUser(
                42L,
                new edu.courseflow.accesscontrol.dto.AccessControlDtos.DeactivateAccessUserRequest("policy"),
                new CurrentUser(2L, "learner@courseflow.local", "STUDENT")))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("platform:admin");

        verify(users, never()).findById(42L);
    }

    @Test
    void assignsScopedRoleUsingTargetScopePermissionCheck() {
        AccessControlService accessControl = service(false);
        AccessUser adminUser = new AccessUser(1L, "admin@courseflow.local");
        Role admin = role("ADMIN");
        Role instructor = role("INSTRUCTOR");
        when(permissions.findById("user:assign-role")).thenReturn(Optional.of(permissionDefinition(
                "user:assign-role", "ANY")));
        when(assignments.findActiveByUserId(eq(1L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(adminUser, admin, "PLATFORM", null, "seed", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(admin.getId()))
                .thenReturn(List.of(grant(admin, "user:assign-role", "ALLOW")));
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(roles.findById(instructor.getId())).thenReturn(Optional.of(instructor));
        when(assignments.findLiveExisting(42L, instructor.getId(), "ORG", "org-1"))
                .thenReturn(Optional.empty());
        when(assignments.save(any(UserRoleAssignment.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var result = accessControl.assignRole(
                42L,
                new AssignRoleRequestDto(instructor.getId().toString(), "ORG", "org-1", null, null),
                new CurrentUser(1L, "admin@courseflow.local", "ADMIN", java.util.Set.of("ADMIN")));

        assertThat(result.roleCode()).isEqualTo("INSTRUCTOR");
        assertThat(result.scopeType()).isEqualTo("ORG");
        assertThat(result.scopeId()).isEqualTo("org-1");
        AccessControlAuditLog audit = captureAudit();
        assertThat(audit.getEventType()).isEqualTo("ROLE_ASSIGNED");
        assertThat(audit.getActorId()).isEqualTo("user:1");
    }

    @Test
    void assignsApplicationScopedIncentiveRoleUsingPlatformAdmin() {
        AccessControlService accessControl = service(false);
        AccessUser adminUser = new AccessUser(1L, "admin@courseflow.local");
        Role admin = role("ADMIN");
        Role reviewer = role("INCENTIVE_REVIEWER");
        when(permissions.findById("user:assign-role")).thenReturn(Optional.of(permissionDefinition(
                "user:assign-role", "ANY")));
        when(assignments.findActiveByUserId(eq(1L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(adminUser, admin, "PLATFORM", null, "seed", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(admin.getId()))
                .thenReturn(List.of(grant(admin, "user:assign-role", "ALLOW")));
        when(users.findById(42L)).thenReturn(Optional.of(learner));
        when(roles.findById(reviewer.getId())).thenReturn(Optional.of(reviewer));
        when(assignments.findLiveExisting(42L, reviewer.getId(), "APPLICATION", "courseflow:lms"))
                .thenReturn(Optional.empty());
        when(assignments.save(any(UserRoleAssignment.class)))
                .thenAnswer(invocation -> invocation.getArgument(0));

        var result = accessControl.assignRole(
                42L,
                new AssignRoleRequestDto(reviewer.getId().toString(), "APPLICATION", "courseflow:lms", null, null),
                new CurrentUser(1L, "admin@courseflow.local", "ADMIN", java.util.Set.of("ADMIN")));

        assertThat(result.roleCode()).isEqualTo("INCENTIVE_REVIEWER");
        assertThat(result.scopeType()).isEqualTo("APPLICATION");
        assertThat(result.scopeId()).isEqualTo("courseflow:lms");
    }

    @Test
    void rejectsApplicationScopeIdWithoutTenantAndApplicationParts() {
        AccessControlService accessControl = service(false);

        assertThatThrownBy(() -> accessControl.assignRole(
                42L,
                new AssignRoleRequestDto(UUID.randomUUID().toString(), "APPLICATION", "lms", null, null),
                new CurrentUser(1L, "admin@courseflow.local", "ADMIN", java.util.Set.of("ADMIN"))))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("INVALID_APPLICATION_SCOPE_ID");

        verify(permissions, never()).findById("user:assign-role");
    }

    @Test
    void allowsAncestorScopeAssignmentsOnlyForTrustedTopologyAssertingService() {
        AccessControlService accessControl = service(false);
        Role role = role("DEPARTMENT_REVIEWER");
        RolePermissionGrant allowGrant = grant(role, "course:publish", "ALLOW");
        when(internalJwtService.verify("service-token")).thenReturn(serviceClaims(
                InternalScopes.AUTHZ_CHECK,
                InternalScopes.AUTHZ_ASSERT_TOPOLOGY));
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));
        when(assignments.findActiveByUserId(eq(42L), any(Instant.class)))
                .thenReturn(List.of(new UserRoleAssignment(learner, role, "DEPARTMENT", "dept-1", "admin", null)));
        when(grants.findByRole_IdOrderByPermission_CategoryAscPermission_CodeAsc(role.getId()))
                .thenReturn(List.of(allowGrant));

        var result = accessControl.check(new AuthzCheckRequestDto(
                "42",
                "course:publish",
                "COURSE",
                "course-1",
                List.of(new AuthzScopeDto("DEPARTMENT", "dept-1"))),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token"));

        assertThat(result.allowed()).isTrue();
    }

    @Test
    void rejectsAncestorScopeAssignmentsWithoutTopologyAssertionScope() {
        AccessControlService accessControl = service(false);
        when(internalJwtService.verify("service-token")).thenReturn(serviceClaims(InternalScopes.AUTHZ_CHECK));
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));

        assertThatThrownBy(() -> accessControl.check(new AuthzCheckRequestDto(
                "42",
                "course:publish",
                "COURSE",
                "course-1",
                List.of(new AuthzScopeDto("DEPARTMENT", "dept-1"))),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token")))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("AUTHZ_TOPOLOGY_ASSERTION_SCOPE_REQUIRED");
    }

    @Test
    void rejectsScopeAncestorsThatAreNotWiderThanRequestedScope() {
        AccessControlService accessControl = service(false);
        when(internalJwtService.verify("service-token")).thenReturn(serviceClaims(
                InternalScopes.AUTHZ_CHECK,
                InternalScopes.AUTHZ_ASSERT_TOPOLOGY));
        when(permissions.findById("course:publish")).thenReturn(Optional.of(permissionDefinition(
                "course:publish", "DEPARTMENT")));

        assertThatThrownBy(() -> accessControl.check(new AuthzCheckRequestDto(
                "42",
                "course:publish",
                "COURSE",
                "course-1",
                List.of(new AuthzScopeDto("SECTION", "section-1"))),
                new CurrentUser(null, null, null, Set.of(), Set.of(), "service-token")))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("INVALID_SCOPE_ANCESTOR");
    }

    @Test
    void provisioningKeycloakUserWithoutRoleHintsDoesNotGrantDefaultRole() {
        AccessControlService accessControl = service(false);
        when(identityLinks.findByIssuerAndSubject("https://auth.example.com/realms/courseflow", "kc-123"))
                .thenReturn(Optional.empty());
        when(users.save(any(AccessUser.class))).thenAnswer(invocation -> {
            AccessUser user = invocation.getArgument(0);
            ReflectionTestUtils.setField(user, "id", 100000L);
            return user;
        });
        when(assignments.findActiveByUserId(eq(100000L), any(Instant.class))).thenReturn(List.of());

        var result = accessControl.provisionKeycloakUser(new ProvisionKeycloakUserRequest(
                "https://auth.example.com/realms/courseflow",
                "kc-123",
                "new@example.com",
                false,
                List.of()), new CurrentUser(1L, "admin@example.com", "ADMIN"));

        assertThat(result.userId()).isEqualTo("100000");
        assertThat(result.roleAssignments()).isEmpty();
        verify(roles, never()).findByCode(any());
        verify(assignments, never()).save(any(UserRoleAssignment.class));
    }

    private AccessControlService service(boolean auditAllowed) {
        return service(auditAllowed, AccessControlMetrics.noop());
    }

    private AccessControlService service(boolean auditAllowed, AccessControlMetrics metrics) {
        return new AccessControlService(
                users,
                identityLinks,
                permissions,
                roles,
                grants,
                assignments,
                auditLogs,
                metrics,
                internalJwtService,
                auditAllowed);
    }

    private Claims serviceClaims(String... scopes) {
        Set<String> scopeSet = new java.util.LinkedHashSet<>(List.of(scopes));
        return Jwts.claims()
                .add("actor_type", "service")
                .add("scope", String.join(" ", scopeSet))
                .add("scp", List.copyOf(scopeSet))
                .build();
    }

    private Role role(String code) {
        return new Role(UUID.randomUUID(), code, code, null, false, false, 0, null, "test");
    }

    private RolePermissionGrant grant(Role role, String permissionCode, String effect) {
        Permission permission = permissionDefinition(permissionCode, "ANY");
        return new RolePermissionGrant(role, permission, effect, "test");
    }

    private Permission permissionDefinition(String permissionCode, String scopeType) {
        Permission permission = BeanUtils.instantiateClass(Permission.class);
        ReflectionTestUtils.setField(permission, "code", permissionCode);
        ReflectionTestUtils.setField(permission, "description", permissionCode);
        ReflectionTestUtils.setField(permission, "category", "test");
        ReflectionTestUtils.setField(permission, "scopeType", scopeType);
        return permission;
    }

    private AccessControlAuditLog captureAudit() {
        ArgumentCaptor<AccessControlAuditLog> captor = ArgumentCaptor.forClass(AccessControlAuditLog.class);
        verify(auditLogs).save(captor.capture());
        return captor.getValue();
    }
}
