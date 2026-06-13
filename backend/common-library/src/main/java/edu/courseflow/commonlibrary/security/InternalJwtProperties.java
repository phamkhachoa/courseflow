package edu.courseflow.commonlibrary.security;

import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.Set;
import javax.crypto.SecretKey;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class InternalJwtProperties {

    private static final int MIN_SECRET_BYTES = 32;

    private final Algorithm algorithm;
    private final String secret;
    private final String privateKeyPem;
    private final String publicKeyPem;
    private final VerificationMode verificationMode;
    private final String jwksUri;
    private final long jwksCacheTtlSeconds;
    private final ServiceTokenMode serviceTokenMode;
    private final String tokenConverterUri;
    private final String stsClientSecret;
    private final String issuer;
    private final Set<String> audiences;
    private final long ttlSeconds;
    private final long clockSkewSeconds;
    private final String serviceName;

    @Autowired
    public InternalJwtProperties(
            @Value("${courseflow.security.internal-jwt.algorithm:${COURSEFLOW_INTERNAL_JWT_ALGORITHM:HS256}}")
            String algorithm,
            @Value("${courseflow.security.internal-jwt.secret:${COURSEFLOW_INTERNAL_JWT_SECRET:}}") String secret,
            @Value("${courseflow.security.internal-jwt.private-key:${COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY:}}")
            String privateKeyPem,
            @Value("${courseflow.security.internal-jwt.public-key:${COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY:}}")
            String publicKeyPem,
            @Value("${courseflow.security.internal-jwt.verification-mode:${COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE:local}}")
            String verificationMode,
            @Value("${courseflow.security.internal-jwt.jwks-uri:${COURSEFLOW_INTERNAL_JWT_JWKS_URI:}}")
            String jwksUri,
            @Value("${courseflow.security.internal-jwt.jwks-cache-ttl-seconds:${COURSEFLOW_INTERNAL_JWT_JWKS_CACHE_TTL_SECONDS:300}}")
            long jwksCacheTtlSeconds,
            @Value("${courseflow.security.internal-jwt.service-token-mode:${COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE:local}}")
            String serviceTokenMode,
            @Value("${courseflow.security.internal-jwt.token-converter-uri:${TOKEN_CONVERTER_URI:}}")
            String tokenConverterUri,
            @Value("${courseflow.security.internal-jwt.sts-client-secret:${COURSEFLOW_STS_CLIENT_SECRET:}}")
            String stsClientSecret,
            @Value("${courseflow.security.internal-jwt.issuer:${COURSEFLOW_INTERNAL_JWT_ISSUER:courseflow-token-converter}}")
            String issuer,
            @Value("${courseflow.security.internal-jwt.audience:${COURSEFLOW_INTERNAL_JWT_AUDIENCE:courseflow-services}}")
            String audience,
            @Value("${courseflow.security.internal-jwt.ttl-seconds:${COURSEFLOW_INTERNAL_JWT_TTL_SECONDS:180}}")
            long ttlSeconds,
            @Value("${courseflow.security.internal-jwt.clock-skew-seconds:${COURSEFLOW_INTERNAL_JWT_CLOCK_SKEW_SECONDS:30}}")
            long clockSkewSeconds,
            @Value("${spring.application.name:courseflow-service}") String serviceName) {
        this.algorithm = parseAlgorithm(algorithm);
        this.secret = secret == null ? "" : secret.trim();
        this.privateKeyPem = normalizePem(privateKeyPem);
        this.publicKeyPem = normalizePem(publicKeyPem);
        this.verificationMode = parseVerificationMode(verificationMode);
        this.jwksUri = jwksUri == null ? "" : jwksUri.trim();
        this.jwksCacheTtlSeconds = Math.max(30, Math.min(jwksCacheTtlSeconds, 3600));
        this.serviceTokenMode = parseServiceTokenMode(serviceTokenMode);
        this.tokenConverterUri = tokenConverterUri == null ? "" : tokenConverterUri.trim();
        this.stsClientSecret = stsClientSecret == null ? "" : stsClientSecret.trim();
        this.issuer = issuer == null || issuer.isBlank() ? "courseflow-token-converter" : issuer.trim();
        this.audiences = parseAudiences(audience);
        this.ttlSeconds = Math.max(30, Math.min(ttlSeconds, 900));
        this.clockSkewSeconds = Math.max(0, Math.min(clockSkewSeconds, 120));
        this.serviceName = serviceName == null || serviceName.isBlank() ? "courseflow-service" : serviceName.trim();
    }

    public InternalJwtProperties(String secret,
            String issuer,
            String audience,
            long ttlSeconds,
            long clockSkewSeconds,
            String serviceName) {
        this("HS256", secret, "", "", "local", "", 300, "local", "", "",
                issuer, audience, ttlSeconds, clockSkewSeconds, serviceName);
    }

    public InternalJwtProperties(String algorithm,
            String secret,
            String privateKeyPem,
            String publicKeyPem,
            String issuer,
            String audience,
            long ttlSeconds,
            long clockSkewSeconds,
            String serviceName) {
        this(algorithm, secret, privateKeyPem, publicKeyPem, "local", "", 300, "local", "", "",
                issuer, audience, ttlSeconds, clockSkewSeconds, serviceName);
    }

    public boolean configured() {
        if (algorithm == Algorithm.RS256) {
            if (serviceTokenMode == ServiceTokenMode.STS) {
                boolean verifierConfigured = verificationMode == VerificationMode.JWKS
                        ? !jwksUri.isBlank()
                        : !publicKeyPem.isBlank();
                return verifierConfigured && !tokenConverterUri.isBlank() && !stsClientSecret.isBlank();
            }
            if (verificationMode == VerificationMode.JWKS) {
                return !privateKeyPem.isBlank() && !jwksUri.isBlank();
            }
            return !privateKeyPem.isBlank() && !publicKeyPem.isBlank();
        }
        return secret.getBytes(StandardCharsets.UTF_8).length >= MIN_SECRET_BYTES;
    }

    public SecretKey signingKey() {
        if (algorithm == Algorithm.RS256) {
            throw new IllegalStateException("COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY is required for RS256 signing");
        }
        if (!configured()) {
            throw new IllegalStateException("COURSEFLOW_INTERNAL_JWT_SECRET must be at least "
                    + MIN_SECRET_BYTES + " bytes");
        }
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public PrivateKey privateKey() {
        if (algorithm != Algorithm.RS256) {
            throw new IllegalStateException("Internal JWT algorithm is not RS256");
        }
        return parsePrivateKey(privateKeyPem);
    }

    public PublicKey publicKey() {
        if (algorithm != Algorithm.RS256) {
            throw new IllegalStateException("Internal JWT algorithm is not RS256");
        }
        return parsePublicKey(publicKeyPem);
    }

    public boolean jwksVerificationMode() {
        return algorithm == Algorithm.RS256 && verificationMode == VerificationMode.JWKS;
    }

    public String jwksUri() {
        return jwksUri;
    }

    public long jwksCacheTtlSeconds() {
        return jwksCacheTtlSeconds;
    }

    public boolean rs256() {
        return algorithm == Algorithm.RS256;
    }

    public boolean stsServiceTokenMode() {
        return serviceTokenMode == ServiceTokenMode.STS;
    }

    public String tokenConverterUri() {
        return tokenConverterUri;
    }

    public String stsClientSecret() {
        return stsClientSecret;
    }

    public String issuer() {
        return issuer;
    }

    public Set<String> audiences() {
        return audiences;
    }

    public String primaryAudience() {
        return audiences.iterator().next();
    }

    public long ttlSeconds() {
        return ttlSeconds;
    }

    public long clockSkewSeconds() {
        return clockSkewSeconds;
    }

    public String serviceName() {
        return serviceName;
    }

    private Set<String> parseAudiences(String raw) {
        Set<String> parsed = new LinkedHashSet<>();
        if (raw != null && !raw.isBlank()) {
            Arrays.stream(raw.split(","))
                    .map(String::trim)
                    .filter(value -> !value.isBlank())
                    .forEach(parsed::add);
        }
        if (parsed.isEmpty()) {
            parsed.add("courseflow-services");
        }
        return Set.copyOf(parsed);
    }

    private Algorithm parseAlgorithm(String raw) {
        if (raw == null || raw.isBlank() || "HS256".equalsIgnoreCase(raw.trim())) {
            return Algorithm.HS256;
        }
        if ("RS256".equalsIgnoreCase(raw.trim())) {
            return Algorithm.RS256;
        }
        throw new IllegalStateException("Unsupported COURSEFLOW_INTERNAL_JWT_ALGORITHM: " + raw);
    }

    private VerificationMode parseVerificationMode(String raw) {
        if (raw == null || raw.isBlank() || "local".equalsIgnoreCase(raw.trim())) {
            return VerificationMode.LOCAL;
        }
        if ("jwks".equalsIgnoreCase(raw.trim()) || "remote-jwks".equalsIgnoreCase(raw.trim())) {
            return VerificationMode.JWKS;
        }
        throw new IllegalStateException("Unsupported COURSEFLOW_INTERNAL_JWT_VERIFICATION_MODE: " + raw);
    }

    private ServiceTokenMode parseServiceTokenMode(String raw) {
        if (raw == null || raw.isBlank() || "local".equalsIgnoreCase(raw.trim())) {
            return ServiceTokenMode.LOCAL;
        }
        if ("sts".equalsIgnoreCase(raw.trim()) || "token-converter".equalsIgnoreCase(raw.trim())) {
            return ServiceTokenMode.STS;
        }
        throw new IllegalStateException("Unsupported COURSEFLOW_INTERNAL_SERVICE_TOKEN_MODE: " + raw);
    }

    private String normalizePem(String raw) {
        return raw == null ? "" : raw.trim().replace("\\n", "\n");
    }

    private PrivateKey parsePrivateKey(String pem) {
        try {
            String encoded = stripPem(pem, "PRIVATE KEY");
            return KeyFactory.getInstance("RSA")
                    .generatePrivate(new PKCS8EncodedKeySpec(Base64.getDecoder().decode(encoded)));
        } catch (Exception ex) {
            throw new IllegalStateException("Invalid COURSEFLOW_INTERNAL_JWT_PRIVATE_KEY; use PKCS#8 PEM", ex);
        }
    }

    private PublicKey parsePublicKey(String pem) {
        try {
            String encoded = stripPem(pem, "PUBLIC KEY");
            return KeyFactory.getInstance("RSA")
                    .generatePublic(new X509EncodedKeySpec(Base64.getDecoder().decode(encoded)));
        } catch (Exception ex) {
            throw new IllegalStateException("Invalid COURSEFLOW_INTERNAL_JWT_PUBLIC_KEY; use X.509 PEM", ex);
        }
    }

    private String stripPem(String pem, String label) {
        return pem.replace("-----BEGIN " + label + "-----", "")
                .replace("-----END " + label + "-----", "")
                .replaceAll("\\s", "");
    }

    private enum Algorithm {
        HS256,
        RS256
    }

    private enum VerificationMode {
        LOCAL,
        JWKS
    }

    private enum ServiceTokenMode {
        LOCAL,
        STS
    }
}
