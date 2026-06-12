package edu.courseflow.portfolio.controller;

import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.portfolio.dto.PortfolioDtos.AddEvaluationRequestDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.AddLearningEvidenceRequestDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDetailDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.PortfolioSummaryDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.UpdateEvidenceRequestDto;
import edu.courseflow.portfolio.service.PortfolioService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Optional;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PortfolioController {

    private static final String ROLE_ADMIN = "ADMIN";
    private static final String ROLE_INSTRUCTOR = "INSTRUCTOR";

    private final PortfolioService portfolios;

    public PortfolioController(PortfolioService portfolios) {
        this.portfolios = portfolios;
    }

    @GetMapping("/internal/portfolios/students/{studentId}/evidence")
    public List<LearningEvidenceDto> listEvidence(@PathVariable String studentId,
                                                  @RequestParam Optional<String> courseId,
                                                  CurrentUser user) {
        if (isSelfOrAdmin(user, studentId)) {
            return portfolios.listEvidence(studentId, courseId);
        }
        requireStaff(user);
        return portfolios.listEvidenceVisibleToInstructor(studentId, courseId);
    }

    @PostMapping("/internal/portfolios/students/{studentId}/evidence")
    public LearningEvidenceDto addEvidence(@PathVariable String studentId,
                                           @Valid @RequestBody AddLearningEvidenceRequestDto request,
                                           CurrentUser user) {
        requireSelfOrStaff(user, studentId);
        if (!isSelfOrAdmin(user, studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only the student or ADMIN may add private evidence");
        }
        return portfolios.addEvidence(studentId, request);
    }

    @GetMapping("/internal/portfolios/students/{studentId}/evidence/{evidenceId}")
    public LearningEvidenceDetailDto getEvidence(@PathVariable String studentId,
                                                  @PathVariable String evidenceId,
                                                  CurrentUser user) {
        if (isSelfOrAdmin(user, studentId)) {
            return portfolios.getEvidence(studentId, evidenceId);
        }
        requireStaff(user);
        LearningEvidenceDetailDto evidence = portfolios.getEvidence(studentId, evidenceId);
        requireInstructorVisible(evidence);
        return evidence;
    }

    @PutMapping("/internal/portfolios/students/{studentId}/evidence/{evidenceId}")
    public LearningEvidenceDetailDto updateEvidence(@PathVariable String studentId,
                                                     @PathVariable String evidenceId,
                                                     @Valid @RequestBody UpdateEvidenceRequestDto req,
                                                     CurrentUser user) {
        if (!isSelfOrAdmin(user, studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only the student or ADMIN may update evidence");
        }
        return portfolios.updateEvidence(studentId, evidenceId, req);
    }

    @DeleteMapping("/internal/portfolios/students/{studentId}/evidence/{evidenceId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteEvidence(@PathVariable String studentId, @PathVariable String evidenceId,
                               CurrentUser user) {
        if (!isSelfOrAdmin(user, studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only the student or ADMIN may delete evidence");
        }
        portfolios.deleteEvidence(studentId, evidenceId);
    }

    @PostMapping("/internal/portfolios/students/{studentId}/evidence/{evidenceId}/evaluate")
    public LearningEvidenceDetailDto addEvaluation(@PathVariable String studentId,
                                                    @PathVariable String evidenceId,
                                                    @Valid @RequestBody AddEvaluationRequestDto req,
                                                    CurrentUser user) {
        requireStaff(user);
        if (!user.hasRole(ROLE_ADMIN)) {
            requireInstructorVisible(portfolios.getEvidence(studentId, evidenceId));
        }
        AddEvaluationRequestDto trusted = new AddEvaluationRequestDto(
                callerId(user),
                user.role() == null ? ROLE_INSTRUCTOR : user.role(),
                req.score(),
                req.comment());
        return portfolios.addEvaluation(studentId, evidenceId, trusted);
    }

    @GetMapping("/internal/portfolios/students/{studentId}/summary")
    public PortfolioSummaryDto summary(@PathVariable String studentId, CurrentUser user) {
        if (!isSelfOrAdmin(user, studentId)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only the student or ADMIN may view this summary");
        }
        return portfolios.summary(studentId);
    }

    @GetMapping("/internal/portfolios/courses/{courseId}/evidence")
    public List<LearningEvidenceDto> courseEvidence(@PathVariable String courseId, CurrentUser user) {
        requireStaff(user);
        return portfolios.courseEvidence(courseId);
    }

    private String callerId(CurrentUser user) {
        if (user == null || user.id() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Authenticated user required");
        }
        return String.valueOf(user.id());
    }

    private boolean isStaff(CurrentUser user) {
        return user != null && user.hasAnyRole(ROLE_ADMIN, ROLE_INSTRUCTOR);
    }

    private void requireStaff(CurrentUser user) {
        callerId(user);
        if (!isStaff(user)) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Requires ADMIN or INSTRUCTOR role");
        }
    }

    private void requireSelfOrStaff(CurrentUser user, String studentId) {
        if (isSelfOrAdmin(user, studentId) || isStaff(user)) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Not allowed to access another student's portfolio");
    }

    private boolean isSelfOrAdmin(CurrentUser user, String studentId) {
        return user != null && (user.hasRole(ROLE_ADMIN) || callerId(user).equals(studentId));
    }

    private void requireInstructorVisible(LearningEvidenceDetailDto evidence) {
        if (!"INSTRUCTOR".equals(evidence.visibility()) && !"PUBLIC".equals(evidence.visibility())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Evidence is private");
        }
    }
}
