package edu.courseflow.gateway;

import java.util.Set;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtValidators;

final class OAuth2AudienceValidator implements OAuth2TokenValidator<Jwt> {

    private final Set<String> audiences;

    OAuth2AudienceValidator(Set<String> audiences) {
        this.audiences = audiences == null ? Set.of() : Set.copyOf(audiences);
    }

    @Override
    public OAuth2TokenValidatorResult validate(Jwt token) {
        if (token.getSubject() == null || token.getSubject().isBlank()) {
            return OAuth2TokenValidatorResult.failure(new OAuth2Error(
                    "invalid_token",
                    "Token subject is required by CourseFlow",
                    null));
        }
        if (audiences.isEmpty() || token.getAudience().stream().anyMatch(audiences::contains)) {
            return OAuth2TokenValidatorResult.success();
        }
        return OAuth2TokenValidatorResult.failure(new OAuth2Error(
                "invalid_token",
                "Token audience is not accepted by CourseFlow",
                null));
    }

    static OAuth2TokenValidator<Jwt> issuerAndAudience(String issuer, Set<String> audiences) {
        return new DelegatingOAuth2TokenValidator<>(
                JwtValidators.createDefaultWithIssuer(issuer),
                new OAuth2AudienceValidator(audiences));
    }
}
