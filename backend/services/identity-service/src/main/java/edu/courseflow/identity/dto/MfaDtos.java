package edu.courseflow.identity.dto;

import jakarta.validation.constraints.NotBlank;

public final class MfaDtos {

    private MfaDtos() {
    }

    public record MfaEnrollmentDto(
            String secret,
            String otpAuthUri) {
    }

    public record ConfirmMfaRequestDto(
            @NotBlank String code) {
    }

    public record DisableMfaRequestDto(
            @NotBlank String code) {
    }
}
