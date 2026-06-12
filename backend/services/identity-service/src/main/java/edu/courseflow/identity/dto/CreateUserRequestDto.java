package edu.courseflow.identity.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * {@code role} is optional. If omitted, the new user is assigned the
 * platform-wide STUDENT role.
 * Non-default roles must be granted via
 * {@code POST /internal/users/{userId}/assignments}
 * (ADMIN-gated) — keeping role escalation out of plain user creation.
 */
public record CreateUserRequestDto(
        @NotBlank @Email String email,
        @NotBlank @Size(min = 12) String password,
        @NotBlank String fullName,
        String role) {
}
