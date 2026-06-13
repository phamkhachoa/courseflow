package edu.courseflow.usermanagement.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.usermanagement.dto.UserProfileDtos.AccountSecuritySnapshotDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.AdminUserPrivacyExportDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.AdminUserDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.CreateAdminUserRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.CurrentUserDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.DeactivateAdminUserRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.ProfileSummaryDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.ProvisionUserProfileRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.RoleGrantExportDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UpdateMyProfileRequest;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UserDirectoryItemDto;
import edu.courseflow.usermanagement.dto.UserProfileDtos.UserProfileDto;
import edu.courseflow.usermanagement.service.AccessControlUserDirectoryClient.AccessUserDirectoryItem;
import edu.courseflow.usermanagement.service.AccessControlUserDirectoryClient.RoleGrantExport;
import edu.courseflow.usermanagement.service.KeycloakAdminClient.KeycloakUser;
import edu.courseflow.usermanagement.model.UserProfile;
import edu.courseflow.usermanagement.model.UserProfileAuditLog;
import edu.courseflow.usermanagement.repository.UserProfileAuditLogRepository;
import edu.courseflow.usermanagement.repository.UserProfileRepository;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class UserProfileService {

    private static final Set<String> VISIBILITIES = Set.of("PUBLIC", "PRIVATE", "ORG");

    private final UserProfileRepository profiles;
    private final UserProfileAuditLogRepository auditLogs;
    private final AccessControlUserDirectoryClient accessDirectory;
    private final KeycloakAdminClient keycloak;

    public UserProfileService(
            UserProfileRepository profiles,
            UserProfileAuditLogRepository auditLogs,
            AccessControlUserDirectoryClient accessDirectory,
            KeycloakAdminClient keycloak) {
        this.profiles = profiles;
        this.auditLogs = auditLogs;
        this.accessDirectory = accessDirectory;
        this.keycloak = keycloak;
    }

    @Transactional(readOnly = true)
    public UserProfileDto me(CurrentUser user) {
        long userId = requireUser(user);
        return profile(userId);
    }

    @Transactional(readOnly = true)
    public CurrentUserDto currentUser(CurrentUser user) {
        long userId = requireUser(user);
        AccessUserDirectoryItem accessUser = accessDirectory.get(userId);
        if (accessUser == null || accessUser.userId() == null || accessUser.userId().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "access-control returned no user");
        }
        UserProfile profile = profiles.findById(userId).orElse(null);
        String email = trimToNull(accessUser.email());
        String fullName = profile == null ? fallbackDisplayName(userId, email) : profile.getDisplayName();
        String status = accessUser.status() == null || accessUser.status().isBlank() ? "UNKNOWN" : accessUser.status();
        return new CurrentUserDto(
                userId,
                email,
                fullName,
                profile == null ? null : profile.getAvatarUrl(),
                accessUser.primaryRole(),
                status,
                false,
                false);
    }

    @Transactional
    public UserProfileDto updateMe(CurrentUser user, UpdateMyProfileRequest request) {
        long userId = requireUser(user);
        String visibility = normalizeVisibility(request.visibility());
        UserProfile profile = profiles.findById(userId).orElseGet(() -> new UserProfile(
                userId,
                request.displayName().trim(),
                trimToNull(request.avatarUrl()),
                trimToNull(request.bio()),
                trimToDefault(request.locale(), "vi-VN"),
                trimToDefault(request.timezone(), "Asia/Ho_Chi_Minh"),
                visibility));
        profile.update(
                request.displayName().trim(),
                trimToNull(request.avatarUrl()),
                trimToNull(request.bio()),
                trimToDefault(request.locale(), "vi-VN"),
                trimToDefault(request.timezone(), "Asia/Ho_Chi_Minh"),
                visibility);
        UserProfile saved = profiles.save(profile);
        audit(saved, user, "PROFILE_UPDATED", null);
        return toProfileDto(saved);
    }

    @Transactional
    public UserProfileDto provisionProfile(CurrentUser caller, ProvisionUserProfileRequest request) {
        long userId = parseUserId(request.userId());
        String visibility = normalizeVisibility(request.visibility());
        UserProfile profile = profiles.findById(userId).orElseGet(() -> new UserProfile(
                userId,
                request.displayName().trim(),
                trimToNull(request.avatarUrl()),
                trimToNull(request.bio()),
                trimToDefault(request.locale(), "vi-VN"),
                trimToDefault(request.timezone(), "Asia/Ho_Chi_Minh"),
                visibility));
        profile.update(
                request.displayName().trim(),
                trimToNull(request.avatarUrl()),
                trimToNull(request.bio()),
                trimToDefault(request.locale(), "vi-VN"),
                trimToDefault(request.timezone(), "Asia/Ho_Chi_Minh"),
                visibility);
        UserProfile saved = profiles.save(profile);
        audit(saved, caller, "PROFILE_PROVISIONED", null);
        return toProfileDto(saved);
    }

    @Transactional(readOnly = true)
    public UserProfileDto profile(long userId) {
        return profiles.findById(userId)
                .map(this::toProfileDto)
                .orElseThrow(() -> new NotFoundException("PROFILE_NOT_FOUND", userId));
    }

    @Transactional(readOnly = true)
    public List<ProfileSummaryDto> summaries(List<String> rawUserIds) {
        List<Long> userIds = parseIds(rawUserIds);
        if (userIds.isEmpty()) {
            return List.of();
        }
        Map<Long, UserProfile> profileById = profiles.findByUserIdInOrderByUserIdAsc(userIds).stream()
                .collect(LinkedHashMap::new, (map, profile) -> map.put(profile.getUserId(), profile), Map::putAll);
        return userIds.stream()
                .map(profileById::get)
                .filter(java.util.Objects::nonNull)
                .map(this::toProfileSummaryDto)
                .toList();
    }

    @Transactional(readOnly = true)
    public UserProfileDto publicProfile(long userId) {
        UserProfile profile = profiles.findById(userId)
                .filter(candidate -> "PUBLIC".equals(candidate.getVisibility()))
                .orElseThrow(() -> new NotFoundException("PUBLIC_PROFILE_NOT_FOUND", userId));
        return toProfileDto(profile);
    }

    @Transactional(readOnly = true)
    public List<UserDirectoryItemDto> directory(CurrentUser caller, String query, int limit) {
        requirePlatformAdmin(caller);
        int boundedLimit = Math.max(1, Math.min(limit, 100));
        String needle = query == null || query.isBlank() ? "" : query.trim().toLowerCase(Locale.ROOT);
        return profiles.searchDirectory(needle, PageRequest.of(0, boundedLimit)).stream()
                .map(profile -> new UserDirectoryItemDto(
                        String.valueOf(profile.getUserId()),
                        profile.getDisplayName(),
                        profile.getAvatarUrl(),
                        profile.getLocale(),
                        profile.getTimezone(),
                        profile.getVisibility()))
                .toList();
    }

    @Transactional(readOnly = true)
    public List<AdminUserDto> adminDirectory(CurrentUser caller, String query, int limit) {
        requirePlatformAdmin(caller);
        int boundedLimit = Math.max(1, Math.min(limit, 200));
        Map<Long, AccessUserDirectoryItem> accessById = new LinkedHashMap<>();
        for (AccessUserDirectoryItem item : nullSafe(accessDirectory.list(query, boundedLimit))) {
            putAccessUser(accessById, item);
        }
        if (query != null && !query.isBlank() && accessById.size() < boundedLimit) {
            String needle = query.trim().toLowerCase(Locale.ROOT);
            List<Long> profileMatchIds = profiles.searchDirectory(needle, PageRequest.of(0, boundedLimit)).stream()
                    .map(UserProfile::getUserId)
                    .filter(userId -> !accessById.containsKey(userId))
                    .limit(boundedLimit - accessById.size())
                    .toList();
            if (!profileMatchIds.isEmpty()) {
                for (AccessUserDirectoryItem item : nullSafe(accessDirectory.batch(profileMatchIds))) {
                    putAccessUser(accessById, item);
                }
            }
        }
        if (accessById.isEmpty()) {
            return List.of();
        }
        Map<Long, UserProfile> profileById = profiles.findByUserIdInOrderByUserIdAsc(accessById.keySet().stream()
                        .toList())
                .stream()
                .collect(LinkedHashMap::new, (map, profile) -> map.put(profile.getUserId(), profile), Map::putAll);
        return accessById.values().stream()
                .map(item -> toAdminUserDto(item, profileById.get(parseUserId(item.userId()))))
                .toList();
    }

    @Transactional(readOnly = true)
    public AdminUserDto adminUser(CurrentUser caller, long userId) {
        requirePlatformAdmin(caller);
        return adminUserRecord(userId);
    }

    private AdminUserDto adminUserRecord(long userId) {
        AccessUserDirectoryItem item = accessDirectory.get(userId);
        if (item == null || item.userId() == null || item.userId().isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "access-control returned no user");
        }
        UserProfile profile = profiles.findById(userId).orElse(null);
        return toAdminUserDto(item, profile);
    }

    @Transactional
    public AdminUserDto createAdminUser(CurrentUser caller, CreateAdminUserRequest request) {
        requirePlatformAdmin(caller);
        String email = normalizeEmail(request.email());
        String fullName = normalizeRequired(request.fullName(), "fullName");
        KeycloakUser keycloakUser = keycloak.createUser(email, fullName);
        try {
            var resolved = accessDirectory.provisionKeycloakUser(
                    keycloak.issuer(),
                    keycloakUser.id(),
                    email);
            keycloak.setCourseFlowUserId(keycloakUser.id(), resolved.userId());
            provisionProfile(caller, new ProvisionUserProfileRequest(
                    resolved.userId(),
                    fullName,
                    null,
                    null,
                    "vi-VN",
                    "Asia/Ho_Chi_Minh",
                    "ORG"));
            if (Boolean.TRUE.equals(request.sendSetupEmail())) {
                keycloak.sendSetupEmail(keycloakUser.id());
            }
            profiles.findById(parseUserId(resolved.userId())).ifPresent(profile -> audit(
                    profile, caller, "ADMIN_USER_CREATED", "keycloakSubject=" + keycloakUser.id()));
            return adminUserRecord(parseUserId(resolved.userId()));
        } catch (RuntimeException ex) {
            try {
                keycloak.deleteUser(keycloakUser.id());
            } catch (RuntimeException cleanupFailure) {
                ex.addSuppressed(cleanupFailure);
            }
            throw ex;
        }
    }

    @Transactional
    public AdminUserDto deactivateAdminUser(CurrentUser caller, long userId, DeactivateAdminUserRequest request) {
        requirePlatformAdmin(caller);
        if (caller != null && caller.id() != null && caller.id().equals(userId)) {
            throw new BadRequestException("ADMIN_CANNOT_DEACTIVATE_SELF");
        }
        String reason = normalizeRequired(request.reason(), "reason");
        AccessUserDirectoryItem accessUser = accessDirectory.get(userId);
        if (accessUser.externalSubject() == null || accessUser.externalSubject().isBlank()) {
            throw new BadRequestException("KEYCLOAK_IDENTITY_LINK_REQUIRED");
        }
        keycloak.disableUser(accessUser.externalSubject());
        keycloak.logoutUser(accessUser.externalSubject());
        accessDirectory.deactivate(userId, reason);
        profiles.findById(userId).ifPresent(profile -> audit(profile, caller, "ADMIN_USER_DEACTIVATED",
                detail("reason=", reason)));
        return adminUserRecord(userId);
    }

    @Transactional(readOnly = true)
    public AdminUserPrivacyExportDto exportAdminUserPrivacy(CurrentUser caller, long userId) {
        requirePlatformAdmin(caller);
        AdminUserDto profile = adminUserRecord(userId);
        AccessUserDirectoryItem accessUser = accessDirectory.get(userId);
        KeycloakUser keycloakUser = accessUser.externalSubject() == null || accessUser.externalSubject().isBlank()
                ? null
                : keycloak.getUser(accessUser.externalSubject());
        List<RoleGrantExportDto> roleAssignments = nullSafeRoleGrants(accessDirectory.exportAssignments(userId)).stream()
                .map(this::toRoleGrantExportDto)
                .toList();
        profiles.findById(userId).ifPresent(userProfile -> audit(userProfile, caller, "ADMIN_USER_PRIVACY_EXPORTED",
                "keycloakSubject=" + accessUser.externalSubject()));
        return new AdminUserPrivacyExportDto(
                profile,
                toAccountSecuritySnapshot(accessUser, keycloakUser),
                roleAssignments,
                java.time.Instant.now());
    }

    private long requireUser(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new BadRequestException("AUTHENTICATED_USER_REQUIRED");
        }
        return user.id();
    }

    private void requirePlatformAdmin(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("platform:admin permission is required");
        }
        if (!accessDirectory.authorized(String.valueOf(user.id()), "platform:admin", "PLATFORM", null)) {
            throw new ForbiddenException("platform:admin permission is required");
        }
    }

    private List<Long> parseIds(List<String> rawUserIds) {
        if (rawUserIds == null) {
            return List.of();
        }
        Set<Long> ids = new LinkedHashSet<>();
        for (String raw : rawUserIds) {
            try {
                if (raw != null && !raw.isBlank()) {
                    ids.add(Long.parseLong(raw.trim()));
                }
            } catch (NumberFormatException ex) {
                throw new BadRequestException("INVALID_USER_ID");
            }
        }
        return List.copyOf(ids);
    }

    private long parseUserId(String raw) {
        try {
            if (raw != null && !raw.isBlank()) {
                return Long.parseLong(raw.trim());
            }
        } catch (NumberFormatException ex) {
            throw new BadRequestException("INVALID_USER_ID");
        }
        throw new BadRequestException("INVALID_USER_ID");
    }

    private String normalizeRequired(String raw, String field) {
        if (raw == null || raw.isBlank()) {
            throw new BadRequestException("MISSING_" + field.toUpperCase(Locale.ROOT));
        }
        return raw.trim();
    }

    private String normalizeEmail(String raw) {
        String email = normalizeRequired(raw, "email").toLowerCase(Locale.ROOT);
        if (!email.contains("@")) {
            throw new BadRequestException("INVALID_EMAIL");
        }
        return email;
    }

    private String normalizeVisibility(String raw) {
        String visibility = raw == null || raw.isBlank()
                ? "PRIVATE"
                : raw.trim().toUpperCase(Locale.ROOT);
        if (!VISIBILITIES.contains(visibility)) {
            throw new BadRequestException("INVALID_PROFILE_VISIBILITY");
        }
        return visibility;
    }

    private String trimToDefault(String raw, String fallback) {
        return raw == null || raw.isBlank() ? fallback : raw.trim();
    }

    private String trimToNull(String raw) {
        return raw == null || raw.isBlank() ? null : raw.trim();
    }

    private UserProfileDto toProfileDto(UserProfile profile) {
        return new UserProfileDto(
                String.valueOf(profile.getUserId()),
                profile.getDisplayName(),
                profile.getAvatarUrl(),
                profile.getBio(),
                profile.getLocale(),
                profile.getTimezone(),
                profile.getVisibility());
    }

    private ProfileSummaryDto toProfileSummaryDto(UserProfile profile) {
        return new ProfileSummaryDto(
                String.valueOf(profile.getUserId()),
                profile.getDisplayName(),
                profile.getAvatarUrl());
    }

    private AdminUserDto toAdminUserDto(AccessUserDirectoryItem item, UserProfile profile) {
        long userId = parseUserId(item.userId());
        String email = trimToNull(item.email());
        String fullName = profile == null ? fallbackDisplayName(userId, email) : profile.getDisplayName();
        String status = item.status() == null || item.status().isBlank() ? "UNKNOWN" : item.status();
        return new AdminUserDto(userId, email, fullName, item.primaryRole(), status);
    }

    private void putAccessUser(Map<Long, AccessUserDirectoryItem> target, AccessUserDirectoryItem item) {
        if (item != null && item.userId() != null && !item.userId().isBlank()) {
            target.putIfAbsent(parseUserId(item.userId()), item);
        }
    }

    private List<AccessUserDirectoryItem> nullSafe(List<AccessUserDirectoryItem> items) {
        return items == null ? List.of() : items;
    }

    private List<RoleGrantExport> nullSafeRoleGrants(List<RoleGrantExport> items) {
        return items == null ? List.of() : items;
    }

    private String fallbackDisplayName(long userId, String email) {
        if (email != null && !email.isBlank()) {
            int at = email.indexOf('@');
            return at > 0 ? email.substring(0, at) : email;
        }
        return "User #" + userId;
    }

    private void audit(UserProfile profile, CurrentUser actor, String action, String detail) {
        auditLogs.save(new UserProfileAuditLog(
                profile,
                actor == null || actor.id() == null ? "system" : "user:" + actor.id(),
                action,
                detail));
    }

    private AccountSecuritySnapshotDto toAccountSecuritySnapshot(AccessUserDirectoryItem accessUser,
            KeycloakUser keycloakUser) {
        if (keycloakUser == null) {
            return new AccountSecuritySnapshotDto(
                    accessUser.externalSubject(),
                    false,
                    false,
                    List.of(),
                    java.util.Map.of());
        }
        return new AccountSecuritySnapshotDto(
                keycloakUser.id(),
                keycloakUser.enabled(),
                keycloakUser.emailVerified(),
                keycloakUser.requiredActions(),
                keycloakUser.attributes());
    }

    private RoleGrantExportDto toRoleGrantExportDto(RoleGrantExport assignment) {
        return new RoleGrantExportDto(
                assignment.id(),
                assignment.roleId(),
                assignment.roleCode(),
                assignment.roleName(),
                assignment.scopeType(),
                assignment.scopeId(),
                assignment.grantedBy(),
                assignment.grantedAt(),
                assignment.expiresAt(),
                assignment.revokedAt(),
                assignment.revokedBy(),
                assignment.createdAt());
    }

    private String detail(String prefix, String value) {
        String detail = prefix + value;
        return detail.length() > 255 ? detail.substring(0, 255) : detail;
    }

}
