package edu.courseflow.events.common;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;

public interface CourseFlowEvent {
    @NotBlank
    String eventId();

    @NotBlank
    String eventType();

    @NotBlank
    String aggregateId();

    @NotBlank
    String aggregateType();

    @NotNull
    Instant occurredAt();
}
