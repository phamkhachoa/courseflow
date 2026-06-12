package edu.courseflow.course.dto;

public record ModuleItemDto(
        String id,
        String itemType,
        String itemId,
        String title,
        String description,
        String videoMediaId,
        java.util.List<String> documentMediaIds,
        String contentUrl,
        Integer estimatedMinutes,
        int position,
        boolean required
) {
}
