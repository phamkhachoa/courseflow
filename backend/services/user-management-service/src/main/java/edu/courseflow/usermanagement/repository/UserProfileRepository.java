package edu.courseflow.usermanagement.repository;

import edu.courseflow.usermanagement.model.UserProfile;
import java.util.Collection;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserProfileRepository extends JpaRepository<UserProfile, Long> {

    List<UserProfile> findByUserIdInOrderByUserIdAsc(Collection<Long> userIds);

    @Query("""
            select profile from UserProfile profile
            where :needle = '' or lower(profile.displayName) like concat('%', :needle, '%')
            order by profile.displayName asc
            """)
    List<UserProfile> searchDirectory(@Param("needle") String needle, Pageable pageable);
}
