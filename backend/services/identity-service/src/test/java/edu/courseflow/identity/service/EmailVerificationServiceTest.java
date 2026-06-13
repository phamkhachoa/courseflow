package edu.courseflow.identity.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.model.EmailVerificationToken;
import edu.courseflow.identity.model.OutboxEvent;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserStatus;
import edu.courseflow.identity.repository.EmailVerificationTokenRepository;
import edu.courseflow.identity.repository.OutboxEventRepository;
import edu.courseflow.identity.repository.UserRepository;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class EmailVerificationServiceTest {

    @Mock
    private UserRepository users;
    @Mock
    private EmailVerificationTokenRepository tokens;
    @Mock
    private OutboxEventRepository outboxEvents;
    @Mock
    private IdentityMapper mapper;
    @Mock
    private SecurityAuditService audit;
    @Mock
    private RefreshTokenService refreshTokenService;
    @Mock
    private AccessTokenRevocationService accessTokenRevocations;

    private ObjectMapper objectMapper;
    private EmailVerificationService service;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper().findAndRegisterModules();
        service = new EmailVerificationService(
                users,
                tokens,
                outboxEvents,
                mapper,
                audit,
                refreshTokenService,
                accessTokenRevocations,
                objectMapper,
                900,
                "https://learn.example.com/verify-email");
    }

    @Test
    void issueVerificationStoresOnlyTokenHashAndOutboxVerificationUrl() throws Exception {
        User user = pendingUser(9L);
        when(tokens.save(any(EmailVerificationToken.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(outboxEvents.save(any(OutboxEvent.class))).thenAnswer(invocation -> invocation.getArgument(0));

        var issue = service.issueVerification(user, "self-register");

        ArgumentCaptor<EmailVerificationToken> tokenCaptor = ArgumentCaptor.forClass(EmailVerificationToken.class);
        verify(tokens).consumeOutstandingForUser(eq(9L), any(Instant.class));
        verify(tokens).save(tokenCaptor.capture());
        EmailVerificationToken savedToken = tokenCaptor.getValue();
        assertThat(savedToken.getUserId()).isEqualTo(9L);
        assertThat(savedToken.getTokenHash()).hasSize(64);
        assertThat(savedToken.getExpiresAt()).isEqualTo(issue.expiresAt());

        ArgumentCaptor<OutboxEvent> eventCaptor = ArgumentCaptor.forClass(OutboxEvent.class);
        verify(outboxEvents).save(eventCaptor.capture());
        OutboxEvent event = eventCaptor.getValue();
        assertThat(event.getAggregateId()).isEqualTo("9");
        assertThat(event.getEventType()).isEqualTo("user.email_verification_requested");

        var payload = objectMapper.readTree(event.getPayload());
        assertThat(payload.path("email").asText()).isEqualTo("new@example.com");
        String verificationUrl = payload.path("verificationUrl").asText();
        assertThat(verificationUrl).startsWith("https://learn.example.com/verify-email?token=");
        String rawToken = verificationUrl.substring(verificationUrl.indexOf("token=") + "token=".length());
        assertThat(EmailVerificationService.hashToken(rawToken)).isEqualTo(savedToken.getTokenHash());
        verify(audit).record(eq("EMAIL_VERIFICATION_REQUESTED"), eq(9L), eq("new@example.com"),
                eq("self-register"), eq(true), any());
    }

    @Test
    void verifyConsumesTokenActivatesUserAndRevokesSessions() {
        String rawToken = "raw-token";
        EmailVerificationToken token = new EmailVerificationToken(
                9L, EmailVerificationService.hashToken(rawToken), Instant.now().plusSeconds(60));
        User user = pendingUser(9L);
        UserDto dto = new UserDto(9L, "new@example.com", "New Learner", "ACTIVE", true, false);
        when(tokens.findByTokenHash(EmailVerificationService.hashToken(rawToken))).thenReturn(Optional.of(token));
        when(users.findById(9L)).thenReturn(Optional.of(user));
        when(mapper.toDto(user)).thenReturn(dto);

        UserDto verified = service.verify(rawToken);

        assertThat(verified).isEqualTo(dto);
        assertThat(user.isEmailVerified()).isTrue();
        assertThat(user.getStatus()).isEqualTo(UserStatus.ACTIVE);
        assertThat(token.getConsumedAt()).isNotNull();
        verify(refreshTokenService).revokeAll(9L, "email-verified");
        verify(accessTokenRevocations).revokeAllForUser(9L);
        verify(audit).record("EMAIL_VERIFIED", 9L, "new@example.com", "self", true, null);
    }

    @Test
    void verifyRejectsExpiredTokenWithoutActivatingUser() {
        String rawToken = "raw-token";
        EmailVerificationToken token = new EmailVerificationToken(
                9L, EmailVerificationService.hashToken(rawToken), Instant.now().minusSeconds(1));
        when(tokens.findByTokenHash(EmailVerificationService.hashToken(rawToken))).thenReturn(Optional.of(token));

        assertThatThrownBy(() -> service.verify(rawToken))
                .isInstanceOf(BadRequestException.class)
                .hasMessageContaining("EMAIL_VERIFICATION_TOKEN_INVALID");

        verify(users, never()).findById(any());
        verify(refreshTokenService, never()).revokeAll(any(), any());
        verify(accessTokenRevocations, never()).revokeAllForUser(any());
    }

    private User pendingUser(Long id) {
        User user = new User("new@example.com", "hash", "New Learner");
        ReflectionTestUtils.setField(user, "id", id);
        user.setStatus(UserStatus.PENDING_VERIFICATION);
        return user;
    }
}
