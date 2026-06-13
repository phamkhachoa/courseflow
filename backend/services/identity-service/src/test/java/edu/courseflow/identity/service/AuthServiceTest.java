package edu.courseflow.identity.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.exception.UnauthorizedException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.ChangePasswordRequestDto;
import edu.courseflow.identity.dto.LoginRequestDto;
import edu.courseflow.identity.dto.RegisterRequestDto;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.SystemRoles;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserRoleAssignment;
import edu.courseflow.identity.repository.RoleRepository;
import edu.courseflow.identity.repository.UserRepository;
import edu.courseflow.identity.repository.UserRoleAssignmentRepository;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    @Mock
    private UserRepository users;
    @Mock
    private RoleRepository roles;
    @Mock
    private PasswordEncoder passwordEncoder;
    @Mock
    private JwtTokenProvider jwtTokenProvider;
    @Mock
    private RefreshTokenService refreshTokenService;
    @Mock
    private IdentityMapper mapper;
    @Mock
    private UserRoleAssignmentRepository assignments;
    @Mock
    private AccessTokenRevocationService accessTokenRevocations;
    @Mock
    private SecurityAuditService audit;
    @Mock
    private TotpService totpService;
    @Mock
    private EmailVerificationService emailVerificationService;

    private AuthService service;

    @BeforeEach
    void setUp() {
        when(passwordEncoder.encode(anyString())).thenReturn("dummy-hash");
        service = new AuthService(
                users,
                roles,
                passwordEncoder,
                jwtTokenProvider,
                refreshTokenService,
                mapper,
                assignments,
                accessTokenRevocations,
                audit,
                new PasswordPolicy(),
                totpService,
                emailVerificationService,
                false,
                false);
    }

    @Test
    void missingUserStillRunsDummyPasswordCheck() {
        when(users.findByEmailIgnoreCase("missing@example.com")).thenReturn(Optional.empty());
        when(passwordEncoder.matches("bad", "dummy-hash")).thenReturn(false);

        assertThatThrownBy(() -> service.login(new LoginRequestDto("missing@example.com", "bad", null)))
                .isInstanceOf(UnauthorizedException.class);

        verify(passwordEncoder).matches("bad", "dummy-hash");
        verify(audit).record(eq("LOGIN_FAILED"), eq(null), eq("missing@example.com"), eq(null), eq(false),
                eq("INVALID_CREDENTIALS"));
    }

    @Test
    void failedLoginsLockAccountAndKeepGenericResponse() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        when(users.findByEmailIgnoreCase("student@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("wrong", "stored-hash")).thenReturn(false);

        for (int i = 0; i < 10; i++) {
            assertThatThrownBy(() -> service.login(new LoginRequestDto("student@example.com", "wrong", null)))
                    .isInstanceOf(UnauthorizedException.class)
                    .hasMessageContaining("INVALID_CREDENTIALS");
        }

        assertThat(user.getFailedLoginCount()).isEqualTo(10);
        assertThat(user.getLockedUntil()).isNotNull();
        verify(jwtTokenProvider, never()).generateAccessToken(any());
    }

    @Test
    void mustChangePasswordBlocksTokenIssuance() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        user.requirePasswordChange();
        when(users.findByEmailIgnoreCase("student@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("correct", "stored-hash")).thenReturn(true);

        assertThatThrownBy(() -> service.login(new LoginRequestDto("student@example.com", "correct", null)))
                .isInstanceOf(UnauthorizedException.class)
                .hasMessageContaining("PASSWORD_CHANGE_REQUIRED");

        verify(jwtTokenProvider, never()).generateAccessToken(any());
    }

    @Test
    void changePasswordRevokesRefreshAndAccessTokens() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        when(users.findById(5L)).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("OldStrong1!", "stored-hash")).thenReturn(true);
        when(passwordEncoder.encode("NewStrong1!Pwd")).thenReturn("new-hash");

        service.changePassword(new CurrentUser(5L, "student@example.com", "STUDENT"), new ChangePasswordRequestDto(
                "student@example.com", "OldStrong1!", "NewStrong1!Pwd"));

        assertThat(user.getPasswordHash()).isEqualTo("new-hash");
        assertThat(user.isMustChangePassword()).isFalse();
        verify(refreshTokenService).revokeAll(5L, "password-changed");
        verify(accessTokenRevocations).revokeAllForUser(5L);
        verify(audit).record(eq("PASSWORD_CHANGED"), eq(5L), eq("student@example.com"), eq("self"), eq(true),
                eq(null));
    }

    @Test
    void refreshRejectsUnverifiedEmailWhenVerificationIsRequired() {
        AuthService strictService = new AuthService(
                users,
                roles,
                passwordEncoder,
                jwtTokenProvider,
                refreshTokenService,
                mapper,
                assignments,
                accessTokenRevocations,
                audit,
                new PasswordPolicy(),
                totpService,
                emailVerificationService,
                false,
                true);
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        when(refreshTokenService.rotate("refresh-token")).thenReturn(5L);
        when(users.findById(5L)).thenReturn(Optional.of(user));

        assertThatThrownBy(() -> strictService.refresh("refresh-token"))
                .isInstanceOf(UnauthorizedException.class)
                .hasMessageContaining("INVALID_CREDENTIALS");

        verify(audit).record(eq("REFRESH_FAILED"), eq(5L), eq("student@example.com"), eq(null), eq(false),
                eq("EMAIL_NOT_VERIFIED"));
        verify(jwtTokenProvider, never()).generateAccessToken(any());
    }

    @Test
    void startMfaEnrollmentStagesSecretWithoutEnablingMfa() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        when(users.findById(5L)).thenReturn(Optional.of(user));
        when(totpService.generateSecret()).thenReturn("JBSWY3DPEHPK3PXP");
        when(totpService.provisioningUri("CourseFlow", "student@example.com", "JBSWY3DPEHPK3PXP"))
                .thenReturn("otpauth://totp/CourseFlow:student@example.com?secret=JBSWY3DPEHPK3PXP");

        var enrollment = service.startMfaEnrollment(new CurrentUser(5L, "student@example.com", "STUDENT"));

        assertThat(enrollment.secret()).isEqualTo("JBSWY3DPEHPK3PXP");
        assertThat(enrollment.otpAuthUri()).startsWith("otpauth://totp/");
        assertThat(user.getMfaSecret()).isEqualTo("JBSWY3DPEHPK3PXP");
        assertThat(user.isMfaEnabled()).isFalse();
        verify(audit).record(eq("MFA_ENROLLMENT_STARTED"), eq(5L), eq("student@example.com"), eq("self"), eq(true),
                eq(null));
    }

    @Test
    void startMfaEnrollmentRejectsAlreadyEnabledMfa() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        user.enableMfa("JBSWY3DPEHPK3PXP");
        when(users.findById(5L)).thenReturn(Optional.of(user));

        assertThatThrownBy(() -> service.startMfaEnrollment(new CurrentUser(5L, "student@example.com", "STUDENT")))
                .isInstanceOf(edu.courseflow.commonlibrary.exception.BadRequestException.class)
                .hasMessageContaining("MFA_ALREADY_ENABLED");

        verify(totpService, never()).generateSecret();
    }

    @Test
    void confirmMfaEnablesMfaAndRevokesSessions() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        user.stageMfaSecret("JBSWY3DPEHPK3PXP");
        when(users.findById(5L)).thenReturn(Optional.of(user));
        when(totpService.verify("JBSWY3DPEHPK3PXP", "123456")).thenReturn(true);

        service.confirmMfa(new CurrentUser(5L, "student@example.com", "STUDENT"), "123456");

        assertThat(user.isMfaEnabled()).isTrue();
        assertThat(user.getMfaSecret()).isEqualTo("JBSWY3DPEHPK3PXP");
        verify(refreshTokenService).revokeAll(5L, "mfa-enabled");
        verify(accessTokenRevocations).revokeAllForUser(5L);
        verify(audit).record(eq("MFA_ENABLED"), eq(5L), eq("student@example.com"), eq("self"), eq(true), eq(null));
    }

    @Test
    void disableMfaRequiresCurrentCodeAndRevokesSessions() {
        User user = new User("student@example.com", "stored-hash", "Student");
        ReflectionTestUtils.setField(user, "id", 5L);
        user.enableMfa("JBSWY3DPEHPK3PXP");
        when(users.findById(5L)).thenReturn(Optional.of(user));
        when(totpService.verify("JBSWY3DPEHPK3PXP", "123456")).thenReturn(true);

        service.disableMfa(new CurrentUser(5L, "student@example.com", "STUDENT"), "123456");

        assertThat(user.isMfaEnabled()).isFalse();
        assertThat(user.getMfaSecret()).isNull();
        verify(refreshTokenService).revokeAll(5L, "mfa-disabled");
        verify(accessTokenRevocations).revokeAllForUser(5L);
        verify(audit).record(eq("MFA_DISABLED"), eq(5L), eq("student@example.com"), eq("self"), eq(true), eq(null));
    }

    @Test
    void registerCreatesPendingStudentAndRequestsEmailVerification() {
        Role studentRole = new Role(UUID.randomUUID(), SystemRoles.STUDENT, "Student", null, true, false, 10, null,
                "seed");
        Instant expiresAt = Instant.parse("2026-06-14T03:00:00Z");
        UserDto userDto = new UserDto(9L, "new@example.com", "New Learner", "PENDING_VERIFICATION", false, false);
        when(users.existsByEmailIgnoreCase("new@example.com")).thenReturn(false);
        when(roles.findByCode(SystemRoles.STUDENT)).thenReturn(Optional.of(studentRole));
        when(passwordEncoder.encode("StrongPass1!")).thenReturn("new-hash");
        when(users.save(any(User.class))).thenAnswer(invocation -> {
            User saved = invocation.getArgument(0);
            ReflectionTestUtils.setField(saved, "id", 9L);
            return saved;
        });
        when(emailVerificationService.issueVerification(any(User.class), eq("self-register")))
                .thenReturn(new EmailVerificationService.EmailVerificationIssue(expiresAt));
        when(mapper.toDto(any(User.class))).thenReturn(userDto);

        var response = service.register(new RegisterRequestDto("NEW@example.com", "StrongPass1!", " New Learner "));

        assertThat(response.emailVerificationRequired()).isTrue();
        assertThat(response.verificationExpiresAt()).isEqualTo(expiresAt);
        assertThat(response.user()).isEqualTo(userDto);
        verify(assignments).save(any(UserRoleAssignment.class));
        verify(emailVerificationService).issueVerification(any(User.class), eq("self-register"));
        verify(jwtTokenProvider, never()).generateAccessToken(any());
        verify(audit).record(eq("USER_REGISTERED"), eq(9L), eq("new@example.com"), eq("self-register"), eq(true),
                eq("role=STUDENT"));
    }
}
