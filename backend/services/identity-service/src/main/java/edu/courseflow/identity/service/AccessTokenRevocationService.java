package edu.courseflow.identity.service;

import edu.courseflow.identity.model.RevokedAccessToken;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.repository.RevokedAccessTokenRepository;
import edu.courseflow.identity.repository.UserRepository;
import java.time.Instant;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AccessTokenRevocationService {

    private final RevokedAccessTokenRepository revokedTokens;
    private final UserRepository users;

    public AccessTokenRevocationService(RevokedAccessTokenRepository revokedTokens, UserRepository users) {
        this.revokedTokens = revokedTokens;
        this.users = users;
    }

    @Transactional(readOnly = true)
    public boolean isAccepted(Long userId, String jti, Instant issuedAt) {
        if (userId == null || jti == null || jti.isBlank() || issuedAt == null) {
            return false;
        }
        if (revokedTokens.existsById(jti)) {
            return false;
        }
        return users.findById(userId)
                .filter(User::isActive)
                .map(user -> user.getAccessTokensValidAfter() == null
                        || !issuedAt.isBefore(user.getAccessTokensValidAfter()))
                .orElse(false);
    }

    @Transactional
    public void revokeToken(String jti, Long userId, Instant expiresAt, String reason) {
        if (jti == null || jti.isBlank() || expiresAt == null || expiresAt.isBefore(Instant.now())) {
            return;
        }
        if (!revokedTokens.existsById(jti)) {
            revokedTokens.save(new RevokedAccessToken(jti, userId, expiresAt, reason));
        }
    }

    @Transactional
    public void revokeAllForUser(Long userId) {
        users.findById(userId).ifPresent(User::revokeAccessTokens);
    }

    @Transactional
    public int purgeExpired() {
        return revokedTokens.deleteExpired(Instant.now());
    }
}
