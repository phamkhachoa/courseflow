package edu.courseflow.commonlibrary.security;

public final class InternalScopes {

    public static final String SERVICE = "internal:service";
    public static final String TOKEN_EXCHANGE = "internal:token-exchange";
    public static final String USER = "internal:user";
    public static final String IDENTITY_RESOLVE = "internal:identity:resolve";
    public static final String IDENTITY_PROVISION = "internal:identity:provision";
    public static final String AUTHZ_CHECK = "internal:authz:check";
    public static final String AUTHZ_ASSERT_TOPOLOGY = "internal:authz:assert-topology";
    public static final String USER_DIRECTORY_READ = "internal:user-directory:read";
    public static final String USER_DIRECTORY_WRITE = "internal:user-directory:write";
    public static final String ROLE_ASSIGNMENT_READ = "internal:role-assignment:read";
    public static final String ROLE_ASSIGNMENT_WRITE = "internal:role-assignment:write";
    public static final String ROLE_MANAGEMENT_READ = "internal:role-management:read";
    public static final String ROLE_MANAGEMENT_WRITE = "internal:role-management:write";
    public static final String PROFILE_READ = "internal:profile:read";
    public static final String PROFILE_WRITE = "internal:profile:write";
    public static final String BACKOFFICE = "internal:backoffice";

    private InternalScopes() {
    }
}
