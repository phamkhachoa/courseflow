package edu.courseflow.promotion.model;

import java.time.Instant;
import java.util.UUID;

public interface CampaignDefinitionSnapshot {

    UUID getCampaignId();

    int getCampaignVersion();

    String getTenantId();

    String getApplicationId();

    String getCode();

    String getName();

    String getDescription();

    String getIncentiveType();

    Instant getStartsAt();

    Instant getEndsAt();

    int getPriority();

    boolean isExclusive();

    boolean isStackable();

    boolean isCouponRequired();

    String getMatchPolicy();

    String getCurrency();

    String getRulesJson();

    String getActionsJson();

    Integer getMaxRedemptions();

    Integer getMaxRedemptionsPerProfile();
}
