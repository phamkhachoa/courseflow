package edu.courseflow.identity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record DeactivateUserRequestDto(
        @NotBlank
        @Size(max = 255)
        String reason) {
}
