package edu.courseflow.tokenconverter.service;

import java.util.LinkedHashMap;
import java.util.Map;

public record ExternalTokenClaims(String issuer, String subject, Map<String, Object> claims) {

    public ExternalTokenClaims {
        claims = claims == null ? Map.of() : Map.copyOf(new LinkedHashMap<>(claims));
    }

    public Object get(String name) {
        return claims.get(name);
    }

    public String stringClaim(String name) {
        Object value = claims.get(name);
        return value == null || value.toString().isBlank() ? null : value.toString();
    }
}
