import { useMemo } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/shared/api/query-keys";
import { getUserAssignments, type RoleAssignment } from "@/modules/roles/api";
import { listUsers, type AdminUser } from "./api";

function isLearnerUser(user: AdminUser) {
  const role = user.role?.toUpperCase() ?? "";
  return role.includes("STUDENT") || role.includes("LEARNER");
}

function isStaffUser(user: AdminUser) {
  const role = user.role?.toUpperCase() ?? "";
  return role.includes("ADMIN") || role.includes("INSTRUCTOR") || role.includes("TEACHER") || role.includes("STAFF");
}

function isLearnerAssignment(assignment: RoleAssignment) {
  const code = assignment.roleCode?.toUpperCase() ?? "";
  return code.includes("STUDENT") || code.includes("LEARNER");
}

function isStaffAssignment(assignment: RoleAssignment) {
  const code = assignment.roleCode?.toUpperCase() ?? "";
  return (
    code.includes("ADMIN") ||
    code.includes("INSTRUCTOR") ||
    code.includes("PROFESSOR") ||
    code.includes("TEACHER") ||
    code.includes("STAFF") ||
    code === "TA"
  );
}

export function adminUserLabel(user?: AdminUser, fallbackId?: string) {
  if (!user) return fallbackId ? `User ${fallbackId}` : "Tất cả học viên";
  return `${user.fullName || user.email} · ${user.email}`;
}

export function useLearnerUsers() {
  const usersQuery = useQuery({
    queryKey: queryKeys.users.list,
    queryFn: listUsers,
    staleTime: 60_000
  });
  const allUsers = usersQuery.data ?? [];

  const roleAssignments = useQueries({
    queries: allUsers.map((user) => ({
      queryKey: queryKeys.roles.assignments(String(user.id)),
      queryFn: () => getUserAssignments(String(user.id)),
      staleTime: 60_000,
      retry: 1
    }))
  });

  const userById = useMemo(() => {
    const map = new Map<string, AdminUser>();
    for (const user of allUsers) map.set(String(user.id), user);
    return map;
  }, [allUsers]);

  const roleAssignmentsByUserId = useMemo(() => {
    const map = new Map<string, RoleAssignment[]>();
    allUsers.forEach((user, index) => {
      const assignments = roleAssignments[index]?.data;
      if (assignments) map.set(String(user.id), assignments);
    });
    return map;
  }, [allUsers, roleAssignments]);

  const roleQueriesDone = roleAssignments.length > 0 && roleAssignments.every((query) => query.isSuccess || query.isError);
  const roleQueriesLoading = roleAssignments.some((query) => query.isPending);

  const learnerUsers = useMemo(() => {
    const assignedLearners = allUsers.filter((user) =>
      roleAssignmentsByUserId.get(String(user.id))?.some(isLearnerAssignment)
    );
    if (assignedLearners.length || roleQueriesDone) return assignedLearners;

    const inlineLearners = allUsers.filter(isLearnerUser);
    return inlineLearners.length ? inlineLearners : allUsers.filter((user) => !isStaffUser(user));
  }, [allUsers, roleAssignmentsByUserId, roleQueriesDone]);

  const staffUsers = useMemo(() => {
    const assignedStaff = allUsers.filter((user) =>
      roleAssignmentsByUserId.get(String(user.id))?.some(isStaffAssignment)
    );
    if (assignedStaff.length || roleQueriesDone) return assignedStaff;
    return allUsers.filter(isStaffUser);
  }, [allUsers, roleAssignmentsByUserId, roleQueriesDone]);

  return {
    allUsers,
    learnerUsers,
    roleQueriesLoading,
    staffUsers,
    userById,
    usersQuery
  };
}
