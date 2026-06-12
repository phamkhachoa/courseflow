package edu.courseflow.commonlibrary.web;

import java.util.Set;

/**
 * Immutable view of the caller identity propagated by the gateway for the current request.
 *
 * <p>{@code role} is the primary (highest-ranked) role code and is kept for single-role callers.
 * {@code roles} is the full set of effective role codes the caller holds; coarse role checks should
 * prefer {@link #hasAnyRole(String...)} over {@code role} equality. Scope-aware permission decisions
 * (PLATFORM / ORG / COURSE / DEPARTMENT) are delegated to identity-service's {@code /internal/authz/check}.
 */
public record CurrentUser(Long id, String email, String role, Set<String> roles) {

    public CurrentUser {
        roles = roles == null ? Set.of() : Set.copyOf(roles);
    }

    /** Backward-compatible constructor for callers that only know a single role. */
    public CurrentUser(Long id, String email, String role) {
        this(id, email, role, role == null ? Set.of() : Set.of(role));
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
}
