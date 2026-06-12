package edu.courseflow.identity.dto;

import jakarta.validation.constraints.NotBlank;

public record RefreshRequestDto(@NotBlank String refreshToken) {
}
