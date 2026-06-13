package edu.courseflow.assignment.web;

import edu.courseflow.commonlibrary.web.CurrentUser;

/**
 * Centralised authorization checks for this service. Identity is supplied by the gateway via the
 * {@link CurrentUser} resolver; controllers must never trust identity fields in the request body.
 *
 * <p>Course-scoped staff authorization belongs at controller boundaries via
 * {@code CourseAccessClient.requireCourseStaffAccess(...)}. These helpers only answer coarse
 * identity/self checks.
 */
public final class Authz {

    public static final String ROLE_STUDENT = "STUDENT";
    public static final String ROLE_TA = "TA";
    public static final String ROLE_INSTRUCTOR = "INSTRUCTOR";
    public static final String ROLE_PROFESSOR = "PROFESSOR";
    public static final String ROLE_ORG_ADMIN = "ORG_ADMIN";
    public static final String ROLE_ADMIN = "ADMIN";

    private Authz() {
    }

    /** Caller identity as the string used in persistence columns (student_id, grader_id, ...). */
    public static String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("UNAUTHENTICATED");
        }
        return String.valueOf(user.id());
    }

    public static boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole(ROLE_TA, ROLE_INSTRUCTOR, ROLE_PROFESSOR, ROLE_ORG_ADMIN, ROLE_ADMIN);
    }

    /** Require a staff role before the controller applies course-scope authorization. */
    public static void requireStaff(CurrentUser user) {
        if (!isStaff(user)) {
            throw new ForbiddenException("FORBIDDEN_REQUIRES_COURSE_STAFF");
        }
    }

    /**
     * Require the caller to be the owner of the data (its student) or staff. Used for reads/writes of
     * a specific student's records.
     */
    public static void requireSelfOrStaff(CurrentUser user, String ownerStudentId) {
        if (isStaff(user)) {
            return;
        }
        if (ownerStudentId == null || !ownerStudentId.equals(callerId(user))) {
            throw new ForbiddenException("FORBIDDEN_NOT_OWNER");
        }
    }
}
