package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_ACCESS_DENIED;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_CLIENT_NOT_BOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_CLIENT_OPERATION_NOT_ALLOWED;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.security.InternalJwtService;
import edu.courseflow.commonlibrary.security.InternalScopes;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.ClientBindingRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpsertClientBindingRequestDto;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyProgramClientBinding;
import edu.courseflow.loyalty.repository.LoyaltyProgramClientBindingRepository;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyAccessService {

    private static final String APPLICATION_SCOPE_SEPARATOR = ":";
    private static final Set<String> SUPPORTED_OPERATIONS = Set.of(
            "admin", "read", "earn", "burn", "reverse", "adjust", "expire");
    private static final TypeReference<List<String>> STRING_LIST = new TypeReference<>() {
    };

    private final LoyaltyProgramClientBindingRepository clientBindings;
    private final ObjectMapper objectMapper;
    private final InternalJwtService internalJwtService;

    public LoyaltyAccessService(
            LoyaltyProgramClientBindingRepository clientBindings,
            ObjectMapper objectMapper,
            InternalJwtService internalJwtService) {
        this.clientBindings = clientBindings;
        this.objectMapper = objectMapper;
        this.internalJwtService = internalJwtService;
    }

    @Transactional
    public void replaceClientBindings(
            LoyaltyProgram program,
            List<ClientBindingRequestDto> requestedBindings,
            CurrentUser user) {
        if (requestedBindings == null) {
            return;
        }
        requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        Map<String, List<String>> requested = requestedBindings.stream()
                .filter(binding -> binding != null && blankToNull(binding.clientId()) != null)
                .collect(Collectors.toMap(
                        binding -> blankToNull(binding.clientId()),
                        binding -> normalizedAllowedOperations(binding.allowedOperations()),
                        (left, right) -> right));
        for (LoyaltyProgramClientBinding existing : clientBindings.findByTenantIdAndApplicationIdAndProgramId(
                program.getTenantId(), program.getApplicationId(), program.getProgramId())) {
            if (!requested.containsKey(existing.getClientId()) && existing.active()) {
                existing.suspend();
                clientBindings.save(existing);
            }
        }
        for (Map.Entry<String, List<String>> entry : requested.entrySet()) {
            String allowedOperations = toJson(entry.getValue());
            clientBindings.findByTenantIdAndApplicationIdAndProgramIdAndClientId(
                            program.getTenantId(), program.getApplicationId(), program.getProgramId(), entry.getKey())
                    .ifPresentOrElse(existing -> {
                        existing.replace("ACTIVE", allowedOperations);
                        clientBindings.save(existing);
                    }, () -> clientBindings.save(new LoyaltyProgramClientBinding(
                            program,
                            entry.getKey(),
                            allowedOperations,
                            actorId(user))));
        }
    }

    @Transactional
    public LoyaltyProgramClientBinding upsertClientBinding(
            LoyaltyProgram program,
            UpsertClientBindingRequestDto request,
            CurrentUser user) {
        requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        String clientId = blankToNull(request.clientId());
        if (clientId == null) {
            throw ForbiddenException.coded(
                    LOYALTY_CLIENT_NOT_BOUND,
                    "Loyalty client binding requires clientId");
        }
        String allowedOperations = toJson(normalizedAllowedOperations(request.allowedOperations()));
        return clientBindings.findByTenantIdAndApplicationIdAndProgramIdAndClientId(
                        program.getTenantId(), program.getApplicationId(), program.getProgramId(), clientId)
                .map(existing -> {
                    existing.replace(request.status(), allowedOperations);
                    return clientBindings.save(existing);
                })
                .orElseGet(() -> {
                    LoyaltyProgramClientBinding binding = new LoyaltyProgramClientBinding(
                            program,
                            clientId,
                            allowedOperations,
                            actorId(user));
                    binding.replace(request.status(), allowedOperations);
                    return clientBindings.save(binding);
                });
    }

    @Transactional(readOnly = true)
    public void requireAdminAccess(String tenantId, String applicationId, CurrentUser user) {
        if (canAdminAccess(tenantId, applicationId, user)) {
            return;
        }
        throw ForbiddenException.coded(
                LOYALTY_ACCESS_DENIED,
                "Not allowed to manage loyalty application: " + tenantId + "/" + applicationId);
    }

    public boolean canAdminAccess(String tenantId, String applicationId, CurrentUser user) {
        return isPlatformAdmin(user)
                || isScopedOperator(tenantId, applicationId, user, "LOYALTY_ADMIN")
                || serviceHasScope(user, InternalScopes.LOYALTY_ADMIN);
    }

    @Transactional(readOnly = true)
    public void requirePlatformAdmin(CurrentUser user) {
        if (isPlatformAdmin(user) || serviceHasScope(user, InternalScopes.LOYALTY_ADMIN)) {
            return;
        }
        throw ForbiddenException.coded(
                LOYALTY_ACCESS_DENIED,
                "Platform admin access is required for global loyalty operations");
    }

    @Transactional(readOnly = true)
    public void requireProgramReadAccess(LoyaltyProgram program, CurrentUser user) {
        if (canReadAccess(program.getTenantId(), program.getApplicationId(), user)) {
            return;
        }
        requireBoundServiceOperation(program, user, "read");
    }

    public boolean canReadAccess(String tenantId, String applicationId, CurrentUser user) {
        return canAdminAccess(tenantId, applicationId, user)
                || isScopedOperator(tenantId, applicationId, user, "LOYALTY_REVIEWER")
                || isScopedOperator(tenantId, applicationId, user, "LOYALTY_OPERATOR");
    }

    @Transactional(readOnly = true)
    public void requireReadAccess(String tenantId, String applicationId, CurrentUser user) {
        if (canReadAccess(tenantId, applicationId, user)) {
            return;
        }
        throw ForbiddenException.coded(
                LOYALTY_ACCESS_DENIED,
                "Not allowed to read loyalty application: " + tenantId + "/" + applicationId);
    }

    @Transactional(readOnly = true)
    public void requireAdjustmentAccess(String tenantId, String applicationId, CurrentUser user) {
        if (canAdminAccess(tenantId, applicationId, user)
                || isScopedOperator(tenantId, applicationId, user, "LOYALTY_OPERATOR")) {
            return;
        }
        throw ForbiddenException.coded(
                LOYALTY_ACCESS_DENIED,
                "Not allowed to adjust loyalty points: " + tenantId + "/" + applicationId);
    }

    @Transactional(readOnly = true)
    public void requireAdjustmentReviewAccess(String tenantId, String applicationId, CurrentUser user) {
        if (canAdminAccess(tenantId, applicationId, user)
                || isScopedOperator(tenantId, applicationId, user, "LOYALTY_REVIEWER")) {
            return;
        }
        throw ForbiddenException.coded(
                LOYALTY_ACCESS_DENIED,
                "Not allowed to review loyalty adjustments: " + tenantId + "/" + applicationId);
    }

    @Transactional(readOnly = true)
    public void requireRuntimeOperation(LoyaltyProgram program, CurrentUser user, String operation) {
        requireBoundServiceOperation(program, user, operation);
    }

    public boolean canServiceOperation(CurrentUser user, String operation) {
        String normalizedOperation = normalizeOperation(operation);
        return "service".equalsIgnoreCase(actorType(user))
                && serviceHasScope(user, loyaltyScopeForOperation(normalizedOperation));
    }

    public String sourceClientId(CurrentUser user) {
        return firstString(internalTokenClaims(user), "azp", "client_id", "clientId");
    }

    public String actorType(CurrentUser user) {
        return firstString(internalTokenClaims(user), "actor_type", "actorType");
    }

    private void requireBoundServiceOperation(LoyaltyProgram program, CurrentUser user, String operation) {
        String normalizedOperation = normalizeOperation(operation);
        if (!"service".equalsIgnoreCase(actorType(user))) {
            throw ForbiddenException.coded(
                    LOYALTY_ACCESS_DENIED,
                    "Loyalty runtime operation requires a trusted service actor");
        }
        String requiredScope = loyaltyScopeForOperation(normalizedOperation);
        if (!serviceHasScope(user, requiredScope)) {
            throw ForbiddenException.coded(
                    LOYALTY_ACCESS_DENIED,
                    "Missing internal loyalty operation scope: " + requiredScope);
        }
        String clientId = sourceClientId(user);
        if (clientId == null) {
            throw ForbiddenException.coded(LOYALTY_CLIENT_NOT_BOUND, "Loyalty caller is not bound to program");
        }
        LoyaltyProgramClientBinding binding = clientBindings
                .findByTenantIdAndApplicationIdAndProgramIdAndClientId(
                        program.getTenantId(), program.getApplicationId(), program.getProgramId(), clientId)
                .orElseThrow(() -> ForbiddenException.coded(
                        LOYALTY_CLIENT_NOT_BOUND,
                        "Loyalty caller is not bound to program"));
        if (!binding.active()) {
            throw ForbiddenException.coded(
                    LOYALTY_CLIENT_NOT_BOUND,
                    "Loyalty caller binding is suspended");
        }
        List<String> operations = readStringList(binding.getAllowedOperations());
        if (operations.stream().noneMatch(normalizedOperation::equalsIgnoreCase)) {
            throw ForbiddenException.coded(
                    LOYALTY_CLIENT_OPERATION_NOT_ALLOWED,
                    "Loyalty caller is not allowed to run operation: " + normalizedOperation);
        }
    }

    private boolean serviceHasScope(CurrentUser user, String requiredScope) {
        if (!"service".equalsIgnoreCase(actorType(user))) {
            return false;
        }
        Set<String> scopes = extractScopes(internalTokenClaims(user));
        return scopes.contains("*") || scopes.contains(requiredScope);
    }

    private String loyaltyScopeForOperation(String operation) {
        return switch (operation) {
            case "read" -> InternalScopes.LOYALTY_READ;
            case "earn" -> InternalScopes.LOYALTY_EARN;
            case "burn" -> InternalScopes.LOYALTY_BURN;
            case "reverse" -> InternalScopes.LOYALTY_REVERSE;
            case "adjust" -> InternalScopes.LOYALTY_ADJUST;
            case "expire" -> InternalScopes.LOYALTY_EXPIRE;
            default -> InternalScopes.LOYALTY_ADMIN;
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

    private Map<String, Object> internalTokenClaims(CurrentUser user) {
        if (user == null || user.internalToken() == null) {
            return Map.of();
        }
        try {
            Claims claims = internalJwtService.verify(user.internalToken());
            return claims;
        } catch (JwtException | IllegalArgumentException | IllegalStateException ex) {
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

    private List<String> normalizedAllowedOperations(List<String> operations) {
        if (operations == null) {
            return List.of();
        }
        return operations.stream()
                .map(this::blankToNull)
                .filter(value -> value != null)
                .map(this::normalizeOperation)
                .distinct()
                .toList();
    }

    private String normalizeOperation(String operation) {
        String normalized = blankToNull(operation);
        if (normalized == null) {
            return "admin";
        }
        normalized = normalized.toLowerCase(Locale.ROOT);
        if (!SUPPORTED_OPERATIONS.contains(normalized)) {
            throw ForbiddenException.coded(
                    LOYALTY_CLIENT_OPERATION_NOT_ALLOWED,
                    "Unsupported loyalty operation binding: " + normalized);
        }
        return normalized;
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

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? List.of() : value);
        } catch (JsonProcessingException ex) {
            throw new IllegalArgumentException("Unable to serialize loyalty client binding", ex);
        }
    }

    public String actorId(CurrentUser user) {
        if ("service".equalsIgnoreCase(actorType(user))) {
            String clientId = sourceClientId(user);
            if (clientId != null) {
                return clientId;
            }
        }
        if (user == null) {
            return null;
        }
        if (user.email() != null && !user.email().isBlank()) {
            return user.email();
        }
        return user.id() == null ? null : String.valueOf(user.id());
    }

    private String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
