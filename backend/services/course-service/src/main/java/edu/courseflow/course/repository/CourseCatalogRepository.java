package edu.courseflow.course.repository;

import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.course.dto.CourseDtos.AddCourseMaterialRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseDto;
import edu.courseflow.course.dto.CourseDtos.CourseMaterialDto;
import edu.courseflow.course.dto.CourseDtos.CreateCourseRequestDto;
import edu.courseflow.course.dto.CourseDtos.CourseMetadataDto;
import edu.courseflow.course.dto.CourseDtos.CoursePricingDto;
import edu.courseflow.course.dto.CourseDtos.UpdateCoursePricingRequestDto;
import edu.courseflow.course.mapper.CourseMapper;
import edu.courseflow.course.model.Course;
import edu.courseflow.course.model.CourseMaterial;
import edu.courseflow.course.model.OutboxEvent;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class CourseCatalogRepository {

    private final CourseJpaRepository courses;
    private final CourseMaterialJpaRepository materials;
    private final OutboxEventJpaRepository outbox;
    private final CourseMapper mapper;

    public CourseCatalogRepository(CourseJpaRepository courses,
            CourseMaterialJpaRepository materials,
            OutboxEventJpaRepository outbox,
            CourseMapper mapper) {
        this.courses = courses;
        this.materials = materials;
        this.outbox = outbox;
        this.mapper = mapper;
    }

    public List<CourseDto> list(Optional<String> status) {
        List<Course> rows = status
                .map(courses::findByStatusOrderByCreatedAtDescTitleAsc)
                .orElseGet(courses::findAllByOrderByCreatedAtDescTitleAsc);
        return rows.stream().map(this::toCourseDto).toList();
    }

    public List<CourseDto> listOwned(String ownerId, Optional<String> status) {
        List<Course> rows = status
                .map(s -> courses.findByOwnerIdAndStatusOrderByCreatedAtDescTitleAsc(ownerId, s))
                .orElseGet(() -> courses.findByOwnerIdOrderByCreatedAtDescTitleAsc(ownerId));
        return rows.stream().map(this::toCourseDto).toList();
    }

    public List<CourseDto> listByDepartmentIds(List<UUID> departmentIds, Optional<String> status) {
        if (departmentIds == null || departmentIds.isEmpty()) {
            return List.of();
        }
        List<Course> rows = status
                .map(s -> courses.findByDepartmentIdInAndStatusOrderByCreatedAtDescTitleAsc(departmentIds, s))
                .orElseGet(() -> courses.findByDepartmentIdInOrderByCreatedAtDescTitleAsc(departmentIds));
        return rows.stream().map(this::toCourseDto).toList();
    }

    public List<CourseDto> listPublished() {
        return list(Optional.of("PUBLISHED"));
    }

    public Optional<CourseDto> findById(UUID courseId) {
        return courses.findById(courseId).map(this::toCourseDto);
    }

    public Optional<CourseMetadataDto> metadata(UUID courseId) {
        return courses.findById(courseId).map(mapper::toMetadataDto);
    }

    public Optional<CourseDto> findPublishedBySlug(String slug) {
        return courses.findBySlugAndStatus(slug, "PUBLISHED").map(this::toCourseDto);
    }

    public CourseDto create(CreateCourseRequestDto request, String ownerId) {
        UUID courseId = UUID.randomUUID();
        Course course = new Course(
                courseId,
                request.code(),
                request.title(),
                request.slug(),
                request.summary(),
                request.departmentId(),
                ownerId,
                request.level(),
                request.listPrice(),
                request.currency());
        courses.save(course);
        return toCourseDto(course);
    }

    public Optional<CoursePricingDto> pricing(UUID courseId) {
        return courses.findById(courseId).map(this::toPricingDto);
    }

    public CoursePricingDto updatePricing(UUID courseId, UpdateCoursePricingRequestDto request) {
        Course course = courses.findById(courseId).orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
        course.updatePricing(request.listPrice(), request.currency());
        return toPricingDto(courses.save(course));
    }

    public CourseMaterialDto addMaterial(UUID courseId, AddCourseMaterialRequestDto request) {
        if (!courses.existsById(courseId)) {
            throw new NotFoundException("Course not found: " + courseId);
        }
        CourseMaterial material = new CourseMaterial(
                UUID.randomUUID(),
                courseId,
                request.title(),
                request.materialType(),
                request.mediaId(),
                request.position() == null ? materials.nextPosition(courseId) : request.position());
        return toMaterialDto(materials.save(material));
    }

    public void updateStatus(UUID courseId, String status) {
        Course course = courses.findById(courseId).orElseThrow(() -> new NotFoundException("Course not found: " + courseId));
        course.setStatus(status);
    }

    public void outbox(UUID aggregateId, String eventType, String payload) {
        outbox.save(new OutboxEvent(aggregateId, "course", eventType, payload));
    }

    private CourseDto toCourseDto(Course course) {
        return mapper.toDto(course, materials.findByCourseIdOrderByPositionAscTitleAsc(course.getId()).stream()
                .map(mapper::toDto)
                .toList());
    }

    private CourseMaterialDto toMaterialDto(CourseMaterial material) {
        return mapper.toDto(material);
    }

    private CoursePricingDto toPricingDto(Course course) {
        boolean purchasable = "ACTIVE".equalsIgnoreCase(course.getPriceStatus())
                || "FREE".equalsIgnoreCase(course.getPriceStatus());
        return new CoursePricingDto(
                course.getId().toString(),
                course.getListPrice(),
                course.getCurrency(),
                course.getPriceStatus(),
                purchasable,
                "COURSE_CATALOG");
    }
}
