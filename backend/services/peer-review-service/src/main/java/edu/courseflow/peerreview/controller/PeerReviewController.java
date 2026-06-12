package edu.courseflow.peerreview.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.peerreview.service.PeerReviewService;
import edu.courseflow.peerreview.web.Authz;
import edu.courseflow.peerreview.dto.AssignReviewRequestDto;
import edu.courseflow.peerreview.dto.FinalizePeerReviewRequestDto;
import edu.courseflow.peerreview.dto.PeerReviewResultDto;
import edu.courseflow.peerreview.dto.PeerReviewSettingDto;
import edu.courseflow.peerreview.dto.ReviewAssignmentDto;
import edu.courseflow.peerreview.dto.ReviewSubmissionDto;
import edu.courseflow.peerreview.dto.SubmitReviewRequestDto;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/internal/peer-reviews")
public class PeerReviewController {
    private final PeerReviewService peerReviews;

    public PeerReviewController(PeerReviewService peerReviews) {
        this.peerReviews = peerReviews;
    }

    @GetMapping("/settings/{assignmentId}")
    public PeerReviewSettingDto setting(@PathVariable UUID assignmentId, CurrentUser user) {
        Authz.callerId(user);
        return peerReviews.setting(assignmentId);
    }

    @PostMapping("/assignments")
    public ReviewAssignmentDto assign(@Valid @RequestBody AssignReviewRequestDto request, CurrentUser user) {
        // Assigning reviewers to submissions is an instructor/admin action.
        Authz.requireStaff(user);
        return peerReviews.assign(request);
    }

    @GetMapping("/review-assignments/mine")
    public List<ReviewAssignmentDto> mine(CurrentUser user) {
        return peerReviews.assignedToReviewer(Authz.callerId(user));
    }

    @PostMapping("/review-assignments/{reviewAssignmentId}/submit")
    public ReviewSubmissionDto submit(@PathVariable UUID reviewAssignmentId,
                                     @Valid @RequestBody SubmitReviewRequestDto request, CurrentUser user) {
        // Only the assigned reviewer (or staff) may submit a review for this assignment.
        Authz.requireSelfOrStaff(user, peerReviews.reviewerOf(reviewAssignmentId));
        return peerReviews.submit(reviewAssignmentId, request);
    }

    @PostMapping("/results/finalize")
    public PeerReviewResultDto finalizeScore(@Valid @RequestBody FinalizePeerReviewRequestDto request,
            CurrentUser user) {
        // Finalizing is staff-only; the score is computed server-side and the actor is the caller.
        Authz.requireStaff(user);
        return peerReviews.finalizeScore(request, Authz.callerId(user));
    }
}
