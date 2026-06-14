package edu.courseflow.outboxrelay.relay;

public record OperatorActionRecord(
        String status,
        String requestHash,
        String responseJson) {
}
