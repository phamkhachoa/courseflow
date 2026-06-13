package edu.courseflow.tokenconverter.service;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtValidationException;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class ExternalTokenVerifier {

    private final TokenConverterProperties properties;
    private final JwtDecoder oidcDecoder;

    public ExternalTokenVerifier(TokenConverterProperties properties) {
        this.properties = properties;
        this.oidcDecoder = properties.oidcExternalTokenMode() ? oidcDecoder(properties) : null;
    }

    public ExternalTokenClaims verify(String token) {
        if (token == null || token.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "subject_token is required");
        }
        if (properties.oidcExternalTokenMode()) {
            return verifyOidc(token);
        }
        return verifyLegacy(token);
    }

    private ExternalTokenClaims verifyLegacy(String token) {
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(properties.externalJwtKey())
                    .clockSkewSeconds(properties.clockSkewSeconds())
                    .build()
                    .parseSignedClaims(token.trim())
                    .getPayload();
            if (!properties.externalJwtIssuer().equals(claims.getIssuer())) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Unexpected external token issuer");
            }
            requireClaim(claims, "uid");
            if (claims.getSubject() == null || claims.getSubject().isBlank()) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "External token subject is missing");
            }
            return new ExternalTokenClaims(claims.getIssuer(), claims.getSubject(), new LinkedHashMap<>(claims));
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (JwtException | IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid external token", ex);
        }
    }

    private ExternalTokenClaims verifyOidc(String token) {
        try {
            Jwt jwt = oidcDecoder.decode(token.trim());
            Map<String, Object> claims = new LinkedHashMap<>(jwt.getClaims());
            return new ExternalTokenClaims(
                    jwt.getIssuer() == null ? null : jwt.getIssuer().toString(),
                    jwt.getSubject(),
                    claims);
        } catch (JwtValidationException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid external token", ex);
        } catch (org.springframework.security.oauth2.jwt.JwtException | IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid external token", ex);
        }
    }

    private JwtDecoder oidcDecoder(TokenConverterProperties properties) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withJwkSetUri(properties.externalJwkSetUri()).build();
        decoder.setJwtValidator(OAuth2AudienceValidator.issuerAndAudience(
                properties.externalOidcIssuer(),
                properties.externalAudiences()));
        return decoder;
    }

    private void requireClaim(Claims claims, String name) {
        Object value = claims.get(name);
        if (value == null || value.toString().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "External token claim is missing: " + name);
        }
    }
}
