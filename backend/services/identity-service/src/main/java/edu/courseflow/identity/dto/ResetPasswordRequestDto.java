package edu.courseflow.identity.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ResetPasswordRequestDto(
        @NotBlank @Size(min = 12) String newPassword,
        Boolean mustChangePassword) {
}
