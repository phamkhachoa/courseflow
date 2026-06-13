package edu.courseflow.identity.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.events.common.EventMetadata;
import edu.courseflow.events.identity.UserEmailVerificationRequestedEvent;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.model.EmailVerificationToken;
import edu.courseflow.identity.model.OutboxEvent;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserStatus;
import edu.courseflow.identity.repository.EmailVerificationTokenRepository;
import edu.courseflow.identity.repository.OutboxEventRepository;
import edu.courseflow.identity.repository.UserRepository;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class EmailVerificationService {

    private static final String EVENT_TYPE = "user.email_verification_requested";
    private static final int TOKEN_BYTES = 32;

    private final UserRepository users;
    private final EmailVerificationTokenRepository tokens;
    private final OutboxEventRepository outboxEvents;
    private final IdentityMapper mapper;
    private final SecurityAuditService audit;
    private final RefreshTokenService refreshTokenService;
    private final AccessTokenRevocationService accessTokenRevocations;
    private final ObjectMapper objectMapper;
    private final SecureRandom secureRandom = new SecureRandom();
    private final Duration tokenTtl;
    private final String verificationUrl;

    public EmailVerificationService(
            UserRepository users,
            EmailVerificationTokenRepository tokens,
            OutboxEventRepository outboxEvents,
            IdentityMapper mapper,
            SecurityAuditService audit,
            RefreshTokenService refreshTokenService,
            AccessTokenRevocationService accessTokenRevocations,
            ObjectMapper objectMapper,
            @Value("${courseflow.security.email-verification-token-ttl-seconds:86400}") long tokenTtlSeconds,
            @Value("${courseflow.security.email-verification-url:http://localhost:3000/verify-email}")
            String verificationUrl) {
        this.users = users;
        this.tokens = tokens;
        this.outboxEvents = outboxEvents;
        this.mapper = mapper;
        this.audit = audit;
        this.refreshTokenService = refreshTokenService;
        this.accessTokenRevocations = accessTokenRevocations;
        this.objectMapper = objectMapper;
        this.tokenTtl = Duration.ofSeconds(Math.max(300, tokenTtlSeconds));
        this.verificationUrl = verificationUrl == null || verificationUrl.isBlank()
                ? "http://localhost:3000/verify-email"
                : verificationUrl.trim();
    }

    public EmailVerificationIssue issueVerification(User user, String actorId) {
        if (user.getId() == null) {
            throw new IllegalStateException("Cannot issue email verification before user id is assigned");
        }
        Instant now = Instant.now();
        tokens.consumeOutstandingForUser(user.getId(), now);

        String rawToken = generateToken();
        Instant expiresAt = now.plus(tokenTtl);
        tokens.save(new EmailVerificationToken(user.getId(), hashToken(rawToken), expiresAt));

        String eventId = UUID.randomUUID().toString();
        String url = verificationLink(rawToken);
        var event = new UserEmailVerificationRequestedEvent(
                eventId,
                String.valueOf(user.getId()),
                user.getEmail(),
                user.getFullName(),
                url,
                expiresAt,
                now,
                new EventMetadata(null, null, actorId, Map.of()));
        outboxEvents.save(new OutboxEvent(event.aggregateId(), event.aggregateType(), event.eventType(), toJson(event)));
        audit.record("EMAIL_VERIFICATION_REQUESTED", user.getId(), user.getEmail(), actorId, true,
                "expiresAt=" + expiresAt);
        return new EmailVerificationIssue(expiresAt);
    }

    public UserDto verify(String rawToken) {
        if (rawToken == null || rawToken.isBlank()) {
            throw invalidToken();
        }
        Instant now = Instant.now();
        EmailVerificationToken token = tokens.findByTokenHash(hashToken(rawToken.trim()))
                .orElseThrow(this::invalidToken);
        if (!token.isUsable(now)) {
            throw invalidToken();
        }
        User user = users.findById(token.getUserId()).orElseThrow(this::invalidToken);
        token.consume(now);
        user.markEmailVerified();
        refreshTokenService.revokeAll(user.getId(), "email-verified");
        accessTokenRevocations.revokeAllForUser(user.getId());
        audit.record("EMAIL_VERIFIED", user.getId(), user.getEmail(), "self", true, null);
        return mapper.toDto(user);
    }

    public void resend(String rawEmail) {
        String email = rawEmail == null ? "" : rawEmail.trim().toLowerCase();
        if (email.isBlank()) {
            return;
        }
        users.findByEmailIgnoreCase(email).ifPresent(user -> {
            if (user.isEmailVerified() || user.getStatus() != UserStatus.PENDING_VERIFICATION) {
                audit.record("EMAIL_VERIFICATION_RESEND_IGNORED", user.getId(), user.getEmail(),
                        "self", true, "alreadyVerifiedOrInactive");
                return;
            }
            issueVerification(user, "email-verification-resend");
        });
    }

    private String generateToken() {
        byte[] random = new byte[TOKEN_BYTES];
        secureRandom.nextBytes(random);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(random);
    }

    private String verificationLink(String rawToken) {
        String separator = verificationUrl.contains("?") ? "&" : "?";
        return verificationUrl + separator + "token=" + URLEncoder.encode(rawToken, StandardCharsets.UTF_8);
    }

    private String toJson(UserEmailVerificationRequestedEvent event) {
        try {
            return objectMapper.writeValueAsString(event);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize email verification event", ex);
        }
    }

    private BadRequestException invalidToken() {
        return new BadRequestException("EMAIL_VERIFICATION_TOKEN_INVALID");
    }

    static String hashToken(String rawToken) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(rawToken.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is not available", ex);
        }
    }

    public record EmailVerificationIssue(Instant expiresAt) {
    }
}
