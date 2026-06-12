package edu.courseflow.announcement.repository;

import edu.courseflow.announcement.model.Announcement;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AnnouncementJpaRepository extends JpaRepository<Announcement, UUID> {

    @Query("""
            select a from Announcement a
            where (:courseId is null or a.courseId = :courseId)
              and (:status is null or a.status = :status)
            order by coalesce(a.publishedAt, a.publishAt) desc, a.title asc
            """)
    List<Announcement> listFiltered(@Param("courseId") UUID courseId, @Param("status") String status);
}
