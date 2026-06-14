package edu.courseflow.promotion.service;

import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_MANAGE_FORBIDDEN;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_READ_FORBIDDEN;
import static edu.courseflow.promotion.service.PromotionErrorCodes.COUPON_IMPORT_REVIEW_FORBIDDEN;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.promotion.dto.PromotionDtos.ApplicationClientBindingDto;
import edu.courseflow.promotion.dto.PromotionDtos.ApplicationDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateApplicationClientBindingRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.CreateApplicationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateApplicationRequestDto;
import edu.courseflow.promotion.dto.PromotionDtos.UpdateApplicationStatusRequestDto;
import edu.courseflow.promotion.model.IncentiveApplication;
import edu.courseflow.promotion.model.IncentiveApplicationClientBinding;
import edu.courseflow.promotion.model.IncentiveAuditEvent;
import edu.courseflow.promotion.repository.IncentiveApplicationClientBindingRepository;
import edu.courseflow.promotion.repository.IncentiveApplicationRepository;
import edu.courseflow.promotion.repository.IncentiveAuditEventRepository;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class IncentiveAccessService {

    private static final String APPLICATION_SCOPE_SEPARATOR = ":";
    private static final Set<String> SUPPORTED_BINDING_OPERATIONS = Set.of(
            "admin",
            "evaluate",
            "reserve",
            "commit",
            "cancel",
            "reverse");
    private static final String DENY_ALL_OPERATIONS_JSON = "[]";
    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<>() {
    };

    private final IncentiveApplicationRepository applications;
    private final IncentiveApplicationClientBindingRepository clientBindings;
    private final IncentiveAuditEventRepository auditEvents;
    private final ObjectMapper objectMapper;

    public IncentiveAccessService(IncentiveApplicationRepository applications,
                                  IncentiveApplicationClientBindingRepository clientBindings,
                                  IncentiveAuditEventRepository auditEvents,
                                  ObjectMapper objectMapper) {
        this.applications = applications;
        this.clientBindings = clientBindings;
        this.auditEvents = auditEvents;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public List<ApplicationDto> listApplications(Optional<String> tenantId,
                                                 Optional<String> applicationId,
                                                 Optional<String> status,
                                                 CurrentUser user) {
        requirePlatformAdmin(user);
        return applications.listFiltered(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(status.orElse(null)))
                .stream()
                .map(this::applicationDto)
                .toList();
    }

    @Transactional
    public ApplicationDto createApplication(CreateApplicationRequestDto request, CurrentUser user) {
        return createApplication(request, user, null);
    }

    @Transactional
    public ApplicationDto createApplication(CreateApplicationRequestDto request, CurrentUser user,
                                            String correlationId) {
        requirePlatformAdmin(user);
        AuditMetadata auditMetadata = AuditMetadata.from(user, this, correlationId);
        String tenantId = normalized(request.tenantId(), "tenantId");
        String applicationId = normalized(request.applicationId(), "applicationId");
        applications.findByTenantIdAndApplicationId(tenantId, applicationId).ifPresent(existing -> {
            throw new ConflictException("Incentive application already exists");
        });
        IncentiveApplication application = applications.save(new IncentiveApplication(
                tenantId,
                applicationId,
                request.name(),
                request.status(),
                actorId(user)));
        replaceClientBindings(application, request.allowedClientIds(), actorId(user));
        audit(application.getTenantId(), application.getApplicationId(), application.getId().toString(), "application",
                "application.created", actorId(user), null, Map.of(
                        "applicationUuid", application.getId().toString(),
                        "status", application.getStatus()), auditMetadata);
        return applicationDto(application);
    }

    @Transactional
    public ApplicationDto updateApplication(UUID applicationUuid, UpdateApplicationRequestDto request,
                                            CurrentUser user) {
        return updateApplication(applicationUuid, request, user, null);
    }

    @Transactional
    public ApplicationDto updateApplication(UUID applicationUuid, UpdateApplicationRequestDto request,
                                            CurrentUser user, String correlationId) {
        IncentiveApplication application = application(applicationUuid);
        requireAdminAccess(application.getTenantId(), application.getApplicationId(), user);
        AuditMetadata auditMetadata = AuditMetadata.from(user, this, correlationId);
        application.rename(request.name());
        IncentiveApplication saved = applications.save(application);
        if (request.allowedClientIds() != null) {
            replaceClientBindings(saved, request.allowedClientIds(), actorId(user));
        }
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "application",
                "application.updated", actorId(user), null, Map.of(
                        "applicationUuid", saved.getId().toString(),
                        "name", saved.getName()), auditMetadata);
        return applicationDto(saved);
    }

    @Transactional
    public ApplicationDto updateApplicationStatus(UUID applicationUuid, UpdateApplicationStatusRequestDto request,
                                                  CurrentUser user) {
        return updateApplicationStatus(applicationUuid, request, user, null);
    }

    @Transactional
    public ApplicationDto updateApplicationStatus(UUID applicationUuid, UpdateApplicationStatusRequestDto request,
                                                  CurrentUser user, String correlationId) {
        IncentiveApplication application = application(applicationUuid);
        requireAdminAccess(application.getTenantId(), application.getApplicationId(), user);
        AuditMetadata auditMetadata = AuditMetadata.from(user, this, correlationId);
        try {
            application.changeStatus(request.status());
        } catch (IllegalArgumentException ex) {
            throw new BadRequestException(ex.getMessage());
        }
        IncentiveApplication saved = applications.save(application);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "application",
                "application.status_changed", actorId(user), request.note(), Map.of(
                        "applicationUuid", saved.getId().toString(),
                        "status", saved.getStatus()), auditMetadata);
        return applicationDto(saved);
    }

    @Transactional
    public ApplicationClientBindingDto upsertClientBinding(UUID applicationUuid,
                                                           CreateApplicationClientBindingRequestDto request,
                                                           CurrentUser user) {
        return upsertClientBinding(applicationUuid, request, user, null);
    }

    @Transactional
    public ApplicationClientBindingDto upsertClientBinding(UUID applicationUuid,
                                                           CreateApplicationClientBindingRequestDto request,
                                                           CurrentUser user,
                                                           String correlationId) {
        IncentiveApplication application = application(applicationUuid);
        requireAdminAccess(application.getTenantId(), application.getApplicationId(), user);
        AuditMetadata auditMetadata = AuditMetadata.from(user, this, correlationId);
        String clientId = normalized(request.clientId(), "clientId");
        String allowedOperations = toJson(normalizedAllowedOperations(request.allowedOperations()));
        IncentiveApplicationClientBinding binding = clientBindings
                .findByTenantIdAndApplicationIdAndClientId(
                        application.getTenantId(), application.getApplicationId(), clientId)
                .map(existing -> {
                    existing.replace(request.status(), allowedOperations);
                    return existing;
                })
                .orElseGet(() -> new IncentiveApplicationClientBinding(
                        application.getTenantId(),
                        application.getApplicationId(),
                        clientId,
                        request.status(),
                        allowedOperations,
                        actorId(user)));
        IncentiveApplicationClientBinding saved = clientBindings.save(binding);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "application-client-binding",
                "application_client_binding.upserted", actorId(user), null, Map.of(
                        "applicationUuid", application.getId().toString(),
                        "clientId", saved.getClientId(),
                        "status", saved.getStatus(),
                        "allowedOperations", readStringList(saved.getAllowedOperations())), auditMetadata);
        return bindingDto(saved);
    }

    @Transactional(readOnly = true)
    public void requireActiveApplication(String tenantId, String applicationId, CurrentUser user, String operation) {
        IncentiveApplication application = requireApplication(tenantId, applicationId);
        if (!application.active()) {
            throw new ForbiddenException("Incentive application is not active: " + tenantId + "/" + applicationId);
        }
        enforceClientBinding(application, user, operation);
    }

    @Transactional(readOnly = true)
    public void requireKnownApplication(String tenantId, String applicationId, CurrentUser user, String operation) {
        IncentiveApplication application = requireApplication(tenantId, applicationId);
        enforceClientBinding(application, user, operation);
    }

    @Transactional(readOnly = true)
    public void requireClientOperation(String tenantId, String applicationId, CurrentUser user, String operation) {
        IncentiveApplication application = requireApplication(tenantId, applicationId);
        enforceClientBinding(application, user, operation);
    }

    @Transactional(readOnly = true)
    public void requireTrustedRuntimeCaller(String tenantId, String applicationId, CurrentUser user, String operation) {
        if ("service".equalsIgnoreCase(actorType(user))) {
            return;
        }
        throw new ForbiddenException(
                "Incentive runtime facts must be submitted by a trusted application service");
    }

    public String sourceClientId(CurrentUser user) {
        return firstInternalTokenClaim(user, "azp", "client_id", "clientId");
    }

    public String actorType(CurrentUser user) {
        return firstInternalTokenClaim(user, "actor_type", "actorType");
    }

    @Transactional(readOnly = true)
    public void requireAdminAccess(String tenantId, String applicationId, CurrentUser user) {
        requireAuthenticated(user);
        if (canAdminAccess(tenantId, applicationId, user)) {
            return;
        }
        throw new ForbiddenException("Not allowed to manage incentive application: " + tenantId + "/" + applicationId);
    }

    public boolean canAdminAccess(String tenantId, String applicationId, CurrentUser user) {
        return isPlatformAdmin(user)
                || isScopedOperator(tenantId, applicationId, user, "ORG_ADMIN")
                || isScopedOperator(tenantId, applicationId, user, "INCENTIVE_ADMIN");
    }

    @Transactional(readOnly = true)
    public void requireCouponImportManageAccess(String tenantId, String applicationId, CurrentUser user) {
        requireAuthenticated(user);
        if (canCouponImportManageAccess(tenantId, applicationId, user)) {
            return;
        }
        throw ForbiddenException.coded(
                COUPON_IMPORT_MANAGE_FORBIDDEN,
                "Not allowed to operate coupon import: " + tenantId + "/" + applicationId);
    }

    public boolean canCouponImportManageAccess(String tenantId, String applicationId, CurrentUser user) {
        return canAdminAccess(tenantId, applicationId, user)
                || isScopedOperator(tenantId, applicationId, user, "INCENTIVE_OPERATOR");
    }

    @Transactional(readOnly = true)
    public void requireCouponImportReadAccess(String tenantId, String applicationId, CurrentUser user) {
        requireAuthenticated(user);
        if (canCouponImportReadAccess(tenantId, applicationId, user)) {
            return;
        }
        throw ForbiddenException.coded(
                COUPON_IMPORT_READ_FORBIDDEN,
                "Not allowed to view coupon import operations: " + tenantId + "/" + applicationId);
    }

    public boolean canCouponImportReadAccess(String tenantId, String applicationId, CurrentUser user) {
        return canCouponImportManageAccess(tenantId, applicationId, user)
                || isScopedOperator(tenantId, applicationId, user, "INCENTIVE_REVIEWER");
    }

    @Transactional(readOnly = true)
    public void requireReviewAccess(String tenantId, String applicationId, CurrentUser user) {
        requireAuthenticated(user);
        if (canReviewAccess(tenantId, applicationId, user)) {
            return;
        }
        throw new ForbiddenException("Not allowed to review incentive campaign: " + tenantId + "/" + applicationId);
    }

    @Transactional(readOnly = true)
    public void requireCouponImportReviewAccess(String tenantId, String applicationId, CurrentUser user) {
        requireAuthenticated(user);
        if (canReviewAccess(tenantId, applicationId, user)) {
            return;
        }
        throw ForbiddenException.coded(
                COUPON_IMPORT_REVIEW_FORBIDDEN,
                "Not allowed to review coupon import approval: " + tenantId + "/" + applicationId);
    }

    public boolean canReviewAccess(String tenantId, String applicationId, CurrentUser user) {
        return isPlatformAdmin(user) || isScopedOperator(tenantId, applicationId, user, "ORG_ADMIN")
                || isScopedOperator(tenantId, applicationId, user, "INCENTIVE_ADMIN")
                || isScopedOperator(tenantId, applicationId, user, "INCENTIVE_REVIEWER");
    }

    public ApplicationDto applicationDto(IncentiveApplication application) {
        return new ApplicationDto(
                application.getId(),
                application.getTenantId(),
                application.getApplicationId(),
                application.getName(),
                application.getStatus(),
                clientBindings.findByTenantIdAndApplicationId(
                                application.getTenantId(), application.getApplicationId())
                        .stream()
                        .map(this::bindingDto)
                        .toList(),
                application.getCreatedAt(),
                application.getUpdatedAt());
    }

    private void replaceClientBindings(IncentiveApplication application, List<String> allowedClientIds,
                                       String actorId) {
        if (allowedClientIds == null) {
            return;
        }
        Set<String> requested = allowedClientIds.stream()
                .map(this::blankToNull)
                .filter(value -> value != null)
                .collect(Collectors.toSet());
        for (IncentiveApplicationClientBinding existing
                : clientBindings.findByTenantIdAndApplicationId(
                application.getTenantId(), application.getApplicationId())) {
            if (!requested.contains(existing.getClientId()) && existing.active()) {
                existing.suspend();
                clientBindings.save(existing);
            }
        }
        for (String rawClientId : requested) {
            String clientId = blankToNull(rawClientId);
            if (clientId == null) {
                continue;
            }
            clientBindings.findByTenantIdAndApplicationIdAndClientId(
                            application.getTenantId(), application.getApplicationId(), clientId)
                    .ifPresentOrElse(existing -> {
                        existing.replace("ACTIVE", DENY_ALL_OPERATIONS_JSON);
                        clientBindings.save(existing);
                    }, () -> clientBindings.save(new IncentiveApplicationClientBinding(
                            application.getTenantId(),
                            application.getApplicationId(),
                            clientId,
                            "ACTIVE",
                            DENY_ALL_OPERATIONS_JSON,
                            actorId)));
        }
    }

    private IncentiveApplication requireApplication(String tenantId, String applicationId) {
        return applications.findByTenantIdAndApplicationId(tenantId, applicationId)
                .orElseThrow(() -> new NotFoundException(
                        "Incentive application not found: " + tenantId + "/" + applicationId));
    }

    private IncentiveApplication application(UUID applicationUuid) {
        return applications.findById(applicationUuid)
                .orElseThrow(() -> new NotFoundException("Incentive application not found: " + applicationUuid));
    }

    private void enforceClientBinding(IncentiveApplication application, CurrentUser user, String operation) {
        requireOperationScopeForServiceActor(user, operation);
        String clientId = callerClientId(user);
        if (clientId == null) {
            throw new ForbiddenException("Incentive caller is not bound to application");
        }
        IncentiveApplicationClientBinding binding = clientBindings
                .findByTenantIdAndApplicationIdAndClientId(
                        application.getTenantId(), application.getApplicationId(), clientId)
                .orElseThrow(() -> new ForbiddenException("Incentive caller is not bound to application"));
        if (!binding.active()) {
            throw new ForbiddenException("Incentive caller binding is suspended");
        }
        List<String> operations = readStringList(binding.getAllowedOperations());
        if (operations.isEmpty()) {
            throw new ForbiddenException("Incentive caller binding has no allowed operations");
        }
        if (operations.stream().noneMatch(operation::equalsIgnoreCase)) {
            throw new ForbiddenException("Incentive caller is not allowed to run operation: " + operation);
        }
    }

    private void requireOperationScopeForServiceActor(CurrentUser user, String operation) {
        Map<String, Object> claims = internalTokenClaims(user);
        if (!"service".equalsIgnoreCase(firstString(claims, "actor_type", "actorType"))) {
            return;
        }
        String requiredScope = promotionScopeForOperation(operation);
        Set<String> scopes = extractScopes(claims);
        if (!scopes.contains("*") && !scopes.contains(requiredScope)) {
            throw new ForbiddenException("Missing internal promotion operation scope: " + requiredScope);
        }
    }

    private String promotionScopeForOperation(String operation) {
        String normalized = operation == null ? "" : operation.trim().toLowerCase(Locale.ROOT);
        return switch (normalized) {
            case "evaluate" -> InternalScopes.PROMOTION_EVALUATE;
            case "reserve" -> InternalScopes.PROMOTION_RESERVE;
            case "commit" -> InternalScopes.PROMOTION_COMMIT;
            case "cancel" -> InternalScopes.PROMOTION_CANCEL;
            case "reverse" -> InternalScopes.PROMOTION_REVERSE;
            default -> InternalScopes.PROMOTION_ADMIN;
        };
    }

    private boolean isPlatformAdmin(CurrentUser user) {
        return user != null && user.hasPlatformRole("ADMIN");
    }

    private boolean isScopedOperator(String tenantId, String applicationId, CurrentUser user, String role) {
        return user != null
                && (user.hasScopedRole(role, "TENANT", tenantId)
                || user.hasScopedRole(role, "APPLICATION", applicationScope(tenantId, applicationId)));
    }

    private String applicationScope(String tenantId, String applicationId) {
        return tenantId + APPLICATION_SCOPE_SEPARATOR + applicationId;
    }

    public void requirePlatformAdmin(CurrentUser user) {
        requireAuthenticated(user);
        if (!isPlatformAdmin(user)) {
            throw new ForbiddenException("Requires platform ADMIN role");
        }
    }

    private void requireAuthenticated(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ForbiddenException("Authenticated operator is required");
        }
    }

    private ApplicationClientBindingDto bindingDto(IncentiveApplicationClientBinding binding) {
        return new ApplicationClientBindingDto(
                binding.getId(),
                binding.getTenantId(),
                binding.getApplicationId(),
                binding.getClientId(),
                binding.getStatus(),
                readStringList(binding.getAllowedOperations()),
                binding.getCreatedAt(),
                binding.getUpdatedAt());
    }

    private String callerClientId(CurrentUser user) {
        return sourceClientId(user);
    }

    private String firstInternalTokenClaim(CurrentUser user, String... keys) {
        return firstString(internalTokenClaims(user), keys);
    }

    private Map<String, Object> internalTokenClaims(CurrentUser user) {
        if (user == null || user.internalToken() == null) {
            return Map.of();
        }
        String[] parts = user.internalToken().split("\\.");
        if (parts.length < 2) {
            return Map.of();
        }
        try {
            String payload = new String(Base64.getUrlDecoder().decode(parts[1]), StandardCharsets.UTF_8);
            return objectMapper.readValue(payload, MAP_TYPE);
        } catch (IllegalArgumentException | JsonProcessingException ex) {
            return Map.of();
        }
    }

    private String firstString(Map<String, Object> claims, String... keys) {
        for (String key : keys) {
            Object value = claims.get(key);
            if (value != null && !String.valueOf(value).isBlank()) {
                return String.valueOf(value).trim();
            }
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private Set<String> extractScopes(Map<String, Object> claims) {
        LinkedHashSet<String> scopes = new LinkedHashSet<>();
        Object rawScope = claims.get("scope");
        if (rawScope != null) {
            for (String scope : rawScope.toString().split("\\s+")) {
                String value = blankToNull(scope);
                if (value != null) {
                    scopes.add(value);
                }
            }
        }
        Object rawScp = claims.get("scp");
        if (rawScp instanceof List<?> list) {
            for (Object scope : list) {
                String value = scope == null ? null : blankToNull(scope.toString());
                if (value != null) {
                    scopes.add(value);
                }
            }
        }
        return scopes;
    }

    private List<String> readStringList(String json) {
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<String> result = objectMapper.readValue(json, STRING_LIST);
            return result == null ? List.of() : result;
        } catch (JsonProcessingException ex) {
            return List.of();
        }
    }

    private List<String> normalizedAllowedOperations(List<String> operations) {
        if (operations == null) {
            return List.of();
        }
        LinkedHashSet<String> normalized = new LinkedHashSet<>();
        for (String operation : operations) {
            String value = blankToNull(operation);
            if (value == null) {
                throw new BadRequestException("Client binding allowed operation is required");
            }
            String canonical = value.toLowerCase(Locale.ROOT);
            if (!SUPPORTED_BINDING_OPERATIONS.contains(canonical)) {
                throw new BadRequestException("Unsupported incentive client operation: " + operation);
            }
            normalized.add(canonical);
        }
        return List.copyOf(normalized);
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new BadRequestException("Invalid incentive access payload");
        }
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, Object payload, AuditMetadata metadata) {
        auditEvents.save(new IncentiveAuditEvent(
                tenantId,
                applicationId,
                aggregateId,
                aggregateType,
                action,
                actorId,
                note,
                toJson(payload == null ? Map.of() : payload),
                metadata == null ? null : metadata.correlationId(),
                metadata == null ? null : metadata.sourceClientId()));
    }

    private String actorId(CurrentUser user) {
        return user == null || user.id() == null ? null : String.valueOf(user.id());
    }

    private String normalized(String value, String field) {
        String normalized = blankToNull(value);
        if (normalized == null) {
            throw new BadRequestException(field + " is required");
        }
        return normalized;
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
