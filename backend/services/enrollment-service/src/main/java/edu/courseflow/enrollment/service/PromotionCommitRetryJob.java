package edu.courseflow.enrollment.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class PromotionCommitRetryJob {

    private final EnrollmentService enrollments;
    private final boolean enabled;
    private final int batchSize;

    public PromotionCommitRetryJob(
            EnrollmentService enrollments,
            @Value("${courseflow.enrollment.promotion-commit-retry.enabled:true}") boolean enabled,
            @Value("${courseflow.enrollment.promotion-commit-retry.batch-size:25}") int batchSize) {
        this.enrollments = enrollments;
        this.enabled = enabled;
        this.batchSize = batchSize;
    }

    @Scheduled(fixedDelayString = "${courseflow.enrollment.promotion-commit-retry.fixed-delay-ms:60000}")
    public void retryPendingPromotionCommits() {
        if (!enabled) {
            return;
        }
        enrollments.retryPromotionCommitFailures(batchSize);
        enrollments.openReservedPromotionRemediationCases(batchSize);
    }
}
