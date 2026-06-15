package edu.courseflow.outboxrelay.controller;

import edu.courseflow.commonlibrary.constants.GatewayHeaders;
import edu.courseflow.commonlibrary.exception.ForbiddenException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalQueryResponseDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalRequestDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterApprovalReviewRequestDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterActionRequestDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterActionResponseDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterDetailDto;
import edu.courseflow.outboxrelay.dto.OutboxRelayDtos.DeadLetterQueryResponseDto;
import edu.courseflow.outboxrelay.relay.DeadLetterService;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/outbox/dead-letters")
public class DeadLetterAdminController {

    private final DeadLetterService deadLetters;

    public DeadLetterAdminController(DeadLetterService deadLetters) {
        this.deadLetters = deadLetters;
    }

    @GetMapping
    public DeadLetterQueryResponseDto search(
            @RequestParam(required = false) String status,
            @RequestParam(required = false) String service,
            @RequestParam(required = false) String eventType,
            @RequestParam(required = false) String aggregateId,
            @RequestParam(required = false) String payloadHash,
            @RequestParam(required = false) Integer limit,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.search(status, service, eventType, aggregateId, payloadHash, limit);
    }

    @GetMapping("/{id}")
    public DeadLetterDetailDto get(@PathVariable UUID id, CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.get(id);
    }

    @GetMapping("/{id}/approvals")
    public DeadLetterApprovalQueryResponseDto approvals(
            @PathVariable UUID id,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Integer limit,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.approvals(id, status, limit);
    }

    @PostMapping("/{id}/approvals")
    public DeadLetterApprovalDto requestApproval(
            @PathVariable UUID id,
            @RequestBody DeadLetterApprovalRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.requestApproval(id, request, actorId(user), correlationId);
    }

    @PostMapping("/approvals/{approvalId}:approve")
    public DeadLetterApprovalDto approveApproval(
            @PathVariable UUID approvalId,
            @RequestBody DeadLetterApprovalReviewRequestDto request,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.approveApproval(approvalId, request, actorId(user));
    }

    @PostMapping("/approvals/{approvalId}:reject")
    public DeadLetterApprovalDto rejectApproval(
            @PathVariable UUID approvalId,
            @RequestBody DeadLetterApprovalReviewRequestDto request,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.rejectApproval(approvalId, request, actorId(user));
    }

    @PostMapping("/{id}:replay")
    public DeadLetterActionResponseDto replay(
            @PathVariable UUID id,
            @RequestBody(required = false) DeadLetterActionRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.replay(id, request, actorId(user), correlationId);
    }

    @PostMapping("/{id}:discard")
    public DeadLetterActionResponseDto discard(
            @PathVariable UUID id,
            @RequestBody(required = false) DeadLetterActionRequestDto request,
            @RequestHeader(value = GatewayHeaders.CORRELATION_ID, required = false) String correlationId,
            CurrentUser user) {
        requirePlatformAdmin(user);
        return deadLetters.discard(id, request, actorId(user), correlationId);
    }

    private void requirePlatformAdmin(CurrentUser user) {
        if (user == null || user.id() == null || !user.hasPlatformRole("ADMIN")) {
            throw new ForbiddenException("Requires platform ADMIN role");
        }
    }

    private String actorId(CurrentUser user) {
        if (user == null) {
            return null;
        }
        if (user.id() != null) {
            return user.id().toString();
        }
        return user.email();
    }
}
