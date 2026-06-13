package edu.courseflow.identity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ChangePasswordRequestDto(
        String email,
        @NotBlank String currentPassword,
        @NotBlank @Size(min = 12) String newPassword) {
}
