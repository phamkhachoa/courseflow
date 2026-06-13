package edu.courseflow.gateway;

import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import org.springframework.security.oauth2.jwt.NimbusReactiveJwtDecoder;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

@Component
public class ConfiguredGatewayExternalTokenVerifier implements GatewayExternalTokenVerifier {

    private final ExternalTokenProperties properties;
    private final ReactiveJwtDecoder oidcDecoder;

    public ConfiguredGatewayExternalTokenVerifier(ExternalTokenProperties properties) {
        this.properties = properties;
        this.oidcDecoder = properties.legacyMode() ? null : oidcDecoder(properties);
    }

    @Override
    public Mono<Void> verify(String token) {
        if (token == null || token.isBlank()) {
            return Mono.error(new IllegalArgumentException("Bearer token is missing"));
        }
        if (properties.legacyMode()) {
            return Mono.fromRunnable(() -> verifyLegacy(token));
        }
        return oidcDecoder.decode(token.trim()).then();
    }

    private void verifyLegacy(String token) {
        try {
            var claims = Jwts.parser()
                    .verifyWith(properties.legacySecretKey())
                    .build()
                    .parseSignedClaims(token.trim())
                    .getPayload();
            if (!properties.legacyIssuer().isBlank()
                    && !properties.legacyIssuer().equals(claims.getIssuer())) {
                throw new JwtException("Unexpected legacy token issuer");
            }
        } catch (JwtException | IllegalArgumentException ex) {
            throw ex;
        }
    }

    private ReactiveJwtDecoder oidcDecoder(ExternalTokenProperties properties) {
        NimbusReactiveJwtDecoder decoder = NimbusReactiveJwtDecoder.withJwkSetUri(properties.jwkSetUri()).build();
        decoder.setJwtValidator(OAuth2AudienceValidator.issuerAndAudience(
                properties.oidcIssuer(),
                properties.audiences()));
        return decoder;
    }
}
