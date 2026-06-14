package edu.courseflow.promotion.service;

import java.time.Duration;

public interface CouponAbuseRateLimitStore {

    Hit hit(String key, int capacity, Duration window);

    record Hit(long count, boolean allowed) {
    }
}
