package edu.courseflow.usermanagement.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;

import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.usermanagement.dto.UserProfileDtos.CreateAdminUserRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.DeactivateAdminUserRequest;
import edu.courseflow.usermanagement.model.UserProfile;
import edu.courseflow.usermanagement.repository.UserProfileAuditLogRepository;
import edu.courseflow.usermanagement.repository.UserProfileRepository;
import edu.courseflow.usermanagement.service.AccessControlUserDirectoryClient.AccessUserDirectoryItem;
import edu.courseflow.usermanagement.service.AccessControlUserDirectoryClient.ResolvedIdentity;
import edu.courseflow.usermanagement.service.KeycloakAdminClient.KeycloakUser;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageRequest;

@ExtendWith(MockitoExtension.class)
class UserProfileServiceAdminDirectoryTest {

    @Mock
    private UserProfileRepository profiles;

    @Mock
    private UserProfileAuditLogRepository auditLogs;

    @Mock
    private AccessControlUserDirectoryClient accessDirectory;

    @Mock
    private KeycloakAdminClient keycloak;

    private UserProfileService service;

    @BeforeEach
    void setUp() {
        service = new UserProfileService(profiles, auditLogs, accessDirectory, keycloak);
    }

    @Test
    void adminDirectoryComposesProfileWithAccessControlSummary() {
        CurrentUser admin = admin();
        allowPlatformAdmin(admin);
        when(accessDirectory.list(null, 100)).thenReturn(List.of(new AccessUserDirectoryItem(
                "42", "learner@example.com", "ACTIVE", "STUDENT", "issuer", "subject")));
        when(profiles.findByUserIdInOrderByUserIdAsc(List.of(42L))).thenReturn(List.of(new UserProfile(
                42L,
                "Learner Forty Two",
                "https://cdn.example.com/avatar-42.png",
                null,
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "ORG")));

        var users = service.adminDirectory(admin, null, 100);

        assertThat(users).singleElement()
                .satisfies(user -> {
                    assertThat(user.id()).isEqualTo(42L);
                    assertThat(user.email()).isEqualTo("learner@example.com");
                    assertThat(user.fullName()).isEqualTo("Learner Forty Two");
                    assertThat(user.role()).isEqualTo("STUDENT");
                    assertThat(user.status()).isEqualTo("ACTIVE");
                });
    }

    @Test
    void adminUserFallsBackToEmailDisplayNameWhenProfileIsMissing() {
        CurrentUser admin = admin();
        allowPlatformAdmin(admin);
        when(accessDirectory.get(7L)).thenReturn(new AccessUserDirectoryItem(
                "7", "ops@example.com", "ACTIVE", "ADMIN", "issuer", "subject"));
        when(profiles.findById(7L)).thenReturn(Optional.empty());

        var user = service.adminUser(admin, 7L);

        assertThat(user.id()).isEqualTo(7L);
        assertThat(user.fullName()).isEqualTo("ops");
        assertThat(user.role()).isEqualTo("ADMIN");
        assertThat(user.status()).isEqualTo("ACTIVE");
    }

    @Test
    void profileSummariesFollowRequestedOrder() {
        when(profiles.findByUserIdInOrderByUserIdAsc(List.of(9L, 2L, 42L))).thenReturn(List.of(
                new UserProfile(2L, "Second User", "https://cdn.example.com/2.png", null,
                        "vi-VN", "Asia/Ho_Chi_Minh", "ORG"),
                new UserProfile(9L, "Ninth User", "https://cdn.example.com/9.png", null,
                        "vi-VN", "Asia/Ho_Chi_Minh", "ORG"),
                new UserProfile(42L, "Forty Two", "https://cdn.example.com/42.png", null,
                        "vi-VN", "Asia/Ho_Chi_Minh", "ORG")));

        var summaries = service.summaries(List.of("9", "2", "42"));

        assertThat(summaries).extracting("userId").containsExactly("9", "2", "42");
        assertThat(summaries).extracting("displayName")
                .containsExactly("Ninth User", "Second User", "Forty Two");
    }

    @Test
    void currentUserComposesAccessControlIdentityWithProfile() {
        CurrentUser caller = new CurrentUser(42L, "stale@example.com", "STUDENT");
        when(accessDirectory.get(42L)).thenReturn(new AccessUserDirectoryItem(
                "42", "learner@example.com", "ACTIVE", "STUDENT", "issuer", "subject"));
        when(profiles.findById(42L)).thenReturn(Optional.of(new UserProfile(
                42L,
                "Learner Forty Two",
                "https://cdn.example.com/avatar-42.png",
                null,
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "ORG")));

        var current = service.currentUser(caller);

        assertThat(current.id()).isEqualTo(42L);
        assertThat(current.email()).isEqualTo("learner@example.com");
        assertThat(current.fullName()).isEqualTo("Learner Forty Two");
        assertThat(current.avatarUrl()).isEqualTo("https://cdn.example.com/avatar-42.png");
        assertThat(current.role()).isEqualTo("STUDENT");
        assertThat(current.status()).isEqualTo("ACTIVE");
    }

    @Test
    void currentUserFallsBackToEmailDisplayNameWhenProfileIsMissing() {
        CurrentUser caller = new CurrentUser(7L, "ops@example.com", "ADMIN");
        when(accessDirectory.get(7L)).thenReturn(new AccessUserDirectoryItem(
                "7", "ops@example.com", "ACTIVE", "ADMIN", "issuer", "subject"));
        when(profiles.findById(7L)).thenReturn(Optional.empty());

        var current = service.currentUser(caller);

        assertThat(current.id()).isEqualTo(7L);
        assertThat(current.fullName()).isEqualTo("ops");
        assertThat(current.role()).isEqualTo("ADMIN");
    }

