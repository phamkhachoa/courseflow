package edu.courseflow.commonlibrary.web;

import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Immutable view of the caller identity propagated by the gateway for the current request.
 *
 * <p>{@code role} is the primary (highest-ranked) role code and is kept for single-role callers.
 * {@code roles} is the full set of effective role codes the caller holds; coarse role checks should
 * prefer {@link #hasAnyRole(String...)} over {@code role} equality. Scope-aware guards should use
 * {@code roleAssignments}; services still receive legacy role codes for backward compatibility.
 */
public record CurrentUser(Long id, String email, String role, Set<String> roles,
                          Set<RoleAssignment> roleAssignments, String internalToken) {

    public CurrentUser {
        roles = roles == null ? Set.of() : Set.copyOf(roles);
        roleAssignments = roleAssignments == null ? Set.of() : Set.copyOf(roleAssignments);
        internalToken = normalizeToken(internalToken);
        if (roleAssignments.isEmpty() && !roles.isEmpty()) {
            roleAssignments = roles.stream()
                    .map(code -> new RoleAssignment(code, "PLATFORM", null))
                    .collect(Collectors.toUnmodifiableSet());
        }
    }

    public CurrentUser(Long id, String email, String role, Set<String> roles, Set<RoleAssignment> roleAssignments) {
        this(id, email, role, roles, roleAssignments, null);
    }

    /** Backward-compatible constructor for callers that only know a single role. */
    public CurrentUser(Long id, String email, String role) {
        this(id, email, role, role == null ? Set.of() : Set.of(role), Set.of(), null);
    }

    /** Backward-compatible constructor for callers that know role codes but not scopes. */
    public CurrentUser(Long id, String email, String role, Set<String> roles) {
        this(id, email, role, roles, Set.of(), null);
    }

    private static String normalizeToken(String token) {
        if (token == null || token.isBlank()) {
            return null;
        }
        String normalized = token.trim();
        if (normalized.regionMatches(true, 0, "Bearer ", 0, 7)) {
            normalized = normalized.substring(7).trim();
        }
        return normalized.isBlank() ? null : normalized;
    }

    public boolean hasRole(String expected) {
        if (expected == null) {
            return false;
        }
        return roles.stream().anyMatch(expected::equalsIgnoreCase);
    }

    public boolean hasAnyRole(String... candidates) {
        for (String candidate : candidates) {
            if (hasRole(candidate)) {
                return true;
            }
        }
        return false;
    }

    public boolean hasPlatformRole(String expected) {
        return hasScopedRole(expected, "PLATFORM", null);
    }

    public boolean hasCourseRole(String expected, UUID courseId) {
        return courseId != null && hasScopedRole(expected, "COURSE", courseId.toString());
    }

    public boolean hasAnyCourseRole(UUID courseId, String... candidates) {
        for (String candidate : candidates) {
            if (hasCourseRole(candidate, courseId)) {
                return true;
            }
        }
        return false;
    }

    public boolean hasDepartmentRole(String expected, String departmentId) {
        return departmentId != null && hasScopedRole(expected, "DEPARTMENT", departmentId);
    }

    public boolean hasAnyDepartmentRole(String departmentId, String... candidates) {
        for (String candidate : candidates) {
            if (hasDepartmentRole(candidate, departmentId)) {
                return true;
            }
        }
        return false;
    }

    public boolean hasScopedRole(String expected, String scopeType, String scopeId) {
        if (expected == null || scopeType == null) {
            return false;
        }
        return roleAssignments.stream().anyMatch(assignment ->
                assignment.codeEquals(expected)
                        && assignment.scopeTypeEquals(scopeType)
                        && assignment.scopeIdEquals(scopeId));
    }

    public record RoleAssignment(String code, String scopeType, String scopeId) {
        public RoleAssignment {
            code = code == null ? "" : code.trim();
            scopeType = scopeType == null || scopeType.isBlank()
                    ? "PLATFORM"
                    : scopeType.trim().toUpperCase();
            scopeId = scopeId == null || scopeId.isBlank() ? null : scopeId.trim();
        }

        boolean codeEquals(String expected) {
            return expected != null && code.equalsIgnoreCase(expected);
        }

        boolean scopeTypeEquals(String expected) {
            return expected != null && scopeType.equalsIgnoreCase(expected);
        }

        boolean scopeIdEquals(String expected) {
            if (scopeId == null || scopeId.isBlank()) {
                return expected == null || expected.isBlank();
            }
            return expected != null && scopeId.equalsIgnoreCase(expected);
        }
    }
}
