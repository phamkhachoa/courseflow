package edu.courseflow.peerreview.web;

import edu.courseflow.commonlibrary.web.CurrentUser;

/**
 * Centralised authorization checks for this service. Identity is supplied by the gateway via the
 * {@link CurrentUser} resolver; controllers must never trust identity fields in the request body.
 *
 * <p><b>Assumption:</b> there is no instructor&rarr;course mapping available inside this service yet,
 * so the coarse rule applied is: a STUDENT may only act as themselves (e.g. submit a review they were
 * assigned), while INSTRUCTOR and ADMIN may perform staff actions (assign reviewers, finalize scores).
 * Tightening to per-course ownership is a follow-up once a course-membership lookup exists.
 */
public final class Authz {

    public static final String ROLE_STUDENT = "STUDENT";
    public static final String ROLE_INSTRUCTOR = "INSTRUCTOR";
    public static final String ROLE_ADMIN = "ADMIN";

    private Authz() {
    }

    /** Caller identity as the string used in persistence columns (reviewer_id, finalized_by, ...). */
    public static String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("UNAUTHENTICATED");
        }
        return String.valueOf(user.id());
    }

    public static boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole(ROLE_INSTRUCTOR, ROLE_ADMIN);
    }

    /** Require the caller to be an instructor or admin (assign reviewers, finalize, etc.). */
    public static void requireStaff(CurrentUser user) {
        if (!isStaff(user)) {
            throw new ForbiddenException("FORBIDDEN_REQUIRES_INSTRUCTOR_OR_ADMIN");
        }
    }

    /**
     * Require the caller to be the given owner (its reviewer) or staff. Used when a student submits a
     * review for an assignment that must belong to them.
     */
    public static void requireSelfOrStaff(CurrentUser user, String ownerId) {
        if (isStaff(user)) {
            return;
        }
        if (ownerId == null || !ownerId.equals(callerId(user))) {
            throw new ForbiddenException("FORBIDDEN_NOT_OWNER");
        }
    }
}