    @Test
    void publicProfileRequiresPublicVisibility() {
        when(profiles.findById(42L)).thenReturn(Optional.of(new UserProfile(
                42L,
                "Learner Forty Two",
                "https://cdn.example.com/avatar-42.png",
                "Private bio",
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "PRIVATE")));

        assertThatThrownBy(() -> service.publicProfile(42L))
                .isInstanceOf(NotFoundException.class);
    }

    @Test
    void publicProfileReturnsFullPublicProfile() {
        when(profiles.findById(42L)).thenReturn(Optional.of(new UserProfile(
                42L,
                "Learner Forty Two",
                "https://cdn.example.com/avatar-42.png",
                "Public bio",
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "PUBLIC")));

        var profile = service.publicProfile(42L);

        assertThat(profile.displayName()).isEqualTo("Learner Forty Two");
        assertThat(profile.bio()).isEqualTo("Public bio");
        assertThat(profile.visibility()).isEqualTo("PUBLIC");
    }

    @Test
    void adminDirectoryCanSearchByProfileDisplayName() {
        CurrentUser admin = admin();
        allowPlatformAdmin(admin);
        UserProfile profile = new UserProfile(
                42L,
                "Learner Forty Two",
                null,
                null,
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "ORG");
        when(accessDirectory.list("Forty", 100)).thenReturn(List.of());
        when(profiles.searchDirectory("forty", PageRequest.of(0, 100))).thenReturn(List.of(profile));
        when(accessDirectory.batch(List.of(42L))).thenReturn(List.of(new AccessUserDirectoryItem(
                "42", "learner@example.com", "ACTIVE", "STUDENT", "issuer", "subject")));
        when(profiles.findByUserIdInOrderByUserIdAsc(List.of(42L))).thenReturn(List.of(profile));

        var users = service.adminDirectory(admin, "Forty", 100);

        assertThat(users).singleElement()
                .satisfies(user -> {
                    assertThat(user.id()).isEqualTo(42L);
                    assertThat(user.fullName()).isEqualTo("Learner Forty Two");
                    assertThat(user.email()).isEqualTo("learner@example.com");
                });
    }

    @Test
    void createAdminUserDelegatesIamToKeycloakAndProvisioningToAccessControl() {
        CurrentUser admin = admin();
        allowPlatformAdmin(admin);
        KeycloakUser keycloakUser = new KeycloakUser(
                "kc-123",
                "new@example.com",
                "new@example.com",
                "New",
                "User",
                true,
                false,
                List.of("VERIFY_EMAIL", "UPDATE_PASSWORD"),
                Map.of());
        UserProfile profile = new UserProfile(
                100000L,
                "New User",
                null,
                null,
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "ORG");
        when(keycloak.createUser("new@example.com", "New User")).thenReturn(keycloakUser);
        when(keycloak.issuer()).thenReturn("https://auth.example.com/realms/courseflow");
        when(accessDirectory.provisionKeycloakUser(
                "https://auth.example.com/realms/courseflow",
                "kc-123",
                "new@example.com")).thenReturn(new ResolvedIdentity(
                        "100000",
                        "https://auth.example.com/realms/courseflow",
                        "kc-123",
                        "new@example.com",
                        "ACTIVE",
                        List.of()));
        when(profiles.findById(100000L)).thenReturn(Optional.of(profile));
        when(profiles.save(profile)).thenReturn(profile);
        when(accessDirectory.get(100000L)).thenReturn(new AccessUserDirectoryItem(
                "100000", "new@example.com", "ACTIVE", null,
                "https://auth.example.com/realms/courseflow", "kc-123"));

        var created = service.createAdminUser(admin, new CreateAdminUserRequest(
                "new@example.com",
                "New User",
                true));

        assertThat(created.id()).isEqualTo(100000L);
        assertThat(created.email()).isEqualTo("new@example.com");
        assertThat(created.fullName()).isEqualTo("New User");
        assertThat(created.role()).isNull();
    }

    @Test
    void deactivateAdminUserDisablesKeycloakAndAccessControl() {
        CurrentUser admin = admin();
        allowPlatformAdmin(admin);
        when(accessDirectory.get(42L)).thenReturn(
                new AccessUserDirectoryItem("42", "learner@example.com", "ACTIVE", "STUDENT", "issuer", "kc-42"),
                new AccessUserDirectoryItem("42", "learner@example.com", "DEACTIVATED", "STUDENT", "issuer", "kc-42"));
        when(profiles.findById(42L)).thenReturn(Optional.of(new UserProfile(
                42L,
                "Learner Forty Two",
                null,
                null,
                "vi-VN",
                "Asia/Ho_Chi_Minh",
                "ORG")));

        var deactivated = service.deactivateAdminUser(admin, 42L, new DeactivateAdminUserRequest("left company"));

        assertThat(deactivated.status()).isEqualTo("DEACTIVATED");
    }

    @Test
    void adminDirectoryRequiresAccessControlPlatformAdminPermission() {
        CurrentUser instructor = new CurrentUser(2L, "instructor@example.com", "INSTRUCTOR");
        when(accessDirectory.authorized("2", "platform:admin", "PLATFORM", null)).thenReturn(false);

        assertThatThrownBy(() -> service.adminDirectory(instructor, null, 100))
                .isInstanceOf(ForbiddenException.class)
                .hasMessageContaining("platform:admin");
    }

    private CurrentUser admin() {
        return new CurrentUser(1L, "admin@example.com", "ADMIN");
    }

    private void allowPlatformAdmin(CurrentUser user) {
        when(accessDirectory.authorized(String.valueOf(user.id()), "platform:admin", "PLATFORM", null))
                .thenReturn(true);
    }
}
