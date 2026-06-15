package edu.courseflow.loyalty.service;

import edu.courseflow.loyalty.model.LoyaltyPromotionPointEffect;
import edu.courseflow.loyalty.repository.LoyaltyPromotionPointEffectRepository;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class LoyaltyPromotionPointEffectService {

    private final LoyaltyPromotionPointEffectRepository effects;

    public LoyaltyPromotionPointEffectService(LoyaltyPromotionPointEffectRepository effects) {
        this.effects = effects;
    }

    @Transactional
    public void recordExpectedEffect(LoyaltyPromotionPointEffect effect) {
        if (effects.findBySourceEventTypeAndEventIdAndEffectIdAndExpectedEntryType(
                        effect.getSourceEventType(),
                        effect.getEventId(),
                        effect.getEffectId(),
                        effect.getExpectedEntryType())
                .isPresent()) {
            return;
        }
        try {
            effects.save(effect);
        } catch (DataIntegrityViolationException ignored) {
            // Another consumer thread recorded the same expectation first; the unique key is enough.
        }
    }
}
