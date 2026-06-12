package edu.courseflow.identity.mapper;

import edu.courseflow.commonlibrary.mapper.CourseFlowMapperConfig;
import edu.courseflow.identity.dto.AuthzDtos.AssignmentDto;
import edu.courseflow.identity.dto.AuthzDtos.PermissionDto;
import edu.courseflow.identity.dto.AuthzDtos.PermissionGrantDto;
import edu.courseflow.identity.dto.AuthzDtos.RoleDto;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.model.Permission;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.RolePermissionGrant;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserRoleAssignment;
import java.util.List;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;

@Mapper(config = CourseFlowMapperConfig.class)
public interface IdentityMapper {

    UserDto toDto(User user);

    PermissionDto toDto(Permission permission);

    @Mapping(target = "code", source = "permission.code")
    @Mapping(target = "description", source = "permission.description")
    @Mapping(target = "category", source = "permission.category")
    @Mapping(target = "effect", source = "effect")
    PermissionGrantDto toDto(RolePermissionGrant grant);

    @Mapping(target = "id", source = "role.id")
    @Mapping(target = "isSystem", source = "role.system")
    @Mapping(target = "isOperator", source = "role.operator")
    @Mapping(target = "parentRoleId", source = "role.parentRole.id")
    @Mapping(target = "permissions", source = "permissions")
    RoleDto toDto(Role role, List<PermissionGrantDto> permissions);

    @Mapping(target = "roleId", source = "role.id")
    @Mapping(target = "roleCode", source = "role.code")
    @Mapping(target = "roleName", source = "role.name")
    AssignmentDto toDto(UserRoleAssignment assignment);
}
