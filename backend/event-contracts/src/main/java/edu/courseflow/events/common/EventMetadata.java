package edu.courseflow.events.common;

import java.util.Map;

public record EventMetadata(
        String correlationId,
        String causationId,
        String actorId,
        Map<String, String> attributes
) {
}
