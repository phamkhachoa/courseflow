package edu.courseflow.gradebook.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.gradebook.dto.GradebookDtos.CategorySummaryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.CreateGradingSchemeRequestDto;
import edu.courseflow.gradebook.dto.GradebookDtos.FinalGradeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeCategoryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeEntryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeItemDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradeOverrideDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeDto;
import edu.courseflow.gradebook.dto.GradebookDtos.GradingSchemeEntryDto;
import edu.courseflow.gradebook.dto.GradebookDtos.StudentGradebookDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertCategoryRequestDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertGradeEntryRequestDto;
import edu.courseflow.gradebook.dto.GradebookDtos.UpsertGradeItemRequestDto;
import edu.courseflow.gradebook.mapper.GradebookMapper;
import edu.courseflow.gradebook.model.FinalGrade;
import edu.courseflow.gradebook.model.GradeCategory;
import edu.courseflow.gradebook.model.GradeEntry;
import edu.courseflow.gradebook.model.GradeItem;
import edu.courseflow.gradebook.model.GradeOverride;
import edu.courseflow.gradebook.model.GradingScheme;
import edu.courseflow.gradebook.model.GradingSchemeEntry;
import edu.courseflow.gradebook.model.OutboxEvent;
import edu.courseflow.gradebook.repository.FinalGradeRepository;
import edu.courseflow.gradebook.repository.GradeCategoryRepository;
import edu.courseflow.gradebook.repository.GradeEntryRepository;
import edu.courseflow.gradebook.repository.GradeItemRepository;
import edu.courseflow.gradebook.repository.GradeOverrideRepository;
import edu.courseflow.gradebook.repository.GradingSchemeEntryRepository;
import edu.courseflow.gradebook.repository.GradingSchemeRepository;
import edu.courseflow.gradebook.repository.OutboxEventRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class GradebookService {

    private static final BigDecimal ONE_HUNDRED = new BigDecimal("100");
    private static final BigDecimal MINUTES_PER_DAY = new BigDecimal("1440");

    private final GradeCategoryRepository categories;
    private final GradeItemRepository items;
    private final GradeEntryRepository entries;
    private final GradeOverrideRepository overrides;
    private final GradingSchemeRepository schemes;
    private final GradingSchemeEntryRepository schemeEntries;
    private final FinalGradeRepository finalGrades;
    private final OutboxEventRepository outbox;
    private final ObjectMapper objectMapper;
    private final GradebookMapper mapper;

    public GradebookService(GradeCategoryRepository categories,
            GradeItemRepository items,
            GradeEntryRepository entries,
            GradeOverrideRepository overrides,
            GradingSchemeRepository schemes,
            GradingSchemeEntryRepository schemeEntries,
            FinalGradeRepository finalGrades,
            OutboxEventRepository outbox,
            ObjectMapper objectMapper,
            GradebookMapper mapper) {
        this.categories = categories;
        this.items = items;
        this.entries = entries;
        this.overrides = overrides;
        this.schemes = schemes;
        this.schemeEntries = schemeEntries;
        this.finalGrades = finalGrades;
        this.outbox = outbox;
        this.objectMapper = objectMapper;
        this.mapper = mapper;
    }

    // ---------- Reads ----------

    public List<GradeItemDto> listItems(UUID courseId) {
        Map<UUID, GradeCategory> categoryById = categories.findByCourseIdOrderByPositionAscNameAsc(courseId).stream()
                .collect(Collectors.toMap(GradeCategory::getId, Function.identity()));
        return items.findByCourseId(courseId).stream()
                .sorted(Comparator
                        .comparing((GradeItem item) -> categoryById.get(item.getCategoryId()).getPosition())
                        .thenComparing(GradeItem::getTitle))
                .map(item -> toGradeItemDto(item, categoryById.get(item.getCategoryId())))
                .toList();
    }

    @Transactional
    public GradeItemDto createGradeItem(UUID courseId, UpsertGradeItemRequestDto request) {
        GradeItemInput input = validateGradeItemInput(courseId, request);
        items.findBySourceTypeAndSourceId(input.sourceType(), input.sourceId())
                .ifPresent(existing -> {
                    throw new BadRequestException("GRADE_ITEM_SOURCE_ALREADY_EXISTS");
                });
        GradeItem item = new GradeItem(
                UUID.randomUUID(),
                courseId,
                input.category().getId(),
                input.sourceType(),
                input.sourceId(),
                input.title(),
                input.maxScore(),
                input.weightPercent(),
                input.latePenaltyPercent());
        item.update(input.category().getId(), input.sourceType(), input.sourceId(), input.title(),
                input.maxScore(), input.weightPercent(), input.latePenaltyPercent(), input.published());
        return toGradeItemDto(items.save(item), input.category());
    }

    @Transactional
    public GradeItemDto updateGradeItem(UUID courseId, UUID itemId, UpsertGradeItemRequestDto request) {
        GradeItem item = items.findById(itemId)
                .orElseThrow(() -> new NotFoundException("Grade item not found: " + itemId));
        if (!item.getCourseId().equals(courseId)) {
            throw new BadRequestException("GRADE_ITEM_NOT_IN_COURSE");
        }
        GradeItemInput input = validateGradeItemInput(courseId, request);
        items.findBySourceTypeAndSourceId(input.sourceType(), input.sourceId())
                .filter(existing -> !existing.getId().equals(itemId))
                .ifPresent(existing -> {
                    throw new BadRequestException("GRADE_ITEM_SOURCE_ALREADY_EXISTS");
                });
        item.update(input.category().getId(), input.sourceType(), input.sourceId(), input.title(),
                input.maxScore(), input.weightPercent(), input.latePenaltyPercent(), input.published());
        return toGradeItemDto(items.save(item), input.category());
    }

    public StudentGradebookDto studentGradebook(UUID courseId, String studentId) {
        List<EntryRow> rows = loadEntries(courseId, studentId);
        Optional<GradingSchemeDto> scheme = findDefaultScheme(courseId);

        Map<UUID, List<EntryRow>> byCategory = rows.stream()
                .collect(Collectors.groupingBy(EntryRow::categoryId, LinkedHashMap::new, Collectors.toList()));

        BigDecimal finalScore = BigDecimal.ZERO;
        List<CategorySummaryDto> categorySummaries = new ArrayList<>();
        List<GradeEntryDto> entryDtos = new ArrayList<>();

        for (Map.Entry<UUID, List<EntryRow>> e : byCategory.entrySet()) {
            List<EntryRow> categoryItems = new ArrayList<>(e.getValue());
            CategoryMeta meta = categoryItems.get(0).category();
            int dropLowest = meta.dropLowest();

            List<EntryRow> sorted = categoryItems.stream()
                    .sorted(Comparator.comparing(EntryRow::scorePercent))
                    .collect(Collectors.toCollection(ArrayList::new));
            List<EntryRow> kept = sorted.size() <= dropLowest ? List.of() : sorted.subList(dropLowest, sorted.size());

            BigDecimal contribution = aggregateCategory(meta.aggregationMethod(), kept, meta.weightPercent());
            finalScore = finalScore.add(contribution);
            categorySummaries.add(new CategorySummaryDto(
                    meta.name(), meta.aggregationMethod(), dropLowest, meta.weightPercent(),
                    contribution.setScale(2, RoundingMode.HALF_UP),
                    categoryItems.size(), categoryItems.size() - kept.size()));

            for (EntryRow row : categoryItems) {
                entryDtos.add(toEntryDto(row, scheme));
            }
        }

        BigDecimal rounded = finalScore.setScale(2, RoundingMode.HALF_UP);
        String letter = scheme.map(s -> resolveLetter(s, rounded)).orElse(null);
        return new StudentGradebookDto(
                courseId.toString(), studentId, rounded, letter,
                scheme.map(GradingSchemeDto::name).orElse(null),
                categorySummaries, entryDtos);
    }

    private GradeEntryDto toEntryDto(EntryRow row, Optional<GradingSchemeDto> scheme) {
        BigDecimal pct = row.scorePercent().multiply(ONE_HUNDRED).setScale(2, RoundingMode.HALF_UP);
        String letter = scheme.map(s -> resolveLetter(s, pct)).orElse(null);
        return new GradeEntryDto(
                row.entryId().toString(), row.gradeItemId().toString(), row.title(), row.category().name(),
                row.rawScore(), row.adjustedScore(), row.maxScore(),
                row.latePenaltyApplied(), row.isLate(), row.minutesLate(),
                letter, row.status(), row.gradedAt());
    }

    private BigDecimal aggregateCategory(String method, List<EntryRow> kept, BigDecimal categoryWeightPercent) {
        return categoryContribution(
                method,
                kept.stream().map(EntryRow::scorePercent).toList(),
                kept.stream().map(EntryRow::maxScore).toList(),
                kept.stream().map(EntryRow::itemWeight).toList(),
                categoryWeightPercent);
    }

    static BigDecimal categoryContribution(String method, List<BigDecimal> scorePercents,
            List<BigDecimal> maxScores, List<BigDecimal> itemWeights, BigDecimal categoryWeightPercent) {
        if (scorePercents.isEmpty()) {
            return BigDecimal.ZERO;
        }
        BigDecimal catWeight = categoryWeightPercent.divide(ONE_HUNDRED, 6, RoundingMode.HALF_UP);
        return switch (method == null ? "WEIGHTED_MEAN" : method.toUpperCase(Locale.ROOT)) {
            case "SUM" -> {
                BigDecimal totalMax = maxScores.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
                if (totalMax.compareTo(BigDecimal.ZERO) <= 0) {
                    yield BigDecimal.ZERO;
                }
                BigDecimal totalEarned = BigDecimal.ZERO;
                for (int i = 0; i < scorePercents.size(); i++) {
                    totalEarned = totalEarned.add(scorePercents.get(i).multiply(maxScores.get(i)));
                }
                yield totalEarned.divide(totalMax, 6, RoundingMode.HALF_UP)
                        .multiply(catWeight).multiply(ONE_HUNDRED);
            }
            case "MEAN" -> scorePercents.stream()
                    .reduce(BigDecimal.ZERO, BigDecimal::add)
                    .divide(BigDecimal.valueOf(scorePercents.size()), 6, RoundingMode.HALF_UP)
                    .multiply(catWeight).multiply(ONE_HUNDRED);
            default -> {
                BigDecimal totalWeight = itemWeights.stream().reduce(BigDecimal.ZERO, BigDecimal::add);
                if (totalWeight.compareTo(BigDecimal.ZERO) == 0) {
                    yield BigDecimal.ZERO;
                }
                BigDecimal weighted = BigDecimal.ZERO;
                for (int i = 0; i < scorePercents.size(); i++) {
                    weighted = weighted.add(scorePercents.get(i).multiply(itemWeights.get(i)));
                }
                yield weighted.divide(totalWeight, 6, RoundingMode.HALF_UP)
                        .multiply(catWeight).multiply(ONE_HUNDRED);
            }
        };
    }

    private List<EntryRow> loadEntries(UUID courseId, String studentId) {
        List<GradeItem> courseItems = items.findByCourseId(courseId);
        if (courseItems.isEmpty()) {
            return List.of();
        }
        Map<UUID, GradeItem> itemById = courseItems.stream()
                .collect(Collectors.toMap(GradeItem::getId, Function.identity()));
        Map<UUID, GradeCategory> categoryById = categories.findByCourseIdOrderByPositionAscNameAsc(courseId).stream()
                .collect(Collectors.toMap(GradeCategory::getId, Function.identity()));

        return entries.findByGradeItemIdInAndStudentIdAndStatus(itemById.keySet(), studentId, "PUBLISHED").stream()
                .map(entry -> {
                    GradeItem item = itemById.get(entry.getGradeItemId());
                    GradeCategory category = categoryById.get(item.getCategoryId());
                    BigDecimal raw = entry.getRawScore();
                    BigDecimal adjusted = entry.getAdjustedScore();
                    BigDecimal effective = adjusted != null ? adjusted : raw;
                    BigDecimal pct = item.getMaxScore().compareTo(BigDecimal.ZERO) == 0
                            ? BigDecimal.ZERO
                            : effective.divide(item.getMaxScore(), 6, RoundingMode.HALF_UP);
                    CategoryMeta categoryMeta = new CategoryMeta(
                            category.getName(),
                            category.getWeightPercent(),
                            category.getAggregationMethod(),
                            category.getDropLowest());
                    return new EntryRow(
                            entry.getId(), entry.getGradeItemId(),
                            item.getTitle(), item.getMaxScore(), raw, adjusted, pct,
                            item.getWeightPercent(), entry.isLate(), entry.getMinutesLate(),
                            entry.getLatePenaltyApplied(), category.getId(), categoryMeta,
                            entry.getStatus(), entry.getGradedAt());
                })
                .sorted(Comparator
                        .comparing((EntryRow row) -> categoryById.get(row.categoryId()).getPosition())
                        .thenComparing(EntryRow::title))
                .toList();
    }

    // ---------- Upsert with late penalty ----------

    @Transactional
    public StudentGradebookDto upsertEntry(UpsertGradeEntryRequestDto request, String actorId) {
        UUID gradeItemId = UUID.fromString(request.gradeItemId());
        GradeItem item = items.findById(gradeItemId)
                .orElseThrow(() -> new NotFoundException("Grade item not found: " + gradeItemId));
        if (request.rawScore().compareTo(BigDecimal.ZERO) < 0 || request.rawScore().compareTo(item.getMaxScore()) > 0) {
            throw new BadRequestException("SCORE_OUT_OF_RANGE");
        }

        boolean isLate = request.isLate() != null && request.isLate();
        int minutesLate = request.minutesLate() == null ? 0 : request.minutesLate();
        BigDecimal penaltyPct = BigDecimal.ZERO;
        BigDecimal adjusted = null;

        if (isLate && item.getLatePenaltyPercent().compareTo(BigDecimal.ZERO) > 0) {
            BigDecimal daysLate = BigDecimal.valueOf(Math.max(1,
                    (int) Math.ceil(minutesLate / MINUTES_PER_DAY.doubleValue())));
            penaltyPct = item.getLatePenaltyPercent().multiply(daysLate).min(ONE_HUNDRED);
            BigDecimal penalty = request.rawScore().multiply(penaltyPct).divide(ONE_HUNDRED, 4, RoundingMode.HALF_UP);
            adjusted = request.rawScore().subtract(penalty).max(BigDecimal.ZERO).setScale(2, RoundingMode.HALF_UP);
        }

        Optional<GradeEntry> existingEntry = entries.findByGradeItemIdAndStudentId(gradeItemId, request.studentId());
        GradeEntry entry = existingEntry.orElseGet(() -> new GradeEntry(UUID.randomUUID(), gradeItemId, request.studentId()));
        BigDecimal oldScore = existingEntry.map(this::effectiveScore).orElse(null);
        BigDecimal newScore = adjusted == null ? request.rawScore() : adjusted;
        if (oldScore != null && oldScore.compareTo(newScore) != 0 && isBlank(request.reason())) {
            throw new BadRequestException("GRADE_OVERRIDE_REASON_REQUIRED");
        }
        entry.publish(request.rawScore(), adjusted, isLate, minutesLate, penaltyPct);
        entry = entries.save(entry);
        if (oldScore != null && oldScore.compareTo(newScore) != 0) {
            overrides.save(new GradeOverride(
                    entry.getId(),
                    oldScore,
                    newScore,
                    request.reason().trim(),
                    actorId == null || actorId.isBlank() ? "system" : actorId));
        }

        return studentGradebook(item.getCourseId(), request.studentId());
    }

    public UUID courseIdForGradeItem(UUID gradeItemId) {
        return items.findById(gradeItemId)
                .map(GradeItem::getCourseId)
                .orElseThrow(() -> new NotFoundException("Grade item not found: " + gradeItemId));
    }

    public UUID courseIdForEntry(UUID entryId) {
        GradeEntry entry = entries.findById(entryId)
                .orElseThrow(() -> new NotFoundException("Grade entry not found: " + entryId));
        return courseIdForGradeItem(entry.getGradeItemId());
    }

    public List<GradeOverrideDto> listOverrides(UUID gradeEntryId) {
        if (!entries.existsById(gradeEntryId)) {
            throw new NotFoundException("Grade entry not found: " + gradeEntryId);
        }
        return overrides.findByGradeEntryIdOrderByCreatedAtDesc(gradeEntryId).stream()
                .map(this::toOverrideDto)
                .toList();
    }

    // ---------- Final grade ----------

    @Transactional
    public FinalGradeDto finalizeGrade(UUID courseId, String studentId, String finalizedBy) {
        StudentGradebookDto gradebook = studentGradebook(courseId, studentId);
        BigDecimal finalScore = gradebook.finalScore() == null
                ? BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP)
                : gradebook.finalScore();
        String letter = gradebook.finalLetter();
        BigDecimal passThreshold = passingThreshold(courseId);
        boolean passed = finalScore.compareTo(passThreshold) >= 0;
        String actor = (finalizedBy == null || finalizedBy.isBlank()) ? "system" : finalizedBy;

        FinalGrade finalGrade = finalGrades.findByCourseIdAndStudentId(courseId, studentId)
                .orElseGet(() -> new FinalGrade(UUID.randomUUID(), courseId, studentId));
        finalGrade.finalizeAs(finalScore, letter, passed, actor);
        finalGrade = finalGrades.save(finalGrade);

        Map<String, Object> payload = new HashMap<>();
        payload.put("eventId", UUID.randomUUID().toString());
        payload.put("finalGradeId", finalGrade.getId().toString());
        payload.put("courseId", courseId.toString());
        payload.put("studentId", studentId);
        payload.put("finalScore", finalScore);
        payload.put("letter", letter);
        payload.put("passed", passed);
        payload.put("status", "FINALIZED");
        payload.put("updatedAt", Instant.now().toString());
        outbox.save(new OutboxEvent(finalGrade.getId(), "final-grade", "gradebook.final_grade.updated", toJson(payload)));

        return toFinalGradeDto(finalGrade);
    }

    public FinalGradeDto getFinalGrade(UUID courseId, String studentId) {
        return finalGrades.findByCourseIdAndStudentId(courseId, studentId)
                .map(this::toFinalGradeDto)
                .orElseThrow(() -> new NotFoundException(
                        "No final grade for student " + studentId + " in course " + courseId));
    }

    private BigDecimal passingThreshold(UUID courseId) {
        return findDefaultScheme(courseId)
                .flatMap(scheme -> scheme.entries().stream()
                        .filter(e -> e.gpaPoints() != null && e.gpaPoints().compareTo(BigDecimal.ZERO) > 0)
                        .map(GradingSchemeEntryDto::minPercent)
                        .min(BigDecimal::compareTo))
                .orElse(new BigDecimal("60.00"));
    }

    // ---------- Grade categories ----------

    public List<GradeCategoryDto> listCategories(UUID courseId) {
        return categories.findByCourseIdOrderByPositionAscNameAsc(courseId).stream()
                .map(this::toCategoryDto)
                .toList();
    }

    @Transactional
    public GradeCategoryDto createCategory(UUID courseId, UpsertCategoryRequestDto request) {
        BigDecimal weight = request.weightPercent();
        validateCourseWeightTotal(courseId, null, weight);
        GradeCategory category = new GradeCategory(
                UUID.randomUUID(),
                courseId,
                request.name(),
                weight,
                categories.nextPosition(courseId),
                request.aggregationMethod() == null ? "WEIGHTED_MEAN" : request.aggregationMethod(),
                request.dropLowest() == null ? 0 : request.dropLowest());
        return toCategoryDto(categories.save(category));
    }

    @Transactional
    public GradeCategoryDto updateCategory(UUID courseId, UUID categoryId, UpsertCategoryRequestDto request) {
        GradeCategory existing = categories.findById(categoryId)
                .orElseThrow(() -> new NotFoundException("Grade category not found: " + categoryId));
        if (!existing.getCourseId().equals(courseId)) {
            throw new BadRequestException("CATEGORY_NOT_IN_COURSE");
        }
        validateCourseWeightTotal(courseId, categoryId, request.weightPercent());
        existing.update(
                request.name(),
                request.weightPercent(),
                request.aggregationMethod() == null ? existing.getAggregationMethod() : request.aggregationMethod(),
                request.dropLowest() == null ? existing.getDropLowest() : request.dropLowest());
        return toCategoryDto(existing);
    }

    private void validateCourseWeightTotal(UUID courseId, UUID excludeCategoryId, BigDecimal newWeight) {
        if (newWeight == null || newWeight.compareTo(BigDecimal.ZERO) < 0) {
            throw new BadRequestException("CATEGORY_WEIGHT_INVALID");
        }
        BigDecimal total = categories.sumWeightsExcluding(courseId, excludeCategoryId).add(newWeight);
        if (total.compareTo(new BigDecimal("100.01")) > 0) {
            throw new BadRequestException("CATEGORY_WEIGHT_TOTAL_EXCEEDS_100");
        }
    }

    // ---------- Grading schemes ----------

    @Transactional
    public GradingSchemeDto createScheme(UUID courseId, CreateGradingSchemeRequestDto request) {
        boolean isDefault = request.isDefault() != null && request.isDefault();
        if (isDefault) {
            List<GradingScheme> defaults = schemes.findByCourseIdAndDefaultSchemeTrueOrderByNameAsc(courseId);
            defaults.forEach(scheme -> scheme.setDefaultScheme(false));
            schemes.saveAll(defaults);
        }
        GradingScheme scheme = schemes.save(new GradingScheme(UUID.randomUUID(), courseId, request.name(), isDefault));
        int pos = 1;
        List<GradingSchemeEntryDto> sorted = request.entries().stream()
                .sorted(Comparator.comparing(GradingSchemeEntryDto::minPercent).reversed())
                .toList();
        for (GradingSchemeEntryDto entry : sorted) {
            schemeEntries.save(new GradingSchemeEntry(
                    scheme.getId(), entry.letter(), entry.minPercent(), entry.gpaPoints(), pos++));
        }
        return loadScheme(scheme.getId());
    }

    public List<GradingSchemeDto> listSchemes(UUID courseId) {
        return schemes.findByCourseIdOrderByDefaultSchemeDescNameAsc(courseId).stream()
                .map(scheme -> loadScheme(scheme.getId()))
                .toList();
    }

    private GradingSchemeDto loadScheme(UUID schemeId) {
        GradingScheme scheme = schemes.findById(schemeId)
                .orElseThrow(() -> new NotFoundException("Grading scheme not found: " + schemeId));
        return mapper.toDto(scheme, schemeEntries.findBySchemeIdOrderByMinPercentDesc(scheme.getId()).stream()
                .map(mapper::toDto)
                .toList());
    }

    private Optional<GradingSchemeDto> findDefaultScheme(UUID courseId) {
        return schemes.findByCourseIdAndDefaultSchemeTrue(courseId).map(scheme -> loadScheme(scheme.getId()));
    }

    private String resolveLetter(GradingSchemeDto scheme, BigDecimal percent) {
        for (GradingSchemeEntryDto entry : scheme.entries()) {
            if (percent.compareTo(entry.minPercent()) >= 0) {
                return entry.letter();
            }
        }
        return null;
    }

    // ---------- CSV export ----------

    public String exportCsv(UUID courseId) {
        List<GradeItemDto> gradeItems = listItems(courseId);
        if (gradeItems.isEmpty()) {
            return "student_id,FinalScore,Letter\n";
        }
        List<UUID> itemIds = gradeItems.stream().map(item -> UUID.fromString(item.id())).toList();
        List<String> students = entries.distinctStudentsForItems(itemIds);

        StringBuilder sb = new StringBuilder();
        sb.append("student_id");
        for (GradeItemDto item : gradeItems) {
            sb.append(",").append(csvField(item.title()));
        }
        sb.append(",FinalScore,Letter\n");

        for (String studentId : students) {
            StudentGradebookDto gradebook = studentGradebook(courseId, studentId);
            Map<String, GradeEntryDto> byItem = gradebook.entries().stream()
                    .collect(Collectors.toMap(GradeEntryDto::gradeItemId, e -> e, (a, b) -> a));
            sb.append(csvField(studentId));
            for (GradeItemDto item : gradeItems) {
                GradeEntryDto entry = byItem.get(item.id());
                if (entry == null) {
                    sb.append(",");
                } else {
                    BigDecimal score = entry.adjustedScore() != null ? entry.adjustedScore() : entry.rawScore();
                    sb.append(",").append(score == null ? "" : score.toPlainString());
                }
            }
            sb.append(",").append(gradebook.finalScore() == null ? "" : gradebook.finalScore().toPlainString());
            sb.append(",").append(gradebook.finalLetter() == null ? "" : gradebook.finalLetter());
            sb.append("\n");
        }
        return sb.toString();
    }

    private GradeItemDto toGradeItemDto(GradeItem item, GradeCategory category) {
        return mapper.toDto(item, category);
    }

    private GradeItemInput validateGradeItemInput(UUID courseId, UpsertGradeItemRequestDto request) {
        UUID categoryId = UUID.fromString(request.categoryId());
        GradeCategory category = categories.findById(categoryId)
                .orElseThrow(() -> new NotFoundException("Grade category not found: " + categoryId));
        if (!category.getCourseId().equals(courseId)) {
            throw new BadRequestException("CATEGORY_NOT_IN_COURSE");
        }
        if (request.maxScore().compareTo(BigDecimal.ZERO) <= 0) {
            throw new BadRequestException("GRADE_ITEM_MAX_SCORE_INVALID");
        }
        if (request.weightPercent().compareTo(BigDecimal.ZERO) < 0) {
            throw new BadRequestException("GRADE_ITEM_WEIGHT_INVALID");
        }
        if (request.latePenaltyPercent().compareTo(BigDecimal.ZERO) < 0
                || request.latePenaltyPercent().compareTo(ONE_HUNDRED) > 0) {
            throw new BadRequestException("GRADE_ITEM_LATE_PENALTY_INVALID");
        }
        String sourceType = request.sourceType().trim().toUpperCase(Locale.ROOT);
        String sourceId = request.sourceId().trim();
        String title = request.title().trim();
        if (sourceType.isBlank() || sourceId.isBlank() || title.isBlank()) {
            throw new BadRequestException("GRADE_ITEM_REQUIRED_FIELDS_MISSING");
        }
        return new GradeItemInput(
                category,
                sourceType,
                sourceId,
                title,
                request.maxScore(),
                request.weightPercent(),
                request.latePenaltyPercent(),
                !Boolean.FALSE.equals(request.published()));
    }

    private GradeCategoryDto toCategoryDto(GradeCategory category) {
        return mapper.toDto(category);
    }

    private FinalGradeDto toFinalGradeDto(FinalGrade grade) {
        return mapper.toDto(grade);
    }

    private GradeOverrideDto toOverrideDto(GradeOverride override) {
        return new GradeOverrideDto(
                override.getId().toString(),
                override.getGradeEntryId().toString(),
                override.getOldScore(),
                override.getNewScore(),
                override.getReason(),
                override.getActorId(),
                override.getCreatedAt());
    }

    private BigDecimal effectiveScore(GradeEntry entry) {
        return entry.getAdjustedScore() == null ? entry.getRawScore() : entry.getAdjustedScore();
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (JsonProcessingException ex) {
            throw new IllegalStateException("Unable to serialize JSON payload", ex);
        }
    }

    private static String csvField(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    private record CategoryMeta(String name, BigDecimal weightPercent, String aggregationMethod, int dropLowest) {
    }

    private record EntryRow(
            UUID entryId, UUID gradeItemId, String title,
            BigDecimal maxScore, BigDecimal rawScore, BigDecimal adjustedScore, BigDecimal scorePercent,
            BigDecimal itemWeight,
            boolean isLate, int minutesLate, BigDecimal latePenaltyApplied,
            UUID categoryId, CategoryMeta category,
            String status, Instant gradedAt) {
    }

    private record GradeItemInput(
            GradeCategory category,
            String sourceType,
            String sourceId,
            String title,
            BigDecimal maxScore,
            BigDecimal weightPercent,
            BigDecimal latePenaltyPercent,
            boolean published) {
    }
}
