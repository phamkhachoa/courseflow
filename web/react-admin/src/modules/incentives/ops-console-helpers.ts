import type { LoyaltyInboundDeadLetterFilters, OutboxDeadLetterFilters } from "./types";

type OpsDltFilterInput = {
  dltPayloadHash?: string;
  outboxService?: string;
  outboxEventType?: string;
  limit: number;
};

export function isOpenDeadLetterStatus(status?: string | null) {
  return !["REPLAYED", "DISCARDED", "RESOLVED"].includes(status ?? "");
}

export function isActionableDeadLetterStatus(status?: string | null) {
  return status === "OPEN" || status === "FAILED";
}

export function loyaltyDltOpsFilters(input: Pick<OpsDltFilterInput, "dltPayloadHash" | "limit">): LoyaltyInboundDeadLetterFilters {
  return {
    payloadHash: input.dltPayloadHash,
    limit: input.limit
  };
}

export function outboxDltOpsFilters(input: OpsDltFilterInput, aggregateId?: string): OutboxDeadLetterFilters {
  return {
    service: input.outboxService,
    eventType: input.outboxEventType,
    aggregateId,
    payloadHash: input.dltPayloadHash,
    limit: input.limit
  };
}
