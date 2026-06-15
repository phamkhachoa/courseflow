package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.RelatedCourse;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RelatedCourseRepository extends JpaRepository<RelatedCourse, UUID> {

    List<RelatedCourse> findByCourseIdOrderByScoreDesc(UUID courseId, Pageable pageable);

    Optional<RelatedCourse> findByCourseIdAndRelatedCourseId(UUID courseId, UUID relatedCourseId);

    @Modifying
    @Query("delete from RelatedCourse row where row.source <> 'MANUAL'")
    int deleteGeneratedReadModel();

    @Query("""
            select count(row) > 0
            from RelatedCourse row
            where row.source = 'ML'
              and row.generatedAt > :generatedAt
            """)
    boolean existsMlReadModelNewerThan(@Param("generatedAt") Instant generatedAt);

    boolean existsBySourceAndModelVersion(String source, String modelVersion);

    @Modifying
    @Query(value = """
            with ranked as (
                select
                    stat.course_id,
                    stat.related_course_id,
                    stat.score,
                    stat.support_count,
                    stat.impression_count,
                    stat.click_count,
                    stat.enroll_count,
                    stat.model_version,
                    row_number() over (
                        partition by stat.course_id
                        order by stat.score desc, stat.support_count desc, stat.click_count desc, stat.related_course_id
                    ) as rank_number
                from course_pair_stats stat
                where stat.score > 0
            )
            insert into related_courses (
                id,
                course_id,
                related_course_id,
                score,
                source,
                reason,
                reason_code,
                model_version,
                generated_at
            )
            select
                gen_random_uuid(),
                ranked.course_id,
                ranked.related_course_id,
                ranked.score,
                'BEHAVIORAL',
                case
                    when ranked.support_count > 0 and ranked.enroll_count > 0
                        then 'Learners who enrolled here also enrolled in this course, with attributed conversions.'
                    when ranked.support_count > 0
                        then 'Learners who enrolled here also enrolled in this course.'
                    when ranked.enroll_count > 0
                        then 'Recommended course with attributed enrollments.'
                    when ranked.click_count > 0
                        then 'Recommended course with recent clicks.'
                    else 'Recommended course with recent impressions.'
                end,
                case
                    when ranked.support_count > 0 then 'CO_ENROLLMENT'
                    when ranked.enroll_count > 0 then 'ATTRIBUTED_ENROLLMENT'
                    when ranked.click_count > 0 then 'BEHAVIORAL_CLICK'
                    else 'BEHAVIORAL_IMPRESSION'
                end,
                ranked.model_version,
                now()
            from ranked
            where ranked.rank_number <= :limitPerCourse
              and not exists (
                  select 1
                  from manual_related_courses manual
                  where manual.course_id = ranked.course_id
                    and manual.related_course_id = ranked.related_course_id
                    and manual.placement = 'COURSE_DETAIL'
                    and manual.status in ('ACTIVE', 'ARCHIVED')
              )
            on conflict (course_id, related_course_id) do update set
                score = excluded.score,
                source = excluded.source,
                reason = excluded.reason,
                reason_code = excluded.reason_code,
                model_version = excluded.model_version,
                generated_at = excluded.generated_at
            """, nativeQuery = true)
    int refreshGeneratedReadModel(@Param("limitPerCourse") int limitPerCourse);
}
