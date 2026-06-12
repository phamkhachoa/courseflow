package edu.courseflow.search.web;

import edu.courseflow.commonlibrary.web.CurrentUser;

/**
 * Centralised authorization checks for this service. Identity is supplied by the gateway via the
 * {@link CurrentUser} resolver; controllers must never trust identity fields in the request body.
 *
 * <p>Public search endpoints ({@code /public/search/**}) are unauthenticated by design. The internal
 * indexing endpoints ({@code /internal/search/**}) are staff-only (INSTRUCTOR or ADMIN) and used for
 * manual backfill/reindex; event-driven indexing happens via the Kafka consumer.
 */
public final class Authz {

    public static final String ROLE_INSTRUCTOR = "INSTRUCTOR";
    public static final String ROLE_ADMIN = "ADMIN";

    private Authz() {
    }

    public static boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole(ROLE_INSTRUCTOR, ROLE_ADMIN);
    }

    /** Require the caller to be an instructor or admin (manual indexing/backfill). */
    public static void requireStaff(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("UNAUTHENTICATED");
        }
        if (!isStaff(user)) {
            throw new ForbiddenException("FORBIDDEN_REQUIRES_INSTRUCTOR_OR_ADMIN");
        }
    }
}
