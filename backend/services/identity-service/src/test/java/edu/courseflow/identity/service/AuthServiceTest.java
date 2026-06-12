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
        when(users.findByEmailIgnoreCase("student@example.com")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("OldStrong1!", "stored-hash")).thenReturn(true);
        when(passwordEncoder.encode("NewStrong1!Pwd")).thenReturn("new-hash");

        service.changePassword(new ChangePasswordRequestDto(
                "student@example.com", "OldStrong1!", "NewStrong1!Pwd"));

        assertThat(user.getPasswordHash()).isEqualTo("new-hash");
        assertThat(user.isMustChangePassword()).isFalse();
        verify(refreshTokenService).revokeAll(5L, "password-changed");
        verify(accessTokenRevocations).revokeAllForUser(5L);
        verify(audit).record(eq("PASSWORD_CHANGED"), eq(5L), eq("student@example.com"), eq("self"), eq(true),
                eq(null));
    }

    @Test
    void registerCreatesActiveStudentAndReturnsTokens() {
        Role studentRole = new Role(UUID.randomUUID(), SystemRoles.STUDENT, "Student", null, true, false, 10, null,
                "seed");
        UserDto userDto = new UserDto(9L, "new@example.com", "New Learner", "ACTIVE", true, false);
        when(users.existsByEmailIgnoreCase("new@example.com")).thenReturn(false);
        when(roles.findByCode(SystemRoles.STUDENT)).thenReturn(Optional.of(studentRole));
        when(passwordEncoder.encode("StrongPass1!")).thenReturn("new-hash");
        when(users.save(any(User.class))).thenAnswer(invocation -> {
            User saved = invocation.getArgument(0);
            ReflectionTestUtils.setField(saved, "id", 9L);
            return saved;
        });
        when(jwtTokenProvider.generateAccessToken(any(User.class))).thenReturn("access-token");
        when(jwtTokenProvider.getAccessTtlSeconds()).thenReturn(900L);
        when(refreshTokenService.issue(9L)).thenReturn("refresh-token");
        when(mapper.toDto(any(User.class))).thenReturn(userDto);

        var response = service.register(new RegisterRequestDto("NEW@example.com", "StrongPass1!", " New Learner "));

        assertThat(response.accessToken()).isEqualTo("access-token");
        assertThat(response.refreshToken()).isEqualTo("refresh-token");
        assertThat(response.user()).isEqualTo(userDto);
        verify(assignments).save(any(UserRoleAssignment.class));
        verify(audit).record(eq("USER_REGISTERED"), eq(9L), eq("new@example.com"), eq("self-register"), eq(true),
                eq("role=STUDENT"));
    }
}
