package edu.courseflow.accesscontrol.repository;

import edu.courseflow.accesscontrol.model.UserRoleAssignment;
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
            select assignment from UserRoleAssignment assignment
            where assignment.user.id = :userId
              and assignment.revokedAt is null
            order by assignment.id
            """)
    List<UserRoleAssignment> findLiveByUserId(@Param("userId") Long userId);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select assignment from UserRoleAssignment assignment
            where assignment.user.id = :userId
            order by assignment.id
            """)
    List<UserRoleAssignment> findAllByUserId(@Param("userId") Long userId);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select assignment from UserRoleAssignment assignment
            where assignment.user.id = :userId
              and assignment.revokedAt is null
              and (assignment.expiresAt is null or assignment.expiresAt > :now)
            order by assignment.role.rank desc, assignment.role.code asc, assignment.scopeType asc, assignment.scopeId asc
            """)
    List<UserRoleAssignment> findActiveByUserId(@Param("userId") Long userId, @Param("now") Instant now);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select assignment from UserRoleAssignment assignment
            where assignment.user.id = :userId
              and assignment.revokedAt is null
              and (assignment.expiresAt is null or assignment.expiresAt > :now)
              and (assignment.scopeType = 'PLATFORM'
                   or (assignment.scopeType = :scopeType and
                       (assignment.scopeId is null or assignment.scopeId = :scopeId)))
            order by assignment.id
            """)
    List<UserRoleAssignment> findActiveForScope(@Param("userId") Long userId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId,
            @Param("now") Instant now);

    @EntityGraph(attributePaths = { "role", "role.parentRole" })
    @Query("""
            select assignment from UserRoleAssignment assignment
            where assignment.user.id = :userId
              and assignment.role.id = :roleId
              and assignment.scopeType = :scopeType
              and ((assignment.scopeId is null and :scopeId is null) or assignment.scopeId = :scopeId)
              and assignment.revokedAt is null
            """)
    Optional<UserRoleAssignment> findLiveExisting(@Param("userId") Long userId,
            @Param("roleId") UUID roleId,
            @Param("scopeType") String scopeType,
            @Param("scopeId") String scopeId);

    @Query("select count(assignment) from UserRoleAssignment assignment where assignment.role.id = :roleId and assignment.revokedAt is null")
    long countLiveByRoleId(@Param("roleId") UUID roleId);

    Optional<UserRoleAssignment> findByIdAndUser_Id(Long id, Long userId);
}
