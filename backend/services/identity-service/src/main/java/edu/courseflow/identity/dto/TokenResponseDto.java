package edu.courseflow.identity.dto;

public record TokenResponseDto(
        String accessToken,
        String refreshToken,
        String tokenType,
        long expiresInSeconds,
        UserDto user) {
}
