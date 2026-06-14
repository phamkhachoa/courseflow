package edu.courseflow.promotion.repository;

import java.time.Instant;

public interface RetentionDryRunStats {
    long getEligibleCount();

    long getBlockedCount();

    Instant getOldestCandidateAt();

    Instant getNewestCandidateAt();
}
