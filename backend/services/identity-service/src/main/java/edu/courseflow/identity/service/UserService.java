package edu.courseflow.identity.service;

import edu.courseflow.commonlibrary.exception.BadRequestException;
import edu.courseflow.commonlibrary.exception.DuplicatedException;
import edu.courseflow.commonlibrary.exception.NotFoundException;
import edu.courseflow.commonlibrary.web.CurrentUser;
import edu.courseflow.identity.dto.CreateUserRequestDto;
import edu.courseflow.identity.dto.ResetPasswordRequestDto;
import edu.courseflow.identity.dto.UserDto;
import edu.courseflow.identity.model.Role;
import edu.courseflow.identity.model.SystemRoles;
import edu.courseflow.identity.model.User;
import edu.courseflow.identity.model.UserRoleAssignment;
import edu.courseflow.identity.mapper.IdentityMapper;
import edu.courseflow.identity.repository.RoleRepository;
import edu.courseflow.identity.repository.UserRepository;
import edu.courseflow.identity.repository.UserRoleAssignmentRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
@Transactional
public class UserService {

    private final UserRepository users;
    private final RoleRepository roles;
    private final UserRoleAssignmentRepository assignments;
    private final PasswordEncoder passwordEncoder;
    private final IdentityMapper mapper;
    private final PasswordPolicy passwordPolicy;
    private final RefreshTokenService refreshTokenService;
    private final AccessTokenRevocationService accessTokenRevocations;
    private final SecurityAuditService audit;

    public UserService(UserRepository users,
            RoleRepository roles,
            UserRoleAssignmentRepository assignments,
            PasswordEncoder passwordEncoder,
            IdentityMapper mapper,
            PasswordPolicy passwordPolicy,
            RefreshTokenService refreshTokenService,
            AccessTokenRevocationService accessTokenRevocations,
            SecurityAuditService audit) {
        this.users = users;
        this.roles = roles;
        this.assignments = assignments;
        this.passwordEncoder = passwordEncoder;
        this.mapper = mapper;
        this.passwordPolicy = passwordPolicy;
        this.refreshTokenService = refreshTokenService;
        this.accessTokenRevocations = accessTokenRevocations;
        this.audit = audit;
    }

    /**
     * Creates a user and atomically grants a platform role. Non-admin operators may only create
     * plain STUDENT accounts; privileged/operator roles must be granted by an ADMIN. This keeps a
     * TA/INSTRUCTOR operator from escalating by creating a new ADMIN account via user creation.
     */
    public UserDto create(CreateUserRequestDto request, CurrentUser caller) {
        if (users.existsByEmailIgnoreCase(request.email())) {
            throw new DuplicatedException("EMAIL_ALREADY_EXISTS", request.email());
        }
        passwordPolicy.validate(request.password());
        String roleCode = (request.role() == null || request.role().isBlank())
                ? SystemRoles.STUDENT
                : request.role().toUpperCase();
        Role role = roles.findByCode(roleCode)
                .orElseThrow(() -> new BadRequestException("UNKNOWN_ROLE: " + roleCode));
        if (requiresAdminToGrant(role) && (caller == null || !caller.hasRole(SystemRoles.ADMIN))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,
                    "Only ADMIN may create accounts with role " + roleCode);
        }

        User user = new User(
                request.email(),
                passwordEncoder.encode(request.password()),
                request.fullName());
        users.save(user);

        UserRoleAssignment assignment = new UserRoleAssignment(
                user.getId(), role, "PLATFORM", null, callerTag(caller), null);
        assignments.save(assignment);
        audit.record("USER_CREATED", user.getId(), user.getEmail(), callerTag(caller), true, "role=" + roleCode);

        return mapper.toDto(user);
    }

    @Transactional(readOnly = true)
    public UserDto getById(Long id) {
        return users.findById(id)
                .map(mapper::toDto)
                .orElseThrow(() -> new NotFoundException("USER_NOT_FOUND", id));
    }

    @Transactional(readOnly = true)
    public Page<UserDto> list(Pageable pageable) {
        Pageable bounded = pageable.isPaged()
                ? PageRequest.of(pageable.getPageNumber(), Math.min(pageable.getPageSize(), 100), pageable.getSort())
                : PageRequest.of(0, 100);
        return users.findAll(bounded).map(mapper::toDto);
    }

    public void resetPassword(Long userId, ResetPasswordRequestDto request, CurrentUser caller) {
        passwordPolicy.validate(request.newPassword());
        User user = users.findById(userId)
                .orElseThrow(() -> new NotFoundException("USER_NOT_FOUND", userId));
        user.updatePassword(passwordEncoder.encode(request.newPassword()));
        if (!Boolean.FALSE.equals(request.mustChangePassword())) {
            user.requirePasswordChange();
        }
        refreshTokenService.revokeAll(userId, "password-reset");
        accessTokenRevocations.revokeAllForUser(userId);
        audit.record("PASSWORD_RESET", userId, user.getEmail(), callerTag(caller), true,
                Boolean.FALSE.equals(request.mustChangePassword()) ? "mustChange=false" : "mustChange=true");
    }

    public UserDto markEmailVerified(Long userId, CurrentUser caller) {
        User user = users.findById(userId)
                .orElseThrow(() -> new NotFoundException("USER_NOT_FOUND", userId));
        user.markEmailVerified();
        audit.record("EMAIL_VERIFIED", userId, user.getEmail(), callerTag(caller), true, null);
        return mapper.toDto(user);
    }

    private boolean requiresAdminToGrant(Role role) {
        return !SystemRoles.STUDENT.equalsIgnoreCase(role.getCode()) || role.isOperator();
    }

    private String callerTag(CurrentUser caller) {
        if (caller == null) {
            return "system";
        }
        if (caller.id() != null) {
            return "user:" + caller.id();
        }
        return caller.email() == null ? "system" : caller.email();
    }
}
