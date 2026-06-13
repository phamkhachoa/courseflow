package edu.courseflow.identity.repository;

import edu.courseflow.identity.model.UserRoleAssignment;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface UserRoleAssignmentRepository extends JpaRepository<UserRoleAssignment, Long> {

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select a from UserRoleAssignment a
            where a.userId = :userId and a.revokedAt is null
            order by a.id
            """)
    List<UserRoleAssignment> findLiveByUserId(@Param("userId") Long userId);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select a from UserRoleAssignment a
            where a.userId = :userId
              and a.revokedAt is null
              and (a.expiresAt is null or a.expiresAt > :now)
            order by a.id
            """)
    List<UserRoleAssignment> findActiveByUserId(@Param("userId") Long userId, @Param("now") Instant now);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select a from UserRoleAssignment a
            where a.userId = :userId
              and a.revokedAt is null
              and (a.expiresAt is null or a.expiresAt > :now)
              and (a.scopeType = 'PLATFORM'
                   or (a.scopeType = :scopeType and
                       ((a.scopeId is null and :scopeId is null) or a.scopeId = :scopeId)))
            order by a.id
            """)
    List<UserRoleAssignment> findActiveForScope(@Param("userId") Long userId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId,
            @Param("now") Instant now);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    List<UserRoleAssignment> findByUserIdOrderById(Long userId);

    @Query("""
            select a from UserRoleAssignment a
            where a.userId = :userId
              and a.role.id = :roleId
              and a.scopeType = :scopeType
              and ((a.scopeId is null and :scopeId is null) or a.scopeId = :scopeId)
              and a.revokedAt is null
            """)
    Optional<UserRoleAssignment> findLiveExisting(@Param("userId") Long userId,
            @Param("roleId") UUID roleId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId);

    @Query("select count(a) from UserRoleAssignment a where a.role.id = :roleId and a.revokedAt is null")
    long countLiveByRoleId(@Param("roleId") UUID roleId);

    Optional<UserRoleAssignment> findByIdAndUserId(Long id, Long userId);
}
