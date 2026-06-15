package edu.courseflow.loyalty.service;

import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_INVALID_STATUS;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_PROGRAM_NOT_FOUND;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_TIER_INVALID_REQUEST;
import static edu.courseflow.loyalty.service.LoyaltyErrorCodes.LOYALTY_TIER_POLICY_NOT_FOUND;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.ConflictException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.loyalty.dto.LoyaltyDtos.CreateLoyaltyTierPolicyRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierPolicyDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierProgressDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierRecalculateResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierStateDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.LoyaltyTierStateQueryResponseDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.RecalculateLoyaltyTiersRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateLoyaltyTierPolicyRequestDto;
import edu.courseflow.loyalty.dto.LoyaltyDtos.UpdateLoyaltyTierPolicyStatusRequestDto;
import edu.courseflow.loyalty.model.LoyaltyAccount;
import edu.courseflow.loyalty.model.LoyaltyAuditEvent;
import edu.courseflow.loyalty.model.LoyaltyProgram;
import edu.courseflow.loyalty.model.LoyaltyTierPolicy;
import edu.courseflow.loyalty.model.LoyaltyTierState;
import edu.courseflow.loyalty.repository.LoyaltyAccountRepository;
import edu.courseflow.loyalty.repository.LoyaltyAuditEventRepository;
import edu.courseflow.loyalty.repository.LoyaltyPointsEntryRepository;
import edu.courseflow.loyalty.repository.LoyaltyProgramRepository;
import edu.courseflow.loyalty.repository.LoyaltyTierPolicyRepository;
import edu.courseflow.loyalty.repository.LoyaltyTierStateRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyTierService {

    private static final TypeReference<Map<String, Object>> MAP_TYPE = new TypeReference<>() {
    };

    private final LoyaltyTierPolicyRepository policies;
    private final LoyaltyTierStateRepository states;
    private final LoyaltyProgramRepository programs;
    private final LoyaltyAccountRepository accounts;
    private final LoyaltyPointsEntryRepository pointsEntries;
    private final LoyaltyAuditEventRepository auditEvents;
    private final LoyaltyAccessService access;
    private final ObjectMapper objectMapper;

    public LoyaltyTierService(
            LoyaltyTierPolicyRepository policies,
            LoyaltyTierStateRepository states,
            LoyaltyProgramRepository programs,
            LoyaltyAccountRepository accounts,
            LoyaltyPointsEntryRepository pointsEntries,
            LoyaltyAuditEventRepository auditEvents,
            LoyaltyAccessService access,
            ObjectMapper objectMapper) {
        this.policies = policies;
        this.states = states;
        this.programs = programs;
        this.accounts = accounts;
        this.pointsEntries = pointsEntries;
        this.auditEvents = auditEvents;
        this.access = access;
        this.objectMapper = objectMapper;
    }

    @Transactional(readOnly = true)
    public List<LoyaltyTierPolicyDto> listPolicies(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> status,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        return policies.search(
                        blankToNull(tenantId.orElse(null)),
                        blankToNull(applicationId.orElse(null)),
                        blankToNull(programId.orElse(null)),
                        normalizedStatus(status.orElse(null)),
                        PageRequest.of(0, boundedLimit(limit.orElse(50))))
                .stream()
                .map(this::policyDto)
                .toList();
    }

    @Transactional
    public LoyaltyTierPolicyDto createPolicy(CreateLoyaltyTierPolicyRequestDto request, CurrentUser user) {
        LoyaltyProgram program = requireProgram(request.tenantId(), request.applicationId(), request.programId());
        access.requireAdminAccess(program.getTenantId(), program.getApplicationId(), user);
        validatePolicyFields(request.rank(), request.qualificationPoints(), request.qualificationWindowDays(),
                request.downgradeGraceDays());
        LoyaltyTierPolicy policy = new LoyaltyTierPolicy(
                program,
                request.tierCode(),
                request.name(),
                request.rank(),
                request.qualificationPoints(),
                request.qualificationWindowDays(),
                request.downgradeGraceDays(),
                json(request.benefits()),
                actor(user));
        try {
            LoyaltyTierPolicy saved = policies.save(policy);
            audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-tier-policy",
                    "loyalty.tier_policy.created", actor(user), null, null, Map.of(
                            "programId", saved.getProgramId(),
                            "tierCode", saved.getTierCode(),
                            "rank", saved.getRank(),
                            "qualificationPoints", saved.getQualificationPoints(),
                            "qualificationWindowDays", saved.getQualificationWindowDays()));
            return policyDto(saved);
        } catch (DataIntegrityViolationException ex) {
            throw ConflictException.coded(
                    LOYALTY_TIER_INVALID_REQUEST,
                    "Tier code or rank already exists for this loyalty program");
        }
    }

    @Transactional
    public LoyaltyTierPolicyDto updatePolicy(
            UUID policyId,
            UpdateLoyaltyTierPolicyRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyTierPolicy policy = policyById(policyId);
        access.requireAdminAccess(policy.getTenantId(), policy.getApplicationId(), user);
        validatePolicyFields(request.rank(), request.qualificationPoints(), request.qualificationWindowDays(),
                request.downgradeGraceDays());
        policy.update(
                request.name(),
                request.rank(),
                request.qualificationPoints(),
                request.qualificationWindowDays(),
                request.downgradeGraceDays(),
                request.benefits() == null ? null : json(request.benefits()));
        try {
            LoyaltyTierPolicy saved = policies.save(policy);
            audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-tier-policy",
                    "loyalty.tier_policy.updated", actor(user), null, correlationId, Map.of(
                            "programId", saved.getProgramId(),
                            "tierCode", saved.getTierCode(),
                            "rank", saved.getRank(),
                            "qualificationPoints", saved.getQualificationPoints(),
                            "qualificationWindowDays", saved.getQualificationWindowDays(),
                            "downgradeGraceDays", saved.getDowngradeGraceDays()));
            return policyDto(saved);
        } catch (DataIntegrityViolationException ex) {
            throw ConflictException.coded(
                    LOYALTY_TIER_INVALID_REQUEST,
                    "Tier code or rank already exists for this loyalty program");
        }
    }

    @Transactional
    public LoyaltyTierPolicyDto updatePolicyStatus(
            UUID policyId,
            UpdateLoyaltyTierPolicyStatusRequestDto request,
            String correlationId,
            CurrentUser user) {
        LoyaltyTierPolicy policy = policyById(policyId);
        access.requireAdminAccess(policy.getTenantId(), policy.getApplicationId(), user);
        try {
            policy.changeStatus(request.status());
        } catch (IllegalArgumentException ex) {
            throw BadRequestException.coded(LOYALTY_INVALID_STATUS, ex.getMessage());
        }
        LoyaltyTierPolicy saved = policies.save(policy);
        audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-tier-policy",
                "loyalty.tier_policy.status_changed", actor(user), request.note(), correlationId, Map.of(
                        "programId", saved.getProgramId(),
                        "tierCode", saved.getTierCode(),
                        "status", saved.getStatus()));
        return policyDto(saved);
    }

    @Transactional(readOnly = true)
    public LoyaltyTierStateQueryResponseDto listStates(
            Optional<String> tenantId,
            Optional<String> applicationId,
            Optional<String> programId,
            Optional<String> profileId,
            Optional<String> tierCode,
            Optional<Integer> limit,
            CurrentUser user) {
        requireReadForScope(tenantId, applicationId, user);
        int pageSize = boundedLimit(limit.orElse(50));
        List<LoyaltyTierState> rows = states.search(
                blankToNull(tenantId.orElse(null)),
                blankToNull(applicationId.orElse(null)),
                blankToNull(programId.orElse(null)),
                blankToNull(profileId.orElse(null)),
                normalizedTierCode(tierCode.orElse(null)),
                PageRequest.of(0, pageSize + 1));
        return new LoyaltyTierStateQueryResponseDto(
                rows.stream().limit(pageSize).map(this::stateDto).toList(),
                pageSize,
                rows.size() > pageSize);
    }

    @Transactional
    public LoyaltyTierRecalculateResponseDto recalculate(
            RecalculateLoyaltyTiersRequestDto request,
            CurrentUser user) {
        requireReadForScope(Optional.ofNullable(request.tenantId()), Optional.ofNullable(request.applicationId()), user);
        if (blankToNull(request.tenantId()) != null && blankToNull(request.applicationId()) != null) {
            access.requireAdminAccess(blankToNull(request.tenantId()), blankToNull(request.applicationId()), user);
        } else {
            access.requirePlatformAdmin(user);
        }
        Instant runAt = Instant.now();
        int pageSize = boundedLimit(request.limit() == null ? 50 : request.limit());
        List<LoyaltyAccount> scopedAccounts = accounts.search(
                blankToNull(request.tenantId()),
                blankToNull(request.applicationId()),
                blankToNull(request.programId()),
                blankToNull(request.profileId()),
                "ACTIVE",
                PageRequest.of(0, pageSize));
        if (request.accountId() != null) {
            scopedAccounts = accounts.findByIdForUpdate(request.accountId()).stream().toList();
        }
        List<LoyaltyTierStateDto> items = new ArrayList<>();
        int changed = 0;
        for (LoyaltyAccount account : scopedAccounts) {
            LoyaltyTierState state = evaluateAccountInternal(
                    account,
                    actor(user),
                    request.reason(),
                    request.correlationId(),
                    runAt);
            if (state.getCurrentPeriodStartedAt().equals(runAt)) {
                changed += 1;
            }
            items.add(stateDto(state));
        }
        return new LoyaltyTierRecalculateResponseDto(runAt, scopedAccounts.size(), changed, items);
    }

    @Transactional
    public LoyaltyTierStateDto evaluateAfterPointsMutation(
            LoyaltyAccount account,
            String actorId,
            String reason,
            String correlationId) {
        return stateDto(evaluateAccountInternal(account, actorId, reason, correlationId, Instant.now()));
    }

    @Transactional(readOnly = true)
    public LoyaltyTierProgressDto progressForAccount(LoyaltyAccount account, Instant now) {
        LoyaltyTierState existing = states.findByAccountId(account.getId()).orElse(null);
        if (existing != null && existing.getEvaluatedAt() != null) {
            return progressDto(existing);
        }
        List<LoyaltyTierPolicy> activePolicies = activePolicies(account);
        LoyaltyTierPolicy eligible = highestEligible(account, activePolicies, now);
        LoyaltyTierPolicy next = nextTier(activePolicies, eligible == null ? 0 : eligible.getRank());
        long nextPoints = next == null ? 0L : qualifyingPoints(account, next, now);
        return progressDto(null, account, eligible, next, nextPoints, now);
    }

    private LoyaltyTierState evaluateAccountInternal(
            LoyaltyAccount account,
            String actorId,
            String reason,
            String correlationId,
            Instant now) {
        List<LoyaltyTierPolicy> activePolicies = activePolicies(account);
        LoyaltyTierState state = states.findByAccountIdForUpdate(account.getId())
                .orElseGet(() -> states.save(new LoyaltyTierState(account, now)));
        LoyaltyTierPolicy previousPolicy = state.getTierPolicyId() == null
                ? null
                : policies.findById(state.getTierPolicyId()).orElse(null);
        LoyaltyTierPolicy eligible = highestEligible(account, activePolicies, now);
        LoyaltyTierPolicy current = resolveCurrentTier(state, previousPolicy, eligible, now);
        long currentQualificationPoints = current == null ? 0L : qualifyingPoints(account, current, now);
        Instant windowStart = current == null ? null : now.minus(current.getQualificationWindowDays(), ChronoUnit.DAYS);
        Integer windowDays = current == null ? null : current.getQualificationWindowDays();
        Instant graceUntil = resolveGraceUntil(state, previousPolicy, eligible, current, now);
        boolean changed = state.applyTier(
                current,
                currentQualificationPoints,
                windowDays,
                windowStart,
                current == null ? null : now,
                graceUntil,
                now);
        LoyaltyTierPolicy next = nextTier(activePolicies, current == null ? 0 : current.getRank());
        long nextPoints = next == null ? 0L : qualifyingPoints(account, next, now);
        state.applyNextTier(next, nextPoints, null);
        LoyaltyTierState saved = states.save(state);
        if (changed) {
            audit(saved.getTenantId(), saved.getApplicationId(), saved.getId().toString(), "loyalty-tier-state",
                    "loyalty.tier.changed", actorId, reason, correlationId, Map.of(
                            "accountId", saved.getAccountId().toString(),
                            "profileId", saved.getProfileId(),
                            "previousTierCode", previousPolicy == null ? "BASE" : previousPolicy.getTierCode(),
                            "currentTierCode", saved.getTierCode(),
                            "currentTierRank", saved.getTierRank(),
                            "qualificationPoints", saved.getQualificationPoints(),
                            "graceUntil", saved.getGraceUntil() == null ? "" : saved.getGraceUntil().toString()));
        }
        return saved;
    }

    private LoyaltyTierPolicy resolveCurrentTier(
            LoyaltyTierState state,
            LoyaltyTierPolicy previousPolicy,
            LoyaltyTierPolicy eligible,
            Instant now) {
        int eligibleRank = eligible == null ? 0 : eligible.getRank();
        if (eligibleRank >= state.getTierRank()) {
            return eligible;
        }
        if (previousPolicy == null || !"ACTIVE".equals(previousPolicy.getStatus())) {
            return eligible;
        }
        Instant existingGrace = state.getGraceUntil();
        if (existingGrace != null && !existingGrace.isBefore(now)) {
            return previousPolicy;
        }
        int graceDays = previousPolicy.getDowngradeGraceDays();
        if (graceDays > 0 && existingGrace == null) {
            return previousPolicy;
        }
        return eligible;
    }

    private Instant resolveGraceUntil(
            LoyaltyTierState state,
            LoyaltyTierPolicy previousPolicy,
            LoyaltyTierPolicy eligible,
            LoyaltyTierPolicy current,
            Instant now) {
        int eligibleRank = eligible == null ? 0 : eligible.getRank();
        if (current == null || previousPolicy == null || current.getRank() <= eligibleRank) {
            return null;
        }
        if (state.getGraceUntil() != null && !state.getGraceUntil().isBefore(now)) {
            return state.getGraceUntil();
        }
        int graceDays = previousPolicy.getDowngradeGraceDays();
        return graceDays <= 0 ? null : now.plus(graceDays, ChronoUnit.DAYS);
    }

    private LoyaltyTierPolicy highestEligible(LoyaltyAccount account, List<LoyaltyTierPolicy> activePolicies, Instant now) {
        LoyaltyTierPolicy highest = null;
        for (LoyaltyTierPolicy policy : activePolicies) {
            long points = qualifyingPoints(account, policy, now);
            if (points >= policy.getQualificationPoints()
                    && (highest == null || policy.getRank() > highest.getRank())) {
                highest = policy;
            }
        }
        return highest;
    }

    private LoyaltyTierPolicy nextTier(List<LoyaltyTierPolicy> activePolicies, int currentRank) {
        return activePolicies.stream()
                .filter(policy -> policy.getRank() > currentRank)
                .min(Comparator.comparingInt(LoyaltyTierPolicy::getRank))
                .orElse(null);
    }

    private long qualifyingPoints(LoyaltyAccount account, LoyaltyTierPolicy policy, Instant now) {
        Instant from = now.minus(policy.getQualificationWindowDays(), ChronoUnit.DAYS);
        return pointsEntries.qualifyingPositivePoints(account.getId(), from, now);
    }

    private List<LoyaltyTierPolicy> activePolicies(LoyaltyAccount account) {
        return policies.findActiveByProgram(account.getProgramUuid());
    }

    private LoyaltyProgram requireProgram(String tenantId, String applicationId, String programId) {
        return programs.findByTenantIdAndApplicationIdAndProgramId(
                        normalize(tenantId), normalize(applicationId), normalize(programId))
                .orElseThrow(() -> NotFoundException.coded(LOYALTY_PROGRAM_NOT_FOUND, "Loyalty program not found"));
    }

    private LoyaltyTierPolicy policyById(UUID policyId) {
        return policies.findById(policyId)
                .orElseThrow(() -> NotFoundException.coded(
                        LOYALTY_TIER_POLICY_NOT_FOUND,
                        "Loyalty tier policy not found"));
    }

    private void validatePolicyFields(
            Integer rank,
            Long qualificationPoints,
            Integer qualificationWindowDays,
            Integer downgradeGraceDays) {
        if (rank != null && rank <= 0) {
            throw BadRequestException.coded(LOYALTY_TIER_INVALID_REQUEST, "Tier rank must be positive");
        }
        if (qualificationPoints != null && qualificationPoints < 0) {
            throw BadRequestException.coded(LOYALTY_TIER_INVALID_REQUEST, "Qualification points cannot be negative");
        }
        if (qualificationWindowDays != null && qualificationWindowDays <= 0) {
            throw BadRequestException.coded(LOYALTY_TIER_INVALID_REQUEST, "Qualification window must be positive");
        }
        if (downgradeGraceDays != null && downgradeGraceDays < 0) {
            throw BadRequestException.coded(LOYALTY_TIER_INVALID_REQUEST, "Downgrade grace cannot be negative");
        }
    }

    private LoyaltyTierPolicyDto policyDto(LoyaltyTierPolicy policy) {
        return new LoyaltyTierPolicyDto(
                policy.getId(),
                policy.getProgramUuid(),
                policy.getTenantId(),
                policy.getApplicationId(),
                policy.getProgramId(),
                policy.getTierCode(),
                policy.getName(),
                policy.getRank(),
                policy.getStatus(),
                policy.getQualificationPoints(),
                policy.getQualificationWindowDays(),
                policy.getDowngradeGraceDays(),
                readMap(policy.getBenefitsJson()),
                policy.getCreatedBy(),
                policy.getCreatedAt(),
                policy.getUpdatedAt());
    }

    private LoyaltyTierStateDto stateDto(LoyaltyTierState state) {
        return new LoyaltyTierStateDto(
                state.getId(),
                state.getAccountId(),
                state.getProgramUuid(),
                state.getTenantId(),
                state.getApplicationId(),
                state.getProgramId(),
                state.getProfileId(),
                progressDto(state),
                state.getUpdatedAt());
    }

    private LoyaltyTierProgressDto progressDto(LoyaltyTierState state) {
        return new LoyaltyTierProgressDto(
                state.getId(),
                state.getAccountId(),
                state.getTierPolicyId(),
                state.getTierCode(),
                state.getTierName(),
                state.getTierRank(),
                state.getQualificationPoints(),
                state.getQualificationWindowDays(),
                state.getQualificationWindowStartedAt(),
                state.getQualificationWindowEndsAt(),
                state.getCurrentPeriodStartedAt(),
                state.getQualifiedAt(),
                state.getGraceUntil(),
                state.getNextTierPolicyId(),
                state.getNextTierCode(),
                state.getNextTierName(),
                state.getNextTierRank(),
                state.getNextTierPointsRequired(),
                state.getPointsToNext(),
                state.getEvaluatedAt());
    }

    private LoyaltyTierProgressDto progressDto(
            LoyaltyTierState state,
            LoyaltyAccount account,
            LoyaltyTierPolicy current,
            LoyaltyTierPolicy next,
            long nextPoints,
            Instant now) {
        return new LoyaltyTierProgressDto(
                state == null ? null : state.getId(),
                account.getId(),
                current == null ? null : current.getId(),
                current == null ? "BASE" : current.getTierCode(),
                current == null ? "Base" : current.getName(),
                current == null ? 0 : current.getRank(),
                current == null ? 0L : qualifyingPoints(account, current, now),
                current == null ? null : current.getQualificationWindowDays(),
                current == null ? null : now.minus(current.getQualificationWindowDays(), ChronoUnit.DAYS),
                current == null ? null : now,
                state == null ? null : state.getCurrentPeriodStartedAt(),
                state == null ? null : state.getQualifiedAt(),
                state == null ? null : state.getGraceUntil(),
                next == null ? null : next.getId(),
                next == null ? null : next.getTierCode(),
                next == null ? null : next.getName(),
                next == null ? null : next.getRank(),
                next == null ? null : next.getQualificationPoints(),
                next == null ? null : Math.max(0L, next.getQualificationPoints() - nextPoints),
                state == null ? now : state.getEvaluatedAt());
    }

    private void audit(String tenantId, String applicationId, String aggregateId, String aggregateType,
                       String action, String actorId, String note, String correlationId, Map<String, Object> payload) {
        auditEvents.save(new LoyaltyAuditEvent(
                tenantId,
                applicationId,
                aggregateId,
                aggregateType,
                action,
                actorId,
                note,
                correlationId,
                json(payload)));
    }

    private void requireReadForScope(Optional<String> tenantId, Optional<String> applicationId, CurrentUser user) {
        String tenant = blankToNull(tenantId.orElse(null));
        String application = blankToNull(applicationId.orElse(null));
        if (tenant != null && application != null) {
            access.requireReadAccess(tenant, application, user);
            return;
        }
        access.requirePlatformAdmin(user);
    }

    private int boundedLimit(int requested) {
        return Math.max(1, Math.min(requested, 200));
    }

    private String normalizedStatus(String status) {
        String value = blankToNull(status);
        return value == null ? null : value.toUpperCase(Locale.ROOT);
    }

    private String normalizedTierCode(String tierCode) {
        String value = blankToNull(tierCode);
        return value == null ? null : value.toUpperCase(Locale.ROOT);
    }

    private String blankToNull(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        return value.trim();
    }

    private String normalize(String value) {
        return value == null ? "" : value.trim();
    }

    private String actor(CurrentUser user) {
        if (user == null || user.id() == null) {
            return "system";
        }
        return String.valueOf(user.id());
    }

    private Map<String, Object> readMap(String json) {
        if (json == null || json.isBlank()) {
            return Map.of();
        }
        try {
            return objectMapper.readValue(json, MAP_TYPE);
        } catch (JsonProcessingException ex) {
            return Map.of("_raw", json);
        }
    }

    private String json(Object value) {
        try {
            return objectMapper.writeValueAsString(value == null ? Map.of() : value);
        } catch (JsonProcessingException ex) {
            return "{}";
        }
    }
}
