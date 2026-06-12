package edu.courseflow.identity.service;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import edu.courseflow.identity.model.RefreshToken;
import edu.courseflow.identity.repository.RefreshTokenRepository;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class RefreshTokenServiceTest {

    @Mock
    private RefreshTokenRepository refreshTokens;
    @Mock
    private AccessTokenRevocationService accessTokenRevocations;
    @Mock
    private SecurityAuditService audit;

    @Test
    void reuseDetectedRevokesRefreshFamilyAndAccessTokens() {
        RefreshToken stored = new RefreshToken(5L, "stored-hash", Instant.now().plusSeconds(3600));
        stored.revoke("rotated");
        when(refreshTokens.findByTokenHash(any())).thenReturn(Optional.of(stored));
        RefreshTokenService service = new RefreshTokenService(
                refreshTokens, accessTokenRevocations, audit, 604800);

        assertThatThrownBy(() -> service.rotate("raw-refresh-token"))
                .isInstanceOf(UnauthorizedException.class);

        verify(refreshTokens).revokeAllForUser(eq(5L), any(), eq("reuse-detected"));
        verify(accessTokenRevocations).revokeAllForUser(5L);
        verify(audit).record("REFRESH_REUSE_DETECTED", 5L, null, null, false, "reuse-detected");
    }
}
