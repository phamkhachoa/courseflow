package edu.courseflow.identity.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record RegisterRequestDto(
        @NotBlank @Email String email,
        @NotBlank String password,
        @NotBlank String fullName) {
}
