package edu.courseflow.identity.dto;

public record UserDto(
        Long id,
        String email,
        String fullName,
        String status,
        boolean emailVerified,
        boolean mfaEnabled) {
}
