package edu.courseflow.identity.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

public final class EmailVerificationDtos {

    private EmailVerificationDtos() {
    }

    public record RegistrationResponseDto(
            UserDto user,
            boolean emailVerificationRequired,
            Instant verificationExpiresAt) {
    }

    public record VerifyEmailRequestDto(
            @NotBlank String token) {
    }

    public record ResendEmailVerificationRequestDto(
            @NotBlank @Email String email) {
    }
}
