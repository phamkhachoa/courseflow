package edu.courseflow.promotion.service;

import edu.courseflow.promotion.dto.PromotionDtos.ActionCatalogItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.CatalogParameterDto;
import edu.courseflow.promotion.dto.PromotionDtos.EffectCatalogItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.IdempotencyContractDto;
import edu.courseflow.promotion.dto.PromotionDtos.IncentiveCatalogDto;
import edu.courseflow.promotion.dto.PromotionDtos.ReasonCodeCatalogItemDto;
import edu.courseflow.promotion.dto.PromotionDtos.RuleCatalogItemDto;
import java.util.List;
import org.springframework.stereotype.Service;

@Service
public class IncentiveCatalogService {

    private static final String CATALOG_VERSION = "incentive-contract-v1";
    private static final String FACT_CONTRACT_VERSION = "generic-commerce-facts-v1";

    public IncentiveCatalogDto catalog() {
        return new IncentiveCatalogDto(
                CATALOG_VERSION,
                FACT_CONTRACT_VERSION,
                rules(),
                actions(),
                effects(),
                reasonCodes(),
                idempotencyContract(),
                List.of(
                        "The engine is generic incentive infrastructure; source systems resolve facts and pass them as context.",
                        "Current fact contract supports commerce-like transaction facts, but campaign rules use typed generic attributes.",
                        "Do not send raw coupon codes to audit/log/reporting surfaces; runtime request snapshots store fingerprints/masks only.",
                        "Loyalty points, tiers, rewards, expiry and manual adjustment belong to a separate loyalty bounded context."));
    }

    private List<RuleCatalogItemDto> rules() {
        return List.of(
                new RuleCatalogItemDto(
                        "MIN_ORDER_AMOUNT",
                        1,
                        "Matches when transaction subtotal reaches a configured amount and optional currency.",
                        List.of(
                                parameter("amount", "decimal", true, "Minimum subtotal before incentive.", List.of()),
                                parameter("currency", "string", false, "ISO currency expected by this rule.", List.of())),
                        List.of("transaction.subtotal", "currency"),
                        "RULE_MIN_ORDER_AMOUNT_NOT_MATCHED"),
                new RuleCatalogItemDto(
                        "PROFILE_SEGMENT",
                        1,
                        "Matches when request attributes contain one of the configured profile segments.",
                        List.of(
                                parameter("segment", "string", false, "Single accepted segment.", List.of()),
                                parameter("segments", "string[]", false, "Accepted segments.", List.of())),
                        List.of("attributes.segment"),
                        "RULE_PROFILE_SEGMENT_NOT_MATCHED"),
                new RuleCatalogItemDto(
                        "ITEM_CATEGORY_INCLUDE",
                        1,
                        "Matches when at least one item has an included category attribute.",
                        List.of(
                                parameter("category", "string", false, "Single accepted item category.", List.of()),
                                parameter("categories", "string[]", false, "Accepted item categories.", List.of())),
                        List.of("items[].attributes.category"),
                        "RULE_ITEM_CATEGORY_INCLUDE_NOT_MATCHED"),
                new RuleCatalogItemDto(
                        "CHANNEL_MATCH",
                        1,
                        "Matches when the runtime channel is in the configured allow-list.",
                        List.of(
                                parameter("channel", "string", false, "Single accepted channel.", List.of()),
                                parameter("channels", "string[]", false, "Accepted channels.", List.of("WEB", "MOBILE", "POS", "API"))),
                        List.of("channel"),
                        "RULE_CHANNEL_MATCH_NOT_MATCHED"));
    }

    private List<ActionCatalogItemDto> actions() {
        return List.of(
                new ActionCatalogItemDto(
                        "ORDER_PERCENT_OFF",
                        1,
                        "DISCOUNT",
                        "Emits a money discount against the order subtotal, optionally capped.",
                        List.of(
                                parameter("percent", "decimal", true, "Percent between 0 and 100.", List.of()),
                                parameter("maxAmount", "decimal", false, "Maximum money discount.", List.of())),
                        List.of("ORDER_PERCENT_OFF")),
                new ActionCatalogItemDto(
                        "ORDER_FIXED_OFF",
                        1,
                        "DISCOUNT",
                        "Emits a fixed money discount against the order subtotal.",
                        List.of(parameter("amount", "decimal", true, "Money amount to discount.", List.of())),
                        List.of("ORDER_FIXED_OFF")),
                new ActionCatalogItemDto(
                        "LINE_FIXED_OFF",
                        1,
                        "DISCOUNT",
                        "Emits a fixed money discount against the first eligible item line.",
                        List.of(
                                parameter("amount", "decimal", true, "Money amount to discount.", List.of()),
                                parameter("category", "string", false, "Optional item category filter.", List.of()),
                                parameter("categories", "string[]", false, "Optional item category filters.", List.of())),
                        List.of("LINE_FIXED_OFF")),
                new ActionCatalogItemDto(
                        "FREE_SHIPPING",
                        1,
                        "DISCOUNT",
                        "Emits a shipping discount when shipping amount is present and positive.",
                        List.of(),
                        List.of("FREE_SHIPPING")),
                new ActionCatalogItemDto(
                        "LOYALTY_POINTS_EARN",
                        1,
                        "POINTS_EARN_INTENT",
                        "Emits a loyalty points earn intent. Promotion never mutates loyalty balances directly.",
                        List.of(
                                parameter("programId", "string", true, "Loyalty program id to credit after redemption commit.", List.of()),
                                parameter("points", "number", true, "Number of loyalty points to earn.", List.of())),
                        List.of("LOYALTY_POINTS_EARN")));
    }

