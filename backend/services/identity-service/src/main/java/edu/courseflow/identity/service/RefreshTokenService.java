package edu.courseflow.identity.service;

import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import edu.courseflow.identity.model.RefreshToken;
import edu.courseflow.identity.repository.RefreshTokenRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Base64;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Owns the lifecycle of opaque refresh tokens: issue, rotate, revoke.
 * Only the SHA-256 hash is persisted; the raw value is returned to the client
 * once.
 *
 * <p>
 * Reuse detection: {@link #rotate(String)} on a token that is already revoked
 * or expired
 * revokes every live refresh token of that user as a precaution — the
 * assumption is that
 * the token was stolen and the legitimate client must re-authenticate.
 */
@Service
public class RefreshTokenService {

    private final RefreshTokenRepository refreshTokens;
    private final AccessTokenRevocationService accessTokenRevocations;
    private final SecurityAuditService audit;
    private final long refreshTtlSeconds;
    private final SecureRandom random = new SecureRandom();

    public RefreshTokenService(
            RefreshTokenRepository refreshTokens,
            AccessTokenRevocationService accessTokenRevocations,
            SecurityAuditService audit,
            @Value("${courseflow.security.jwt.refresh-token-ttl-seconds}") long refreshTtlSeconds) {
        this.refreshTokens = refreshTokens;
        this.accessTokenRevocations = accessTokenRevocations;
        this.audit = audit;
        this.refreshTtlSeconds = refreshTtlSeconds;
    }

    @Transactional
    public String issue(Long userId) {
        String raw = generateRawToken();
        RefreshToken token = new RefreshToken(userId, hash(raw), Instant.now().plusSeconds(refreshTtlSeconds));
        refreshTokens.save(token);
        return raw;
    }

    /**
     * Validates the presented token, revokes it (rotation), and returns the owning
     * user id.
     */
    @Transactional
    public Long rotate(String rawToken) {
        RefreshToken stored = refreshTokens.findByTokenHash(hash(rawToken))
                .orElseThrow(() -> new UnauthorizedException("REFRESH_TOKEN_INVALID"));
        if (!stored.isUsable()) {
            // Reuse / expired-token reuse: blow away the whole family so a stolen token
            // cannot stay alive.
            refreshTokens.revokeAllForUser(stored.getUserId(), Instant.now(), "reuse-detected");
            accessTokenRevocations.revokeAllForUser(stored.getUserId());
            audit.record("REFRESH_REUSE_DETECTED", stored.getUserId(), null, null, false, "reuse-detected");
            throw new UnauthorizedException("REFRESH_TOKEN_INVALID");
        }
        stored.revoke("rotated");
        return stored.getUserId();
    }

    @Transactional
    public int revokeAll(Long userId, String reason) {
        return refreshTokens.revokeAllForUser(userId, Instant.now(), reason);
    }

    @Transactional
    public int purgeExpired() {
        return refreshTokens.deleteExpired(Instant.now());
    }

    private String generateRawToken() {
        byte[] bytes = new byte[48];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String hash(String raw) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] out = digest.digest(raw.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(out);
        } catch (Exception ex) {
            throw new IllegalStateException("SHA-256 unavailable", ex);
        }
    }
}
