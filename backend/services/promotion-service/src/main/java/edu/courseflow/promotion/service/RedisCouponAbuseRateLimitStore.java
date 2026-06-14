package edu.courseflow.promotion.service;

import java.time.Duration;
import java.util.List;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Component;

@Component
public class RedisCouponAbuseRateLimitStore implements CouponAbuseRateLimitStore {

    private static final DefaultRedisScript<Long> HIT_SCRIPT = new DefaultRedisScript<>("""
            local current = redis.call('INCR', KEYS[1])
            if current == 1 then
              redis.call('PEXPIRE', KEYS[1], ARGV[1])
            end
            return current
            """, Long.class);

    private final StringRedisTemplate redis;

    public RedisCouponAbuseRateLimitStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public Hit hit(String key, int capacity, Duration window) {
        long ttlMs = Math.max(1, window.toMillis());
        Long count = redis.execute(HIT_SCRIPT, List.of(key), Long.toString(ttlMs));
        long current = count == null ? 0 : count;
        return new Hit(current, current <= capacity);
    }
}