    private List<EffectCatalogItemDto> effects() {
        return List.of(
                new EffectCatalogItemDto(
                        "DISCOUNT",
                        "MONEY",
                        List.of("ORDER_PERCENT_OFF", "ORDER_FIXED_OFF", "LINE_FIXED_OFF", "FREE_SHIPPING"),
                        List.of("ORDER", "ITEM", "SHIPPING"),
                        "A monetary reduction that the source application applies in its own domain."),
                new EffectCatalogItemDto(
                        "CREDIT",
                        "MONEY",
                        List.of(),
                        List.of("ACCOUNT", "PROFILE"),
                        "Reserved for future generic stored credit effects."),
                new EffectCatalogItemDto(
                        "ENTITLEMENT",
                        "COUNT",
                        List.of(),
                        List.of("PROFILE", "RESOURCE"),
                        "Reserved for future access or entitlement effects."),
                new EffectCatalogItemDto(
                        "POINTS_EARN_INTENT",
                        "POINT",
                        List.of("LOYALTY_POINTS_EARN"),
                        List.of("LOYALTY_ACCOUNT"),
                        "Portable intent emitted after campaign decision; loyalty-service consumes and applies it idempotently."));
    }

    private List<ReasonCodeCatalogItemDto> reasonCodes() {
        return List.of(
                reason("ELIGIBLE", "decision", false, "At least one campaign matched and emitted effects."),
                reason("NO_ELIGIBLE_INCENTIVE", "decision", true, "No active published campaign produced a usable effect."),
                reason("CURRENCY_NOT_MATCHED", "decision", true, "Campaign currency and request currency differ."),
                reason("RULES_NOT_MATCHED", "decision", true, "No configured rule set matched the request facts."),
                reason("NO_EFFECTS", "decision", true, "Rules matched but actions emitted no positive usable effects."),
                reason("QUOTA_EXHAUSTED", "quota", true, "Campaign or coupon quota is exhausted."),
                reason("RESERVED", "reservation", false, "Incentive reservation was created and quota was held."),
                reason("RESERVATION_EXPIRED", "reservation", true, "Reservation expired before commit/cancel."),
                reason("RESERVATION_CANCELLED", "reservation", true, "Reservation was cancelled before commit."),
                reason("COMMITTED", "redemption", false, "Reservation commit created a redemption."),
                reason("CANCELLED", "reservation", false, "Reservation cancellation completed."),
                reason("ALREADY_COMMITTED", "idempotency", false, "Reservation was already committed."),
                reason("ALREADY_CANCELLED", "idempotency", false, "Reservation was already cancelled."),
                reason("ALREADY_EXPIRED", "idempotency", false, "Reservation was already expired."),
                reason("IDEMPOTENCY_REPLAY", "idempotency", false, "Operation returned a stored idempotent response."),
                reason("ALREADY_REVERSED", "idempotency", false, "Redemption was already reversed."),
                reason("REVERSED", "redemption", false, "Redemption reversal completed."));
    }

    private IdempotencyContractDto idempotencyContract() {
        return new IdempotencyContractDto(
                "body-or-header",
                "Idempotency-Key",
                List.of("ReserveIncentiveRequestDto.idempotencyKey",
                        "CommitReservationRequestDto.idempotencyKey",
                        "CancelReservationRequestDto.idempotencyKey",
                        "ReverseRedemptionRequestDto.idempotencyKey",
                        "CouponImportDryRunRequestDto.idempotencyKey"),
                "PT168H",
                "Same key and same request hash returns the stored response without re-running the operation.",
                "Same key and different request hash returns conflict.");
    }

    private CatalogParameterDto parameter(String name, String type, boolean required, String description,
                                          List<String> allowedValues) {
        return new CatalogParameterDto(name, type, required, description, allowedValues);
    }

    private ReasonCodeCatalogItemDto reason(String code, String category, boolean terminal, String description) {
        return new ReasonCodeCatalogItemDto(code, category, terminal, description);
    }
}
