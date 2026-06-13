package edu.courseflow.tokenconverter.service;

import edu.courseflow.tokenconverter.config.TokenConverterProperties;
import edu.courseflow.tokenconverter.dto.TokenExchangeResponse;
import io.jsonwebtoken.Claims;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class TokenExchangeService {

    public static final String TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange";
    public static final String ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token";

    private final ExternalTokenVerifier externalTokenVerifier;
    private final InternalTokenIssuer internalTokenIssuer;
    private final TokenConverterProperties properties;

    public TokenExchangeService(ExternalTokenVerifier externalTokenVerifier,
            InternalTokenIssuer internalTokenIssuer,
            TokenConverterProperties properties) {
        this.externalTokenVerifier = externalTokenVerifier;
        this.internalTokenIssuer = internalTokenIssuer;
        this.properties = properties;
    }

    public TokenExchangeResponse exchange(String grantType, String subjectTokenType, String subjectToken,
                                          String audience, String requestedScope) {
        if (!TOKEN_EXCHANGE_GRANT.equals(grantType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported grant_type");
        }
        if (subjectTokenType != null && !subjectTokenType.isBlank()
                && !ACCESS_TOKEN_TYPE.equals(subjectTokenType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported subject_token_type");
        }
        String resolvedAudience = audience == null || audience.isBlank() ? properties.defaultAudience() : audience.trim();
        if (!properties.allowedAudiences().contains(resolvedAudience)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Audience is not allowed");
        }
        Claims externalClaims = externalTokenVerifier.verify(subjectToken);
        InternalTokenIssuer.IssuedInternalToken issued = internalTokenIssuer.issue(
                externalClaims,
                resolvedAudience,
                requestedScope);
        return new TokenExchangeResponse(
                issued.token(),
                ACCESS_TOKEN_TYPE,
                "Bearer",
                issued.expiresInSeconds(),
                String.join(" ", issued.scopes()));
    }
}
