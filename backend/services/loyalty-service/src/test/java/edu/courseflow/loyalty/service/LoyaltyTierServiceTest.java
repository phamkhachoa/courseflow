package edu.courseflow.loyalty.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
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
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class LoyaltyTierServiceTest {

    @Mock
    private LoyaltyTierPolicyRepository policies;
    @Mock
    private LoyaltyTierStateRepository states;
    @Mock
    private LoyaltyProgramRepository programs;
    @Mock
    private LoyaltyAccountRepository accounts;
    @Mock
    private LoyaltyPointsEntryRepository pointsEntries;
    @Mock
    private LoyaltyAuditEventRepository auditEvents;
    @Mock
    private LoyaltyAccessService access;

    private LoyaltyTierService service;
    private LoyaltyProgram program;
    private LoyaltyAccount account;
    private LoyaltyTierPolicy silver;
    private LoyaltyTierPolicy gold;

    @BeforeEach
    void setUp() {
        service = new LoyaltyTierService(
                policies,
                states,
                programs,
                accounts,
                pointsEntries,
                auditEvents,
                access,
                new ObjectMapper().findAndRegisterModules());
        program = new LoyaltyProgram("courseflow", "lms", "default", "Default points", "POINT", false, 365, "test");
        account = new LoyaltyAccount(program, "profile-1");
        silver = new LoyaltyTierPolicy(program, "SILVER", "Silver", 1, 500, 365, 30, "{}", "test");
        gold = new LoyaltyTierPolicy(program, "GOLD", "Gold", 2, 1_000, 365, 7, "{}", "test");
    }

    @Test
    void evaluateAfterPointsMutationUpgradesAndComputesNextProgress() {
        when(policies.findActiveByProgram(account.getProgramUuid())).thenReturn(List.of(silver, gold));
        when(states.findByAccountIdForUpdate(account.getId())).thenReturn(Optional.empty());
        when(states.save(any(LoyaltyTierState.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(pointsEntries.qualifyingPositivePoints(eq(account.getId()), any(), any()))
                .thenReturn(600L, 600L, 600L, 600L);

        var state = service.evaluateAfterPointsMutation(account, "operator-1", "earn posted", "corr-1");

        assertThat(state.progress().currentTierCode()).isEqualTo("SILVER");
        assertThat(state.progress().currentTierRank()).isEqualTo(1);
        assertThat(state.progress().qualificationPoints()).isEqualTo(600);
        assertThat(state.progress().nextTierCode()).isEqualTo("GOLD");
        assertThat(state.progress().pointsToNext()).isEqualTo(400);
        verify(auditEvents).save(any(LoyaltyAuditEvent.class));
    }

    @Test
    void evaluateAfterPointsMutationKeepsCurrentTierDuringDowngradeGrace() {
        Instant previousEvaluation = Instant.now().minusSeconds(600);
        LoyaltyTierState existing = new LoyaltyTierState(account, previousEvaluation);
        existing.applyTier(gold, 1_200, 365, previousEvaluation.minusSeconds(31_536_000), previousEvaluation, null, previousEvaluation);
        existing.applyNextTier(null, 0, null);

        when(policies.findActiveByProgram(account.getProgramUuid())).thenReturn(List.of(silver, gold));
        when(states.findByAccountIdForUpdate(account.getId())).thenReturn(Optional.of(existing));
        when(policies.findById(gold.getId())).thenReturn(Optional.of(gold));
        when(states.save(any(LoyaltyTierState.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(pointsEntries.qualifyingPositivePoints(eq(account.getId()), any(), any()))
                .thenReturn(600L, 600L, 600L);

        var state = service.evaluateAfterPointsMutation(account, "operator-1", "window moved", "corr-1");

        assertThat(state.progress().currentTierCode()).isEqualTo("GOLD");
        assertThat(state.progress().currentTierRank()).isEqualTo(2);
        assertThat(state.progress().graceUntil()).isNotNull();
        assertThat(state.progress().qualificationPoints()).isEqualTo(600);
        verifyNoInteractions(auditEvents);
    }
}
