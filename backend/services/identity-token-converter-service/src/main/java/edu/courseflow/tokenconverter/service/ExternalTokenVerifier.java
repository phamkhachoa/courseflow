package edu.courseflow.tokenconverter.service;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class ExternalTokenVerifier {

    private final TokenConverterProperties properties;

    public ExternalTokenVerifier(TokenConverterProperties properties) {
        this.properties = properties;
    }

    public Claims verify(String token) {
        if (token == null || token.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "subject_token is required");
        }
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
            return claims;
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (JwtException | IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid external token", ex);
        }
    }

    private void requireClaim(Claims claims, String name) {
        Object value = claims.get(name);
        if (value == null || value.toString().isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "External token claim is missing: " + name);
        }
    }
}
