package edu.courseflow.identity.model;

/**
 * Constants for built-in system role codes. Roles are stored in DB — this class
 * only gives
 * compile-time safety when referring to a well-known role (e.g. the default
 * role for a new user).
 */
public final class SystemRoles {
    public static final String ADMIN = "ADMIN";
    public static final String ORG_ADMIN = "ORG_ADMIN";
    public static final String INSTRUCTOR = "INSTRUCTOR";
    public static final String PROFESSOR = "PROFESSOR";
    public static final String TA = "TA";
    public static final String STUDENT = "STUDENT";

    private SystemRoles() {
    }
}
