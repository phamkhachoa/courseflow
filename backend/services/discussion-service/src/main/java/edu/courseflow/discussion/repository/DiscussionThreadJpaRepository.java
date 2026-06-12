package edu.courseflow.discussion.repository;

import edu.courseflow.discussion.model.DiscussionThread;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface DiscussionThreadJpaRepository extends JpaRepository<DiscussionThread, UUID> {

    @Query("""
            select t from DiscussionThread t
            where (:courseId is null or t.courseId = :courseId)
              and (:assignmentId is null or t.assignmentId = :assignmentId)
            order by t.createdAt desc
            """)
    List<DiscussionThread> listFiltered(@Param("courseId") UUID courseId,
            @Param("assignmentId") UUID assignmentId);
}
