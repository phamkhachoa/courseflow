package edu.courseflow.portfolio.service;

import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.portfolio.dto.PortfolioDtos.AddEvaluationRequestDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.AddLearningEvidenceRequestDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDetailDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.LearningEvidenceDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.PortfolioSummaryDto;
import edu.courseflow.portfolio.dto.PortfolioDtos.UpdateEvidenceRequestDto;
import edu.courseflow.portfolio.mapper.PortfolioMapper;
import edu.courseflow.portfolio.model.LearningEvidence;
import edu.courseflow.portfolio.repository.LearningEvidenceRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class PortfolioService {

    private final LearningEvidenceRepository evidenceRepository;
    private final PortfolioMapper mapper;

    public PortfolioService(LearningEvidenceRepository evidenceRepository, PortfolioMapper mapper) {
        this.evidenceRepository = evidenceRepository;
        this.mapper = mapper;
    }

    public List<LearningEvidenceDto> listEvidence(String studentId, Optional<String> courseId) {
        List<LearningEvidence> evidence = courseId
                .map(id -> evidenceRepository.findByStudentIdAndCourseIdOrderByCreatedAtDesc(studentId, id))
                .orElseGet(() -> evidenceRepository.findByStudentIdOrderByCreatedAtDesc(studentId));
        return evidence.stream().map(mapper::toDto).toList();
    }

    public List<LearningEvidenceDto> listEvidenceVisibleToInstructor(String studentId, Optional<String> courseId) {
        List<LearningEvidence> evidence = courseId
                .map(id -> evidenceRepository.findByStudentIdAndCourseIdOrderByCreatedAtDesc(studentId, id))
                .orElseGet(() -> evidenceRepository.findByStudentIdOrderByCreatedAtDesc(studentId));
        return evidence.stream()
                .filter(e -> "INSTRUCTOR".equals(e.getVisibility()) || "PUBLIC".equals(e.getVisibility()))
                .map(mapper::toDto)
                .toList();
    }

    public LearningEvidenceDto addEvidence(String studentId, AddLearningEvidenceRequestDto request) {
        LearningEvidence evidence = mapper.toEntity(studentId, request);
        return mapper.toDto(evidenceRepository.save(evidence));
    }

    public LearningEvidenceDetailDto getEvidence(String studentId, String evidenceId) {
        LearningEvidence e = evidenceRepository.findByIdAndStudentId(evidenceId, studentId)
                .orElseThrow(() -> new NotFoundException("Evidence not found: " + evidenceId));
        return toDetailDto(e);
    }

    public LearningEvidenceDetailDto updateEvidence(String studentId, String evidenceId, UpdateEvidenceRequestDto req) {
        LearningEvidence e = evidenceRepository.findByIdAndStudentId(evidenceId, studentId)
                .orElseThrow(() -> new NotFoundException("Evidence not found: " + evidenceId));
        if (req.title() != null) e.setTitle(req.title());
        if (req.reflection() != null) e.setReflection(req.reflection());
        if (req.visibility() != null) e.setVisibility(req.visibility());
        if (req.tags() != null) e.setTags(req.tags());
        if (req.mediaUrls() != null) e.setMediaUrls(req.mediaUrls());
        e.setUpdatedAt(Instant.now());
        return toDetailDto(evidenceRepository.save(e));
    }

    public void deleteEvidence(String studentId, String evidenceId) {
        LearningEvidence e = evidenceRepository.findByIdAndStudentId(evidenceId, studentId)
                .orElseThrow(() -> new NotFoundException("Evidence not found: " + evidenceId));
        evidenceRepository.delete(e);
    }

    public LearningEvidenceDetailDto addEvaluation(String studentId, String evidenceId, AddEvaluationRequestDto req) {
        LearningEvidence e = evidenceRepository.findByIdAndStudentId(evidenceId, studentId)
                .orElseThrow(() -> new NotFoundException("Evidence not found: " + evidenceId));
        LearningEvidence.EvidenceEvaluation eval = new LearningEvidence.EvidenceEvaluation();
        eval.setEvaluatorId(req.evaluatorId());
        eval.setEvaluatorRole(req.evaluatorRole());
        eval.setScore(req.score());
        eval.setComment(req.comment());
        eval.setEvaluatedAt(Instant.now());
        if (e.getEvaluations() == null) e.setEvaluations(new ArrayList<>());
        e.getEvaluations().add(eval);
        e.setUpdatedAt(Instant.now());
        return toDetailDto(evidenceRepository.save(e));
    }

    public PortfolioSummaryDto summary(String studentId) {
        List<LearningEvidence> all = evidenceRepository.findByStudentIdOrderByCreatedAtDesc(studentId);
        Map<String, Integer> byType = new LinkedHashMap<>();
        Map<String, Integer> byCourse = new LinkedHashMap<>();
        int evalCount = 0;
        BigDecimal scoreSum = BigDecimal.ZERO;
        for (LearningEvidence e : all) {
            byType.merge(e.getEvidenceType(), 1, Integer::sum);
            byCourse.merge(e.getCourseId(), 1, Integer::sum);
            if (e.getEvaluations() != null) {
                for (LearningEvidence.EvidenceEvaluation ev : e.getEvaluations()) {
                    if (ev.getScore() != null) {
                        scoreSum = scoreSum.add(ev.getScore());
                        evalCount++;
                    }
                }
            }
        }
        BigDecimal avg = evalCount > 0
                ? scoreSum.divide(BigDecimal.valueOf(evalCount), 2, RoundingMode.HALF_UP)
                : null;
        return new PortfolioSummaryDto(studentId, all.size(), byType, byCourse, avg, evalCount);
    }

    public List<LearningEvidenceDto> courseEvidence(String courseId) {
        return evidenceRepository.findByCourseIdOrderByCreatedAtDesc(courseId).stream()
                .filter(e -> "INSTRUCTOR".equals(e.getVisibility()) || "PUBLIC".equals(e.getVisibility()))
                .map(mapper::toDto)
                .toList();
    }

    private LearningEvidenceDetailDto toDetailDto(LearningEvidence e) {
        List<LearningEvidenceDetailDto.EvaluationDto> evals = e.getEvaluations() == null
                ? Collections.emptyList()
                : e.getEvaluations().stream()
                        .map(mapper::toDto)
                        .toList();
        return mapper.toDetailDto(e, evals);
    }
}
