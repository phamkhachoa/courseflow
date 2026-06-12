package edu.courseflow.peerreview.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.math.BigDecimal;

public record SubmitReviewRequestDto(
        @NotNull BigDecimal score,
        @NotBlank String comment
) {
}
