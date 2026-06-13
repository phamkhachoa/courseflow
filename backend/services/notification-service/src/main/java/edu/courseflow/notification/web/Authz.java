package edu.courseflow.notification.web;

import edu.courseflow.commonlibrary.web.CurrentUser;

/**
 * Centralised authorization checks for this service. Identity is supplied by the gateway via the
 * {@link CurrentUser} resolver; controllers must never trust identity fields in the request body.
 *
 * <p>Notifications are personal: a caller may only read or subscribe to their OWN stream. There is
 * no cross-user access here (even staff have no business reading another user's inbox stream), so
 * the only rule is "must be the owner". Identity columns are VARCHAR(64); the caller id is the
 * gateway's numeric user id rendered as a string.
 */
public final class Authz {

    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_INSTRUCTOR = "INSTRUCTOR";
    private static final String ROLE_ORG_ADMIN = "ORG_ADMIN";

    private Authz() {
    }

    /** Caller identity as the string used in persistence columns (user_id). */
    public static String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("UNAUTHENTICATED");
        }
        return String.valueOf(user.id());
    }

    /**
     * Require the caller to be the owner of the targeted stream/inbox. Used to guard a subscription
     * to a specific user's notification stream — a user may only subscribe to their own.
     */
    public static void requireSelf(CurrentUser user, String targetUserId) {
        String caller = callerId(user);
        if (targetUserId == null || !targetUserId.equals(caller)) {
            throw new ForbiddenException("FORBIDDEN_NOT_OWNER");
        }
    }

    public static boolean isAdmin(CurrentUser user) {
        return user != null && user.hasAnyRole(ROLE_ADMIN, ROLE_ORG_ADMIN);
    }

    public static void requireSelfOrAdmin(CurrentUser user, String targetUserId) {
        if (isAdmin(user)) {
            return;
        }
        requireSelf(user, targetUserId);
    }

    public static boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole(ROLE_INSTRUCTOR, ROLE_ADMIN, ROLE_ORG_ADMIN);
    }

    public static void requireStaff(CurrentUser user) {
        if (!isStaff(user)) {
            throw new ForbiddenException("FORBIDDEN_REQUIRES_INSTRUCTOR_OR_ADMIN");
        }
    }
}
