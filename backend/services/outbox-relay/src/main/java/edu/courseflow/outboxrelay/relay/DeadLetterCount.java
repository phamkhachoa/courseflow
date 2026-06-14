package edu.courseflow.outboxrelay.relay;

public record DeadLetterCount(
        String serviceName,
        String eventType,
        long count,
        double oldestAgeSeconds) {
}
