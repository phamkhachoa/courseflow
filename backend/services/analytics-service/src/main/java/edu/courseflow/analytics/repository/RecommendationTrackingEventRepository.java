package edu.courseflow.analytics.repository;

import edu.courseflow.analytics.model.RecommendationTrackingEvent;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RecommendationTrackingEventRepository extends JpaRepository<RecommendationTrackingEvent, UUID> {

    @Query(value = """
            select
                coalesce(a.related_course_id, a.course_id) as courseId,
                coalesce(b.related_course_id, b.course_id) as relatedCourseId,
                count(distinct a.student_id) as supportCount
            from recommendation_tracking_events a
            join recommendation_tracking_events b
              on b.student_id = a.student_id
             and coalesce(b.related_course_id, b.course_id) <> coalesce(a.related_course_id, a.course_id)
            where a.event_type = 'ENROLLMENT'
              and b.event_type = 'ENROLLMENT'
              and a.student_id is not null
              and coalesce(a.related_course_id, a.course_id) is not null
              and coalesce(b.related_course_id, b.course_id) is not null
            group by coalesce(a.related_course_id, a.course_id), coalesce(b.related_course_id, b.course_id)
            """, nativeQuery = true)
    List<CoEnrollmentPairProjection> coEnrollmentPairs();

    @Query(value = """
            select
                course_id as courseId,
                related_course_id as relatedCourseId,
                coalesce(sum(case when event_type = 'IMPRESSION' then 1 else 0 end), 0) as impressionCount,
                coalesce(sum(case when event_type = 'CLICK' then 1 else 0 end), 0) as clickCount,
                coalesce(sum(case when event_type = 'ENROLLMENT' then 1 else 0 end), 0) as enrollCount
            from recommendation_tracking_events
            where course_id is not null
              and related_course_id is not null
              and event_type in ('IMPRESSION', 'CLICK', 'ENROLLMENT')
            group by course_id, related_course_id
            """, nativeQuery = true)
    List<AttributedPairProjection> attributedPairs();

    @Query(value = """
            select
                coalesce(
                    'student:' || student_id,
                    'session:' || session_id,
                    'actor:' || actor_id
                ) as principalId,
                coalesce(related_course_id, course_id) as courseId,
                event_type as eventType,
                occurred_at as occurredAt
            from recommendation_tracking_events
            where occurred_at >= :since
              and event_type in ('IMPRESSION', 'CLICK', 'ENROLLMENT')
              and coalesce(related_course_id, course_id) is not null
              and coalesce(student_id, session_id, actor_id) is not null
            order by occurred_at desc, event_id
            limit :limit
            """, nativeQuery = true)
    List<TrainingInteractionProjection> trainingInteractions(@Param("since") java.time.Instant since,
                                                             @Param("limit") int limit);

    interface CoEnrollmentPairProjection {
        UUID getCourseId();
        UUID getRelatedCourseId();
        long getSupportCount();
    }

    interface AttributedPairProjection {
        UUID getCourseId();
        UUID getRelatedCourseId();
        long getImpressionCount();
        long getClickCount();
        long getEnrollCount();
    }

    interface TrainingInteractionProjection {
        String getPrincipalId();
        UUID getCourseId();
        String getEventType();
        java.time.Instant getOccurredAt();
    }
}
