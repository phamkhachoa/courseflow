package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.CoursePairStat;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CoursePairStatRepository extends JpaRepository<CoursePairStat, UUID> {

    Optional<CoursePairStat> findByCourseIdAndRelatedCourseId(UUID courseId, UUID relatedCourseId);

    List<CoursePairStat> findByCourseIdOrderByScoreDesc(UUID courseId, Pageable pageable);

    @Modifying
    @Query(value = """
            with behavioral as (
                select
                    course_id,
                    related_course_id,
                    count(*) filter (where event_type = 'IMPRESSION')::int as impression_count,
                    count(*) filter (where event_type = 'CLICK')::int as click_count,
                    count(*) filter (where event_type = 'ENROLLMENT')::int as enroll_count
                from recommendation_tracking_events
                where occurred_at >= :since
                  and course_id is not null
                  and related_course_id is not null
                  and course_id <> related_course_id
                  and event_type in ('IMPRESSION', 'CLICK', 'ENROLLMENT')
                group by course_id, related_course_id
            ),
            enrollments as (
                select
                    student_id,
                    coalesce(related_course_id, course_id) as enrolled_course_id,
                    max(occurred_at) as last_enrolled_at
                from recommendation_tracking_events
                where occurred_at >= :since
                  and event_type = 'ENROLLMENT'
                  and student_id is not null
                  and coalesce(related_course_id, course_id) is not null
                group by student_id, coalesce(related_course_id, course_id)
            ),
            co_enrollments as (
                select
                    anchor.enrolled_course_id as course_id,
                    related.enrolled_course_id as related_course_id,
                    count(*)::int as support_count
                from enrollments anchor
                join enrollments related
                  on related.student_id = anchor.student_id
                 and related.enrolled_course_id <> anchor.enrolled_course_id
                group by anchor.enrolled_course_id, related.enrolled_course_id
            ),
            combined as (
                select
                    coalesce(behavioral.course_id, co_enrollments.course_id) as course_id,
                    coalesce(behavioral.related_course_id, co_enrollments.related_course_id) as related_course_id,
                    coalesce(co_enrollments.support_count, 0) as support_count,
                    coalesce(behavioral.impression_count, 0) as impression_count,
                    coalesce(behavioral.click_count, 0) as click_count,
                    coalesce(behavioral.enroll_count, 0) as enroll_count
                from behavioral
                full outer join co_enrollments
                  on co_enrollments.course_id = behavioral.course_id
                 and co_enrollments.related_course_id = behavioral.related_course_id
            )
            insert into course_pair_stats (
                id,
                course_id,
                related_course_id,
                support_count,
                impression_count,
                click_count,
                enroll_count,
                score,
                model_version,
                generated_at
            )
            select
                gen_random_uuid(),
                course_id,
                related_course_id,
                support_count,
                impression_count,
                click_count,
                enroll_count,
                least(
                    999.999,
                    round((
                        support_count * 4.0
                        + enroll_count * 6.0
                        + click_count * 1.5
                        + impression_count * 0.05
                    )::numeric, 3)
                ) as score,
                :modelVersion,
                now()
            from combined
            where course_id <> related_course_id
              and (
                  support_count > 0
                  or impression_count > 0
                  or click_count > 0
                  or enroll_count > 0
              )
            on conflict (course_id, related_course_id) do update set
                support_count = excluded.support_count,
                impression_count = excluded.impression_count,
                click_count = excluded.click_count,
                enroll_count = excluded.enroll_count,
                score = excluded.score,
                model_version = excluded.model_version,
                generated_at = excluded.generated_at
            """, nativeQuery = true)
    int recomputeFromTrackingEvents(@Param("since") java.time.Instant since,
                                    @Param("modelVersion") String modelVersion);
}
