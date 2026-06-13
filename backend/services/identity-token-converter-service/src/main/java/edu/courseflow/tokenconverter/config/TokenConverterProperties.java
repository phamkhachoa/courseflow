package edu.courseflow.tokenconverter.config;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.interfaces.RSAPrivateCrtKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.RSAPublicKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class TokenConverterProperties {

    private static final int MIN_SECRET_BYTES = 32;
    private static final String DEFAULT_STS_ALLOWED_CLIENTS = "api-gateway,access-control-service,"
            + "user-management-service,organization-service,course-service,enrollment-service,assignment-service,"
            + "deadline-service,announcement-service,portfolio-service,discussion-service,notification-service,"
            + "chat-service,media-service,search-service,analytics-service,gradebook-service,quiz-service,"
            + "certificate-service,peer-review-service,live-session-service,review-service,outbox-relay";
    private static final String DEFAULT_STS_ALLOWED_SERVICE_SCOPES = "internal:service,internal:token-exchange,"
            + "internal:user,"
            + "internal:identity:resolve,internal:identity:provision,internal:authz:check,"
            + "internal:authz:assert-topology,"
            + "internal:user-directory:read,internal:user-directory:write,internal:role-assignment:read,"
            + "internal:role-assignment:write,internal:role-management:read,internal:role-management:write,"
            + "internal:profile:read,internal:profile:write,internal:backoffice";

    private final ExternalTokenMode externalTokenMode;
    private final String externalJwtSecret;
    private final String externalJwtIssuer;
    private final String externalOidcIssuer;
    private final String externalJwkSetUri;
    private final Set<String> externalAudiences;
    private final InternalJwtAlgorithm internalJwtAlgorithm;
    private final String internalJwtSecret;
    private final String internalJwtPrivateKey;
    private final String internalJwtPublicKey;
    private final String internalJwtIssuer;
    private final String defaultAudience;
    private final Set<String> allowedAudiences;
    private final String stsClientSecret;
    private final Map<String, String> serviceClientSecrets;
    private final Set<String> allowedServiceClients;
    private final Set<String> allowedServiceScopes;
    private final Map<String, Set<String>> serviceClientScopes;
    private final long ttlSeconds;
    private final long clockSkewSeconds;

    @Autowired
    public TokenConverterProperties(
            @Value("${courseflow.security.external-token.mode:${EXTERNAL_TOKEN_MODE:oidc}}")
            String externalTokenMode,
            @Value("${courseflow.security.external-jwt.secret:}") String externalJwtSecret,
            @Value("${courseflow.security.external-jwt.issuer:courseflow-identity}") String externalJwtIssuer,
            @Value("${courseflow.security.external-token.issuer:${KEYCLOAK_ISSUER_URI:}}")
            String externalOidcIssuer,
            @Value("${courseflow.security.external-token.jwk-set-uri:${KEYCLOAK_JWK_SET_URI:}}")
            String externalJwkSetUri,
            @Value("${courseflow.security.external-token.audiences:${KEYCLOAK_AUDIENCE:courseflow-api}}")
            String externalAudiences,
            @Value("${courseflow.security.internal-jwt.algorithm:${COURSEFLOW_INTERNAL_JWT_ALGORITHM:HS256}}")
            String internalJwtAlgorithm,
            @Value("${courseflow.security.internal-jwt.secret:}") String internalJwtSecret,
            @Value("${courseflow.security.internal-jwt.private-key:${COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY:}}")
            String internalJwtPrivateKey,
            @Value("${courseflow.security.internal-jwt.public-key:${COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY:}}")
            String internalJwtPublicKey,
            @Value("${courseflow.security.internal-jwt.issuer:courseflow-token-converter}") String internalJwtIssuer,
            @Value("${courseflow.security.internal-jwt.audience:courseflow-services}") String defaultAudience,
            @Value("${courseflow.security.internal-jwt.allowed-audiences:courseflow-services}")
            String allowedAudiences,
            @Value("${courseflow.security.sts.client-secret:${COURSEFLOW_STS_CLIENT_SECRET:}}")
            String stsClientSecret,
            @Value("${courseflow.security.sts.client-secrets:${COURSEFLOW_STS_CLIENT_SECRETS:}}")
            String serviceClientSecrets,
            @Value("${courseflow.security.sts.allowed-clients:${COURSEFLOW_STS_ALLOWED_CLIENTS:"
                    + DEFAULT_STS_ALLOWED_CLIENTS + "}}")
            String allowedServiceClients,
            @Value("${courseflow.security.sts.allowed-service-scopes:${COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES:"
                    + DEFAULT_STS_ALLOWED_SERVICE_SCOPES + "}}")
            String allowedServiceScopes,
            @Value("${courseflow.security.sts.client-scopes:${COURSEFLOW_STS_CLIENT_SCOPES:}}")
            String serviceClientScopes,
            @Value("${courseflow.security.internal-jwt.ttl-seconds:180}") long ttlSeconds,
            @Value("${courseflow.security.internal-jwt.clock-skew-seconds:30}") long clockSkewSeconds) {
        this.externalTokenMode = parseExternalMode(externalTokenMode);
        this.externalJwtSecret = this.externalTokenMode == ExternalTokenMode.LEGACY
                ? validateSecret(externalJwtSecret, "COURSEFLOW_JWT_SECRET")
                : trimToDefault(externalJwtSecret, "");
        this.externalJwtIssuer = trimToDefault(externalJwtIssuer, "courseflow-identity");
        this.externalOidcIssuer = this.externalTokenMode == ExternalTokenMode.OIDC
                ? requireNonBlank(externalOidcIssuer, "KEYCLOAK_ISSUER_URI")
                : trimToDefault(externalOidcIssuer, this.externalJwtIssuer);
        this.externalJwkSetUri = trimToDefault(externalJwkSetUri, defaultKeycloakJwkSetUri(this.externalOidcIssuer));
        this.externalAudiences = parseAudiences(externalAudiences, "courseflow-api");
        this.internalJwtAlgorithm = parseInternalAlgorithm(internalJwtAlgorithm);
        this.internalJwtSecret = this.internalJwtAlgorithm == InternalJwtAlgorithm.HS256
                ? validateSecret(internalJwtSecret, "COURSEFLOW_INTERNAL_JWT_SECRET")
                : trimToDefault(internalJwtSecret, "");
        this.internalJwtPrivateKey = this.internalJwtAlgorithm == InternalJwtAlgorithm.RS256
                ? requireNonBlank(normalizePem(internalJwtPrivateKey), "COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY")
                : "";
        this.internalJwtPublicKey = this.internalJwtAlgorithm == InternalJwtAlgorithm.RS256
                ? normalizePem(internalJwtPublicKey)
                : "";
        this.internalJwtIssuer = trimToDefault(internalJwtIssuer, "courseflow-token-converter");
        this.defaultAudience = trimToDefault(defaultAudience, "courseflow-services");
        this.allowedAudiences = parseAudiences(allowedAudiences, this.defaultAudience);
        this.stsClientSecret = trimToDefault(stsClientSecret, "");
        this.serviceClientSecrets = parseClientSecrets(serviceClientSecrets);
        this.allowedServiceClients = parseAudiences(allowedServiceClients, "*");
        this.allowedServiceScopes = parseAudiences(allowedServiceScopes, "internal:service");
        this.serviceClientScopes = parseClientScopes(serviceClientScopes);
        validateOidcStsPolicy();
        this.ttlSeconds = Math.max(30, Math.min(ttlSeconds, 900));
        this.clockSkewSeconds = Math.max(0, Math.min(clockSkewSeconds, 120));
    }

    public TokenConverterProperties(String externalTokenMode,
            String externalJwtSecret,
            String externalJwtIssuer,
            String externalOidcIssuer,
            String externalJwkSetUri,
            String externalAudiences,
            String internalJwtAlgorithm,
            String internalJwtSecret,
            String internalJwtPrivateKey,
            String internalJwtIssuer,
            String defaultAudience,
            String allowedAudiences,
            long ttlSeconds,
            long clockSkewSeconds) {
        this(externalTokenMode,
                externalJwtSecret,
                externalJwtIssuer,
                externalOidcIssuer,
                externalJwkSetUri,
                externalAudiences,
                internalJwtAlgorithm,
                internalJwtSecret,
                internalJwtPrivateKey,
                "",
                internalJwtIssuer,
                defaultAudience,
                allowedAudiences,
                "",
                "",
                DEFAULT_STS_ALLOWED_CLIENTS,
                DEFAULT_STS_ALLOWED_SERVICE_SCOPES,
                "",
                ttlSeconds,
                clockSkewSeconds);
    }

    public TokenConverterProperties(String externalTokenMode,
            String externalJwtSecret,
            String externalJwtIssuer,
            String externalOidcIssuer,
            String externalJwkSetUri,
            String externalAudiences,
            String internalJwtAlgorithm,
            String internalJwtSecret,
            String internalJwtPrivateKey,
            String internalJwtPublicKey,
            String internalJwtIssuer,
            String defaultAudience,
            String allowedAudiences,
            String stsClientSecret,
            String allowedServiceClients,
            String allowedServiceScopes,
            long ttlSeconds,
            long clockSkewSeconds) {
        this(externalTokenMode,
                externalJwtSecret,
                externalJwtIssuer,
                externalOidcIssuer,
                externalJwkSetUri,
                externalAudiences,
                internalJwtAlgorithm,
                internalJwtSecret,
                internalJwtPrivateKey,
                internalJwtPublicKey,
                internalJwtIssuer,
                defaultAudience,
                allowedAudiences,
                stsClientSecret,
                "",
                allowedServiceClients,
                allowedServiceScopes,
                "",
                ttlSeconds,
                clockSkewSeconds);
    }

    public TokenConverterProperties(String externalTokenMode,
            String externalJwtSecret,
            String externalJwtIssuer,
            String externalOidcIssuer,
            String externalJwkSetUri,
            String externalAudiences,
            String internalJwtSecret,
            String internalJwtIssuer,
            String defaultAudience,
            String allowedAudiences,
            long ttlSeconds,
            long clockSkewSeconds) {
        this(externalTokenMode,
                externalJwtSecret,
                externalJwtIssuer,
                externalOidcIssuer,
                externalJwkSetUri,
                externalAudiences,
                "HS256",
                internalJwtSecret,
                "",
                "",
                internalJwtIssuer,
                defaultAudience,
                allowedAudiences,
                "",
                "",
                DEFAULT_STS_ALLOWED_CLIENTS,
                DEFAULT_STS_ALLOWED_SERVICE_SCOPES,
                "",
                ttlSeconds,
                clockSkewSeconds);
    }

    public boolean legacyExternalTokenMode() {
        return externalTokenMode == ExternalTokenMode.LEGACY;
    }

    public boolean oidcExternalTokenMode() {
        return externalTokenMode == ExternalTokenMode.OIDC;
    }

    public SecretKey externalJwtKey() {
        return Keys.hmacShaKeyFor(externalJwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    public String externalJwtIssuer() {
        return externalJwtIssuer;
    }

    public String externalOidcIssuer() {
        return externalOidcIssuer;
    }

    public String externalJwkSetUri() {
        return externalJwkSetUri;
    }

    public Set<String> externalAudiences() {
        return externalAudiences;
    }

    public SecretKey internalJwtKey() {
        if (internalJwtAlgorithm == InternalJwtAlgorithm.RS256) {
            throw new IllegalStateException("Internal JWT algorithm is RS256");
        }
        return Keys.hmacShaKeyFor(internalJwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    public PrivateKey internalJwtPrivateKey() {
        if (internalJwtAlgorithm != InternalJwtAlgorithm.RS256) {
            throw new IllegalStateException("Internal JWT algorithm is not RS256");
        }
        return parsePrivateKey(internalJwtPrivateKey);
    }

    public PublicKey internalJwtPublicKey() {
        if (internalJwtAlgorithm != InternalJwtAlgorithm.RS256) {
            throw new IllegalStateException("Internal JWT algorithm is not RS256");
        }
        if (!internalJwtPublicKey.isBlank()) {
            return parsePublicKey(internalJwtPublicKey);
        }
        return publicKeyFromPrivateKey(internalJwtPrivateKey());
    }

    public String internalJwtKeyId() {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(internalJwtPublicKey().getEncoded());
            return Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(Arrays.copyOf(digest, 12));
        } catch (Exception ex) {
            throw new IllegalStateException("Could not calculate internal JWT key id", ex);
        }
    }

    public boolean internalJwtRs256() {
        return internalJwtAlgorithm == InternalJwtAlgorithm.RS256;
    }

    public String internalJwtIssuer() {
        return internalJwtIssuer;
    }

    public String defaultAudience() {
        return defaultAudience;
    }

    public Set<String> allowedAudiences() {
        return allowedAudiences;
    }

    public boolean serviceClientAllowed(String clientId) {
        if (clientId == null || clientId.isBlank()) {
            return false;
        }
        String normalized = clientId.trim();
        if (!serviceClientSecrets.isEmpty()) {
            return serviceClientSecrets.containsKey(normalized);
        }
        return allowedServiceClients.contains("*") || allowedServiceClients.contains(normalized);
    }

    public boolean serviceClientSecretMatches(String clientId, String clientSecret) {
        if (clientId == null || clientId.isBlank() || clientSecret == null || clientSecret.isBlank()) {
            return false;
        }
        if (!serviceClientSecrets.isEmpty()) {
            String expected = serviceClientSecrets.get(clientId.trim());
            return secretEquals(expected, clientSecret.trim());
        }
        return secretEquals(stsClientSecret, clientSecret.trim());
    }

    public boolean serviceClientSecretMatches(String clientSecret) {
        return serviceClientSecretMatches("*", clientSecret);
    }

    public Set<String> allowedServiceScopes() {
        return allowedServiceScopes;
    }

    public Set<String> allowedServiceScopes(String clientId) {
        if (clientId != null && !clientId.isBlank()) {
            Set<String> scoped = serviceClientScopes.get(clientId.trim());
            if (scoped != null) {
                return scoped;
            }
        }
        return allowedServiceScopes;
    }

    public List<String> serviceScopesForClient(String clientId, String requestedScope) {
        Set<String> requested = parseScopes(requestedScope);
        if (requested.isEmpty()) {
            requested.add("internal:service");
        }
        Set<String> allowed = allowedServiceScopes(clientId);
        if (!allowed.contains("*") && !allowed.containsAll(requested)) {
            Set<String> denied = new LinkedHashSet<>(requested);
            denied.removeAll(allowed);
            throw new IllegalArgumentException("Requested service scope is not allowed for client: "
                    + String.join(" ", denied));
        }
        return List.copyOf(requested);
    }

    public long ttlSeconds() {
        return ttlSeconds;
    }

    public long clockSkewSeconds() {
        return clockSkewSeconds;
    }

    private String requireNonBlank(String value, String envName) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(envName + " is required for identity-token-converter-service");
        }
        return value.trim();
    }

    private String validateSecret(String value, String envName) {
        String secret = requireNonBlank(value, envName);
        if (secret.getBytes(StandardCharsets.UTF_8).length < MIN_SECRET_BYTES) {
            throw new IllegalStateException(envName + " must be at least " + MIN_SECRET_BYTES + " bytes");
        }
        return secret;
    }

    private String trimToDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private Set<String> parseAudiences(String raw, String fallback) {
        Set<String> audiences = new LinkedHashSet<>();
        if (raw != null && !raw.isBlank()) {
            Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(audiences::add);
        }
        if (audiences.isEmpty()) {
            audiences.add(fallback);
        }
        return Set.copyOf(audiences);
    }

    private Map<String, String> parseClientSecrets(String raw) {
        Map<String, String> secrets = new LinkedHashMap<>();
        if (raw == null || raw.isBlank()) {
            return Map.of();
        }
        Arrays.stream(raw.split(";"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .forEach(entry -> {
                    int separator = entry.indexOf('=');
                    if (separator <= 0 || separator == entry.length() - 1) {
                        throw new IllegalStateException("Invalid COURSEFLOW_STS_CLIENT_SECRETS entry: " + entry);
                    }
                    String clientId = entry.substring(0, separator).trim();
                    String secret = entry.substring(separator + 1).trim();
                    validateSecret(secret, "COURSEFLOW_STS_CLIENT_SECRETS[" + clientId + "]");
                    secrets.put(clientId, secret);
                });
        return Map.copyOf(secrets);
    }

    private Map<String, Set<String>> parseClientScopes(String raw) {
        Map<String, Set<String>> clientScopes = new LinkedHashMap<>();
        if (raw == null || raw.isBlank()) {
            return Map.of();
        }
        Arrays.stream(raw.split(";"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .forEach(entry -> {
                    int separator = entry.indexOf('=');
                    if (separator <= 0 || separator == entry.length() - 1) {
                        throw new IllegalStateException("Invalid COURSEFLOW_STS_CLIENT_SCOPES entry: " + entry);
                    }
                    String clientId = entry.substring(0, separator).trim();
                    Set<String> scopes = parseScopes(entry.substring(separator + 1));
                    if (scopes.isEmpty()) {
                        throw new IllegalStateException("COURSEFLOW_STS_CLIENT_SCOPES[" + clientId
                                + "] must not be empty");
                    }
                    clientScopes.put(clientId, Set.copyOf(scopes));
                });
        return Map.copyOf(clientScopes);
    }

    private void validateOidcStsPolicy() {
        if (externalTokenMode != ExternalTokenMode.OIDC) {
            return;
        }
        if (serviceClientSecrets.isEmpty()) {
            throw new IllegalStateException(
                    "COURSEFLOW_STS_CLIENT_SECRETS is required when EXTERNAL_TOKEN_MODE=oidc");
        }
        if (serviceClientScopes.isEmpty()) {
            throw new IllegalStateException(
                    "COURSEFLOW_STS_CLIENT_SCOPES is required when EXTERNAL_TOKEN_MODE=oidc");
        }
        if (allowedServiceClients.contains("*")) {
            throw new IllegalStateException(
                    "COURSEFLOW_STS_ALLOWED_CLIENTS must not contain wildcard '*' when EXTERNAL_TOKEN_MODE=oidc");
        }
        if (allowedServiceScopes.contains("*")) {
            throw new IllegalStateException(
                    "COURSEFLOW_STS_ALLOWED_SERVICE_SCOPES must not contain wildcard '*' when EXTERNAL_TOKEN_MODE=oidc");
        }
        Set<String> missingScopes = new LinkedHashSet<>(serviceClientSecrets.keySet());
        missingScopes.removeAll(serviceClientScopes.keySet());
        if (!missingScopes.isEmpty()) {
            throw new IllegalStateException("COURSEFLOW_STS_CLIENT_SCOPES missing "
                    + String.join(", ", missingScopes));
        }
        Set<String> unknownScopeClients = new LinkedHashSet<>(serviceClientScopes.keySet());
        unknownScopeClients.removeAll(serviceClientSecrets.keySet());
        if (!unknownScopeClients.isEmpty()) {
            throw new IllegalStateException("COURSEFLOW_STS_CLIENT_SCOPES configured for unknown clients "
                    + String.join(", ", unknownScopeClients));
        }
    }

    private Set<String> parseScopes(String raw) {
        Set<String> scopes = new LinkedHashSet<>();
        if (raw == null || raw.isBlank()) {
            return scopes;
        }
        Arrays.stream(raw.split("[,\\s]+"))
                .map(String::trim)
                .filter(value -> !value.isBlank())
                .forEach(scopes::add);
        return scopes;
    }

    private boolean secretEquals(String expected, String actual) {
        return expected != null && actual != null
                && MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8),
                        actual.getBytes(StandardCharsets.UTF_8));
    }

    private ExternalTokenMode parseExternalMode(String raw) {
        if ("legacy".equalsIgnoreCase(raw == null ? "" : raw.trim())) {
            return ExternalTokenMode.LEGACY;
        }
        if (raw == null || raw.isBlank()
                || "oidc".equalsIgnoreCase(raw.trim()) || "keycloak".equalsIgnoreCase(raw.trim())) {
            return ExternalTokenMode.OIDC;
        }
        throw new IllegalStateException("Unsupported external token mode: " + raw);
    }

    private InternalJwtAlgorithm parseInternalAlgorithm(String raw) {
        if (raw == null || raw.isBlank() || "HS256".equalsIgnoreCase(raw.trim())) {
            return InternalJwtAlgorithm.HS256;
        }
        if ("RS256".equalsIgnoreCase(raw.trim())) {
            return InternalJwtAlgorithm.RS256;
        }
        throw new IllegalStateException("Unsupported internal JWT algorithm: " + raw);
    }

    private String normalizePem(String raw) {
        return raw == null ? "" : raw.trim().replace("\\n", "\n");
    }

    private PrivateKey parsePrivateKey(String pem) {
        try {
            String encoded = pem.replace("-----BEGIN PRIVATE KEY-----", "")
                    .replace("-----END PRIVATE KEY-----", "")
                    .replaceAll("\\s", "");
            return KeyFactory.getInstance("RSA")
                    .generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(encoded)));
        } catch (Exception ex) {
            throw new IllegalStateException("Invalid COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY; use PKCS#8 PEM", ex);
        }
    }

    private PublicKey parsePublicKey(String pem) {
        try {
            String encoded = pem.replace("-----BEGIN PUBLIC KEY-----", "")
                    .replace("-----END PUBLIC KEY-----", "")
                    .replaceAll("\\s", "");
            return KeyFactory.getInstance("RSA")
                    .generatePublic(new X509EncodedKeySpec(Base64.getDecoder().decode(encoded)));
        } catch (Exception ex) {
            throw new IllegalStateException("Invalid COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY; use X.509 PEM", ex);
        }
    }

    private PublicKey publicKeyFromPrivateKey(PrivateKey privateKey) {
        try {
            if (!(privateKey instanceof RSAPrivateCrtKey rsa)) {
                throw new IllegalStateException("RS256 private key must expose RSA CRT parameters");
            }
            return KeyFactory.getInstance("RSA")
                    .generatePublic(new RSAPublicKeySpec(rsa.getModulus(), rsa.getPublicExponent()));
        } catch (Exception ex) {
            throw new IllegalStateException("Could not derive COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY", ex);
        }
    }

    private String defaultKeycloakJwkSetUri(String issuer) {
        if (issuer == null || issuer.isBlank()) {
            return "";
        }
        String normalized = issuer.endsWith("/") ? issuer.substring(0, issuer.length() - 1) : issuer;
        return normalized + "/protocol/openid-connect/certs";
    }

    private enum ExternalTokenMode {
        LEGACY,
        OIDC
    }

    private enum InternalJwtAlgorithm {
        HS256,
        RS256
    }
}
