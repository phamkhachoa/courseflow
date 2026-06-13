package edu.courseflow.identity.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.DeactivateUserRequestDto;
import edu.courseflow.identity.dto.ResetPasswordRequestDto;
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
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository users;
    @Mock
    private RoleRepository roles;
    @Mock
    private UserRoleAssignmentRepository assignments;
    @Mock
    private PasswordEncoder passwordEncoder;
    @Mock
    private IdentityMapper mapper;
    @Mock
    private PasswordPolicy passwordPolicy;
    @Mock
    private RefreshTokenService refreshTokenService;
    @Mock
    private AccessTokenRevocationService accessTokenRevocations;
    @Mock
    private SecurityAuditService audit;

    private UserService service;

    @BeforeEach
    void setUp() {
        service = new UserService(
                users,
                roles,
                assignments,
                passwordEncoder,
                mapper,
                passwordPolicy,
                refreshTokenService,
                accessTokenRevocations,
                audit);
    }

    @Test
    void privacyExportIncludesProfileSecurityAndRoleGrantsAndAudits() {
        User user = user(42L, "learner@example.com", "Learner");
        Role student = role(SystemRoles.STUDENT, false);
        UserRoleAssignment assignment = new UserRoleAssignment(42L, student, "COURSE", "course-1", "seed", null);
        ReflectionTestUtils.setField(assignment, "id", 99L);

        when(users.findById(42L)).thenReturn(Optional.of(user));
        when(assignments.findByUserIdOrderById(42L)).thenReturn(List.of(assignment));
        when(mapper.toDto(user)).thenReturn(new UserDto(
                42L, "learner@example.com", "Learner", "ACTIVE", false, false));

        var export = service.exportPrivacy(42L, admin());

        assertThat(export.profile().email()).isEqualTo("learner@example.com");
        assertThat(export.accountSecurity().passwordChangedAt()).isNotNull();
        assertThat(export.roleAssignments()).hasSize(1);
        assertThat(export.roleAssignments().get(0).roleCode()).isEqualTo(SystemRoles.STUDENT);
        assertThat(export.roleAssignments().get(0).scopeId()).isEqualTo("course-1");
        assertThat(export.exportedAt()).isNotNull();
        verify(audit).record("USER_PRIVACY_EXPORTED", 42L, "learner@example.com", "user:1", true, null);
    }

    @Test
    void deactivateRevokesSessionsAndLiveRoleAssignments() {
        User user = user(42L, "learner@example.com", "Learner");
        Role student = role(SystemRoles.STUDENT, false);
        UserRoleAssignment assignment = new UserRoleAssignment(42L, student, "COURSE", "course-1", "seed", null);
        ReflectionTestUtils.setField(assignment, "id", 99L);

        when(users.findById(42L)).thenReturn(Optional.of(user));
        when(assignments.findLiveByUserId(42L)).thenReturn(List.of(assignment));
        when(mapper.toDto(any(User.class))).thenAnswer(invocation -> {
            User saved = invocation.getArgument(0);
            return new UserDto(saved.getId(), saved.getEmail(), saved.getFullName(),
                    saved.getStatus().name(), saved.isEmailVerified(), saved.isMfaEnabled());
        });

        UserDto dto = service.deactivate(
                42L,
                new DeactivateUserRequestDto("Privacy deletion request"),
                admin());

        assertThat(dto.status()).isEqualTo(UserStatus.DEACTIVATED.name());
        assertThat(user.getStatus()).isEqualTo(UserStatus.DEACTIVATED);
        assertThat(assignment.getRevokedAt()).isNotNull();
        assertThat(assignment.getRevokedBy()).isEqualTo("user:1");
        verify(refreshTokenService).revokeAll(42L, "user-deactivated");
        verify(accessTokenRevocations).revokeAllForUser(42L);
        verify(audit).record(eq("USER_DEACTIVATED"), eq(42L), eq("learner@example.com"),
                eq("user:1"), eq(true), eq("reason=Privacy deletion request"));
    }

    @Test
    void markEmailVerifiedRequiresAdmin() {
        assertThatThrownBy(() -> service.markEmailVerified(42L,
                new CurrentUser(7L, "instructor@example.com", SystemRoles.INSTRUCTOR)))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Only ADMIN may verify user email addresses");

        verifyNoInteractions(users);
    }

    @Test
    void markEmailVerifiedActivatesPendingAccountAndAudits() {
        User user = user(42L, "learner@example.com", "Learner");
        user.setStatus(UserStatus.PENDING_VERIFICATION);
        when(users.findById(42L)).thenReturn(Optional.of(user));
        when(mapper.toDto(any(User.class))).thenAnswer(invocation -> {
            User saved = invocation.getArgument(0);
            return new UserDto(saved.getId(), saved.getEmail(), saved.getFullName(),
                    saved.getStatus().name(), saved.isEmailVerified(), saved.isMfaEnabled());
        });

        UserDto dto = service.markEmailVerified(42L, admin());

        assertThat(user.isEmailVerified()).isTrue();
        assertThat(user.getStatus()).isEqualTo(UserStatus.ACTIVE);
        assertThat(dto.emailVerified()).isTrue();
        assertThat(dto.status()).isEqualTo(UserStatus.ACTIVE.name());
        verify(audit).record("EMAIL_VERIFIED", 42L, "learner@example.com", "user:1", true, null);
    }

    @Test
    void resetPasswordRequiresAdmin() {
        assertThatThrownBy(() -> service.resetPassword(
                42L,
                new ResetPasswordRequestDto("NewStrongPassword1!", true),
                new CurrentUser(7L, "instructor@example.com", SystemRoles.INSTRUCTOR)))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("Only ADMIN may reset user passwords");

        verifyNoInteractions(users, passwordPolicy, refreshTokenService, accessTokenRevocations);
    }

    @Test
    void resetPasswordRevokesSessionsAndRequiresChangeByDefault() {
        User user = user(42L, "learner@example.com", "Learner");
        when(users.findById(42L)).thenReturn(Optional.of(user));
        when(passwordEncoder.encode("NewStrongPassword1!")).thenReturn("new-hash");

        service.resetPassword(42L, new ResetPasswordRequestDto("NewStrongPassword1!", null), admin());

        assertThat(user.getPasswordHash()).isEqualTo("new-hash");
        assertThat(user.isMustChangePassword()).isTrue();
        verify(passwordPolicy).validate("NewStrongPassword1!");
        verify(refreshTokenService).revokeAll(42L, "password-reset");
        verify(accessTokenRevocations).revokeAllForUser(42L);
        verify(audit).record("PASSWORD_RESET", 42L, "learner@example.com", "user:1", true, "mustChange=true");
    }

    private CurrentUser admin() {
        return new CurrentUser(1L, "admin@example.com", SystemRoles.ADMIN);
    }

    private User user(Long id, String email, String fullName) {
        User user = new User(email, "hash", fullName);
        ReflectionTestUtils.setField(user, "id", id);
        return user;
    }

    private Role role(String code, boolean operator) {
        return new Role(UUID.randomUUID(), code, code, null, true, operator, 10, null, "seed");
    }
}
