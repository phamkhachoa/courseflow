package edu.courseflow.commonlibrary.security;

import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.JwsHeader;
import io.jsonwebtoken.LocatorAdapter;
import java.math.BigInteger;
import java.security.Key;
import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.spec.RSAPublicKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

class InternalJwksKeyLocator extends LocatorAdapter<Key> {

    private final InternalJwtProperties properties;
    private final RestClient jwksClient;
    private volatile CachedKeys cachedKeys = new CachedKeys(Map.of(), Instant.EPOCH);

    InternalJwksKeyLocator(InternalJwtProperties properties, RestClient jwksClient) {
        this.properties = properties;
        this.jwksClient = jwksClient;
    }

    @Override
    protected Key locate(JwsHeader header) {
        String kid = header.getKeyId();
        Map<String, PublicKey> keys = keys(false);
        PublicKey key = selectKey(kid, keys);
        if (key != null) {
            return key;
        }
        keys = keys(true);
        key = selectKey(kid, keys);
        if (key != null) {
            return key;
        }
        throw new JwtException("No internal JWKS key found for kid: " + (kid == null ? "<missing>" : kid));
    }

    private PublicKey selectKey(String kid, Map<String, PublicKey> keys) {
        if (kid != null && !kid.isBlank()) {
            return keys.get(kid);
        }
        return keys.size() == 1 ? keys.values().iterator().next() : null;
    }

    private Map<String, PublicKey> keys(boolean forceRefresh) {
        CachedKeys current = cachedKeys;
        if (!forceRefresh && current.expiresAt().isAfter(Instant.now()) && !current.keys().isEmpty()) {
            return current.keys();
        }
        synchronized (this) {
            current = cachedKeys;
            if (!forceRefresh && current.expiresAt().isAfter(Instant.now()) && !current.keys().isEmpty()) {
                return current.keys();
            }
            CachedKeys refreshed = fetchKeys();
            cachedKeys = refreshed;
            return refreshed.keys();
        }
    }

    private CachedKeys fetchKeys() {
        if (properties.jwksUri().isBlank()) {
            throw new JwtException("COURSEFLOW_INTERNAL_JWT_JWKS_URI is required for JWKS verification");
        }
        try {
            Map<String, Object> response = jwksClient.get()
                    .uri(properties.jwksUri())
                    .retrieve()
                    .body(new ParameterizedTypeReference<>() {
                    });
            Map<String, PublicKey> parsed = parseKeys(response);
            if (parsed.isEmpty()) {
                throw new JwtException("Internal JWKS did not contain any usable RS256 keys");
            }
            return new CachedKeys(Map.copyOf(parsed),
                    Instant.now().plusSeconds(properties.jwksCacheTtlSeconds()));
        } catch (RestClientException ex) {
            throw new JwtException("Could not load internal JWKS", ex);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, PublicKey> parseKeys(Map<String, Object> response) {
        if (response == null || !(response.get("keys") instanceof List<?> keys)) {
            return Map.of();
        }
        Map<String, PublicKey> parsed = new LinkedHashMap<>();
        for (Object raw : keys) {
            if (!(raw instanceof Map<?, ?> rawMap)) {
                continue;
            }
            Map<String, Object> key = (Map<String, Object>) rawMap;
            String kid = stringValue(key.get("kid"));
            String kty = stringValue(key.get("kty"));
            String alg = stringValue(key.get("alg"));
            if (kid == null || !"RSA".equals(kty) || (alg != null && !"RS256".equals(alg))) {
                continue;
            }
            String modulus = stringValue(key.get("n"));
            String exponent = stringValue(key.get("e"));
            if (modulus == null || exponent == null) {
                continue;
            }
            parsed.put(kid, rsaPublicKey(modulus, exponent));
        }
        return parsed;
    }

    private PublicKey rsaPublicKey(String modulus, String exponent) {
        try {
            BigInteger n = new BigInteger(1, Base64.getUrlDecoder().decode(modulus));
            BigInteger e = new BigInteger(1, Base64.getUrlDecoder().decode(exponent));
            return KeyFactory.getInstance("RSA").generatePublic(new RSAPublicKeySpec(n, e));
        } catch (Exception ex) {
            throw new JwtException("Invalid internal JWKS RSA key", ex);
        }
    }

    private String stringValue(Object value) {
        return value == null || value.toString().isBlank() ? null : value.toString();
    }

    private record CachedKeys(Map<String, PublicKey> keys, Instant expiresAt) {
    }
}
