package edu.courseflow.identity.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.DuplicatedException;
import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.ChangePasswordRequestDto;
import edu.courseflow.identity.dto.EmailVerificationDtos.RegistrationResponseDto;
import edu.courseflow.identity.dto.LoginRequestDto;
import edu.courseflow.identity.dto.MfaDtos.MfaEnrollmentDto;
import edu.courseflow.identity.dto.RegisterRequestDto;
import edu.courseflow.identity.dto.TokenResponseDto;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.SystemRoles;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserRoleAssignment;
import edu.courseflow.identity.model.UserStatus;
import edu.courseflow.identity.repository.RoleRepository;
import edu.courseflow.identity.repository.UserRepository;
import edu.courseflow.identity.repository.UserRoleAssignmentRepository;
import java.time.Duration;
import java.time.Instant;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {

    /**
     * Soft account-lockout threshold; mitigates online brute force without a
     * separate rate-limiter.
     */
    private static final int LOGIN_LOCKOUT_THRESHOLD = 10;
    private static final Duration LOGIN_LOCKOUT_DURATION = Duration.ofMinutes(15);
    private static final String INVALID_CREDENTIALS = "INVALID_CREDENTIALS";

    private final UserRepository users;
    private final RoleRepository roles;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final RefreshTokenService refreshTokenService;
    private final IdentityMapper mapper;
    private final UserRoleAssignmentRepository assignments;
    private final AccessTokenRevocationService accessTokenRevocations;
    private final SecurityAuditService audit;
    private final PasswordPolicy passwordPolicy;
    private final TotpService totpService;
    private final EmailVerificationService emailVerificationService;
    private final boolean requireMfaForOperators;
    private final boolean requireVerifiedEmail;
    private final String dummyPasswordHash;

    public AuthService(UserRepository users,
            RoleRepository roles,
            PasswordEncoder passwordEncoder,
            JwtTokenProvider jwtTokenProvider,
            RefreshTokenService refreshTokenService,
            IdentityMapper mapper,
            UserRoleAssignmentRepository assignments,
            AccessTokenRevocationService accessTokenRevocations,
            SecurityAuditService audit,
            PasswordPolicy passwordPolicy,
            TotpService totpService,
            EmailVerificationService emailVerificationService,
            @Value("${courseflow.security.require-mfa-for-operators:false}") boolean requireMfaForOperators,
            @Value("${courseflow.security.require-verified-email:false}") boolean requireVerifiedEmail) {
        this.users = users;
        this.roles = roles;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
        this.refreshTokenService = refreshTokenService;
        this.mapper = mapper;
        this.assignments = assignments;
        this.accessTokenRevocations = accessTokenRevocations;
        this.audit = audit;
        this.passwordPolicy = passwordPolicy;
        this.totpService = totpService;
        this.emailVerificationService = emailVerificationService;
        this.requireMfaForOperators = requireMfaForOperators;
        this.requireVerifiedEmail = requireVerifiedEmail;
        this.dummyPasswordHash = passwordEncoder.encode("courseflow-dummy-password-Do-Not-Use-1!");
    }

    @Transactional
    public RegistrationResponseDto register(RegisterRequestDto request) {
        String email = request.email().trim().toLowerCase();
        if (users.existsByEmailIgnoreCase(email)) {
            audit.record("REGISTER_FAILED", null, email, null, false, "EMAIL_ALREADY_EXISTS");
            throw new DuplicatedException("EMAIL_ALREADY_EXISTS", email);
        }
        passwordPolicy.validate(request.password());
        Role studentRole = roles.findByCode(SystemRoles.STUDENT)
                .orElseThrow(() -> new BadRequestException("UNKNOWN_ROLE: " + SystemRoles.STUDENT));

        User user = new User(email, passwordEncoder.encode(request.password()), request.fullName().trim());
        user.setStatus(UserStatus.PENDING_VERIFICATION);
        users.save(user);

        assignments.save(new UserRoleAssignment(
                user.getId(), studentRole, "PLATFORM", null, "self-register", null));
        var verification = emailVerificationService.issueVerification(user, "self-register");
        audit.record("USER_REGISTERED", user.getId(), user.getEmail(), "self-register", true,
                "role=" + SystemRoles.STUDENT);
        return new RegistrationResponseDto(mapper.toDto(user), true, verification.expiresAt());
    }

    @Transactional(noRollbackFor = UnauthorizedException.class)
    public TokenResponseDto login(LoginRequestDto request) {
        User user = users.findByEmailIgnoreCase(request.email()).orElse(null);
        if (user == null) {
            passwordEncoder.matches(request.password(), dummyPasswordHash);
            audit.record("LOGIN_FAILED", null, request.email(), null, false, INVALID_CREDENTIALS);
            throw invalidCredentials();
        }

        if (user.isLockedOut()) {
            passwordEncoder.matches(request.password(), user.getPasswordHash());
            audit.record("LOGIN_LOCKED", user.getId(), user.getEmail(), null, false, "LOCKED");
            throw invalidCredentials();
        }
        if (user.getStatus() != edu.courseflow.identity.model.UserStatus.ACTIVE) {
            passwordEncoder.matches(request.password(), user.getPasswordHash());
            audit.record("LOGIN_FAILED", user.getId(), user.getEmail(), null, false, "INACTIVE");
            throw invalidCredentials();
        }
        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            user.recordFailedLogin(LOGIN_LOCKOUT_THRESHOLD, LOGIN_LOCKOUT_DURATION);
            audit.record("LOGIN_FAILED", user.getId(), user.getEmail(), null, false, INVALID_CREDENTIALS);
            if (user.isLockedOut()) {
                audit.record("ACCOUNT_LOCKED", user.getId(), user.getEmail(), null, true, "LOCKOUT_THRESHOLD");
            }
            throw invalidCredentials();
        }
        if (requireVerifiedEmail && !user.isEmailVerified()) {
            audit.record("LOGIN_FAILED", user.getId(), user.getEmail(), null, false, "EMAIL_NOT_VERIFIED");
            throw invalidCredentials();
        }
        if (user.isMustChangePassword()) {
            audit.record("LOGIN_FAILED", user.getId(), user.getEmail(), null, false, "PASSWORD_CHANGE_REQUIRED");
            throw new UnauthorizedException("PASSWORD_CHANGE_REQUIRED");
        }
        if (!mfaSatisfied(user, request.mfaCode())) {
            audit.record("LOGIN_FAILED", user.getId(), user.getEmail(), null, false, "MFA_REQUIRED");
            throw new UnauthorizedException("MFA_REQUIRED");
        }
        user.recordSuccessfulLogin();
        audit.record("LOGIN_SUCCESS", user.getId(), user.getEmail(), null, true, null);
        return issueTokens(user);
    }

    @Transactional
    public TokenResponseDto refresh(String rawRefreshToken) {
        Long userId = refreshTokenService.rotate(rawRefreshToken);
        User user = users.findById(userId)
                .filter(User::isActive)
                .orElseThrow(() -> new UnauthorizedException(INVALID_CREDENTIALS));
        if (requireVerifiedEmail && !user.isEmailVerified()) {
            audit.record("REFRESH_FAILED", user.getId(), user.getEmail(), null, false, "EMAIL_NOT_VERIFIED");
            throw new UnauthorizedException(INVALID_CREDENTIALS);
        }
        if (user.isMustChangePassword()) {
            throw new UnauthorizedException("PASSWORD_CHANGE_REQUIRED");
        }
        audit.record("REFRESH_SUCCESS", user.getId(), user.getEmail(), null, true, null);
        return issueTokens(user);
    }

    @Transactional
    public void logout(Long userId, String accessTokenJti, Instant accessTokenExpiresAt) {
        refreshTokenService.revokeAll(userId, "logout");
        accessTokenRevocations.revokeToken(accessTokenJti, userId, accessTokenExpiresAt, "logout");
        accessTokenRevocations.revokeAllForUser(userId);
        audit.record("LOGOUT", userId, null, userId == null ? null : "user:" + userId, true, null);
    }

    @Transactional(noRollbackFor = UnauthorizedException.class)
    public void changePassword(CurrentUser currentUser, ChangePasswordRequestDto request) {
        if (currentUser == null || currentUser.id() == null) {
            throw new UnauthorizedException(INVALID_CREDENTIALS);
        }
        User user = users.findById(currentUser.id()).orElseThrow(this::invalidCredentials);
        if (!passwordEncoder.matches(request.currentPassword(), user.getPasswordHash())) {
            user.recordFailedLogin(LOGIN_LOCKOUT_THRESHOLD, LOGIN_LOCKOUT_DURATION);
            audit.record("PASSWORD_CHANGE_FAILED", user.getId(), user.getEmail(), null, false, INVALID_CREDENTIALS);
            throw invalidCredentials();
        }
        passwordPolicy.validate(request.newPassword());
        user.updatePassword(passwordEncoder.encode(request.newPassword()));
        refreshTokenService.revokeAll(user.getId(), "password-changed");
        accessTokenRevocations.revokeAllForUser(user.getId());
        audit.record("PASSWORD_CHANGED", user.getId(), user.getEmail(), "self", true, null);
    }

    @Transactional
    public MfaEnrollmentDto startMfaEnrollment(CurrentUser currentUser) {
        User user = requireCurrentUser(currentUser);
        if (user.isMfaEnabled()) {
            throw new BadRequestException("MFA_ALREADY_ENABLED");
        }
        String secret = totpService.generateSecret();
        user.stageMfaSecret(secret);
        audit.record("MFA_ENROLLMENT_STARTED", user.getId(), user.getEmail(), "self", true, null);
        return new MfaEnrollmentDto(secret, totpService.provisioningUri("CourseFlow", user.getEmail(), secret));
    }

    @Transactional
    public void confirmMfa(CurrentUser currentUser, String code) {
        User user = requireCurrentUser(currentUser);
        if (user.getMfaSecret() == null || user.getMfaSecret().isBlank()) {
            throw new BadRequestException("MFA_ENROLLMENT_NOT_STARTED");
        }
        if (!totpService.verify(user.getMfaSecret(), code)) {
            audit.record("MFA_CONFIRM_FAILED", user.getId(), user.getEmail(), "self", false, "INVALID_CODE");
            throw new UnauthorizedException("INVALID_MFA_CODE");
        }
        user.enableMfa(user.getMfaSecret());
        refreshTokenService.revokeAll(user.getId(), "mfa-enabled");
        accessTokenRevocations.revokeAllForUser(user.getId());
        audit.record("MFA_ENABLED", user.getId(), user.getEmail(), "self", true, null);
    }

    @Transactional
    public void disableMfa(CurrentUser currentUser, String code) {
        User user = requireCurrentUser(currentUser);
        if (!user.isMfaEnabled() || user.getMfaSecret() == null || user.getMfaSecret().isBlank()) {
            throw new BadRequestException("MFA_NOT_ENABLED");
        }
        if (!totpService.verify(user.getMfaSecret(), code)) {
            audit.record("MFA_DISABLE_FAILED", user.getId(), user.getEmail(), "self", false, "INVALID_CODE");
            throw new UnauthorizedException("INVALID_MFA_CODE");
        }
        user.disableMfa();
        refreshTokenService.revokeAll(user.getId(), "mfa-disabled");
        accessTokenRevocations.revokeAllForUser(user.getId());
        audit.record("MFA_DISABLED", user.getId(), user.getEmail(), "self", true, null);
    }

    @Transactional
    public UserDto verifyEmail(String token) {
        return emailVerificationService.verify(token);
    }

    @Transactional
    public void resendEmailVerification(String email) {
        emailVerificationService.resend(email);
    }

    private TokenResponseDto issueTokens(User user) {
        String accessToken = jwtTokenProvider.generateAccessToken(user);
        String refreshToken = refreshTokenService.issue(user.getId());
        return new TokenResponseDto(
                accessToken,
                refreshToken,
                "Bearer",
                jwtTokenProvider.getAccessTtlSeconds(),
                mapper.toDto(user));
    }

    private boolean mfaSatisfied(User user, String code) {
        boolean operator = assignments.findActiveByUserId(user.getId(), Instant.now()).stream()
                .map(UserRoleAssignment::getRole)
                .anyMatch(role -> role.isOperator() || "ADMIN".equals(role.getCode()));
        if (!user.isMfaEnabled()) {
            return !operator || !requireMfaForOperators;
        }
        return totpService.verify(user.getMfaSecret(), code);
    }

    private User requireCurrentUser(CurrentUser currentUser) {
        if (currentUser == null || currentUser.id() == null) {
            throw new UnauthorizedException(INVALID_CREDENTIALS);
        }
        return users.findById(currentUser.id())
                .filter(User::isActive)
                .orElseThrow(this::invalidCredentials);
    }

    private UnauthorizedException invalidCredentials() {
        return new UnauthorizedException(INVALID_CREDENTIALS);
    }
}
