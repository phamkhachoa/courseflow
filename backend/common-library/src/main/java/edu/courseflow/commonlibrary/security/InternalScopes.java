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
    public static final String ANALYTICS_FUNNEL_WRITE = "internal:analytics:funnel-write";
    public static final String ANALYTICS_EXPORT_READ = "internal:analytics:export-read";
    public static final String ANALYTICS_EVENT_WRITE = "internal:analytics:event-write";
    public static final String ANALYTICS_MODEL_WRITE = "internal:analytics:model-write";
    public static final String RECOMMENDATION_ML_TRAIN = "internal:recommendation-ml:train";
    public static final String RECOMMENDATION_ML_INFER = "internal:recommendation-ml:infer";
    public static final String RECOMMENDATION_ML_OPS = "internal:recommendation-ml:ops";
    public static final String PROMOTION_ADMIN = "internal:promotion:admin";
    public static final String PROMOTION_EVALUATE = "internal:promotion:evaluate";
    public static final String PROMOTION_RESERVE = "internal:promotion:reserve";
    public static final String PROMOTION_COMMIT = "internal:promotion:commit";
    public static final String PROMOTION_CANCEL = "internal:promotion:cancel";
    public static final String PROMOTION_REVERSE = "internal:promotion:reverse";
    public static final String LOYALTY_ADMIN = "internal:loyalty:admin";
    public static final String LOYALTY_READ = "internal:loyalty:read";
    public static final String LOYALTY_EARN = "internal:loyalty:earn";
    public static final String LOYALTY_BURN = "internal:loyalty:burn";
    public static final String LOYALTY_REVERSE = "internal:loyalty:reverse";
    public static final String LOYALTY_ADJUST = "internal:loyalty:adjust";
    public static final String LOYALTY_EXPIRE = "internal:loyalty:expire";

    private InternalScopes() {
    }
}
