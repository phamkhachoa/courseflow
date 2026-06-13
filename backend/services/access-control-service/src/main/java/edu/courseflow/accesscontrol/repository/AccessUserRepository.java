package edu.courseflow.accesscontrol.repository;

import edu.courseflow.accesscontrol.model.AccessUser;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AccessUserRepository extends JpaRepository<AccessUser, Long> {

    @Query("""
            select user from AccessUser user
            where :needle = '' or lower(user.email) like concat('%', :needle, '%')
            order by user.id asc
            """)
    List<AccessUser> searchDirectory(@Param("needle") String needle, Pageable pageable);
}
