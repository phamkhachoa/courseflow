import type { LucideIcon } from "lucide-react";
import {
  Award,
  BarChart3,
  Bell,
  BookOpen,
  Building2,
  BadgePercent,
  ClipboardCheck,
  ClipboardList,
  FileText,
  Image,
  LayoutDashboard,
  ListTree,
  MessageSquare,
  PenSquare,
  Search,
  ShieldCheck,
  Timer,
  Users,
  UserSquare2,
  UsersRound,
  Video
} from "lucide-react";

export type ModuleEntry = {
  /** Path relative to the admin layout (without leading slash). */
  path: string;
  label: string;
  description: string;
  icon: LucideIcon;
  group: ModuleGroupId;
};

export type ModuleGroupId =
  | "operate"
  | "content"
  | "assessment"
  | "learners"
  | "communication"
  | "system";

export type ModuleGroup = {
  id: ModuleGroupId;
  label: string;
  description: string;
};

/**
 * Single source of truth for backoffice navigation. The sidebar renders from
 * this list and the router mounts one route group per module.
 */
export const moduleRegistry: ModuleEntry[] = [
  { path: "dashboard", label: "Tổng quan", description: "Trung tâm điều phối", icon: LayoutDashboard, group: "operate" },
  { path: "analytics", label: "Phân tích", description: "Hoàn thành & rủi ro", icon: BarChart3, group: "operate" },
  { path: "incentives", label: "Khuyến mãi", description: "Campaign, coupon & redemption ops", icon: BadgePercent, group: "operate" },
  { path: "search", label: "Tìm nhanh", description: "Nhảy tới khóa học", icon: Search, group: "operate" },
  { path: "courses", label: "Khóa học", description: "Danh mục, công khai, lưu trữ", icon: BookOpen, group: "content" },
  { path: "authoring", label: "Biên soạn", description: "Soạn thảo và duyệt khóa", icon: PenSquare, group: "content" },
  { path: "course-modules", label: "Lộ trình học", description: "Chương, bài học & tiến độ", icon: ListTree, group: "content" },
  { path: "media", label: "Kho học liệu", description: "Video, tài liệu & asset", icon: Image, group: "content" },
  { path: "assignments", label: "Bài tập", description: "Bài tập & bài nộp", icon: ClipboardList, group: "assessment" },
  { path: "quizzes", label: "Bài thi", description: "Bài thi, câu hỏi & lượt làm", icon: ClipboardCheck, group: "assessment" },
  { path: "gradebook", label: "Bảng điểm", description: "Điểm & trọng số", icon: FileText, group: "assessment" },
  { path: "peer-review", label: "Chấm chéo", description: "Luồng peer review", icon: UsersRound, group: "assessment" },
  { path: "enrollments", label: "Ghi danh", description: "Ghi danh & danh sách chờ", icon: UserSquare2, group: "learners" },
  { path: "certificates", label: "Chứng chỉ", description: "Cấp, thu hồi, xác minh", icon: Award, group: "learners" },
  { path: "portfolio", label: "Hồ sơ năng lực", description: "Minh chứng theo học viên", icon: FileText, group: "learners" },
  { path: "announcements", label: "Thông báo", description: "Soạn nháp & công khai", icon: Bell, group: "communication" },
  { path: "discussions", label: "Thảo luận", description: "Chủ đề & kiểm duyệt", icon: MessageSquare, group: "communication" },
  { path: "live-sessions", label: "Lớp trực tuyến", description: "Live & webinar", icon: Video, group: "communication" },
  { path: "deadlines", label: "Hạn chót", description: "Chính sách & nhắc hạn", icon: Timer, group: "communication" },
  { path: "notifications", label: "Thông báo hệ thống", description: "Hộp thư & tuỳ chọn", icon: Bell, group: "communication" },
  { path: "users", label: "Người dùng", description: "Tài khoản & trạng thái", icon: Users, group: "system" },
  { path: "roles", label: "Vai trò", description: "Vai trò & phân quyền", icon: ShieldCheck, group: "system" },
  { path: "organization", label: "Tổ chức", description: "Phòng ban, kỳ, lớp", icon: Building2, group: "system" }
];

export const moduleGroups: ModuleGroup[] = [
  { id: "operate", label: "Vận hành", description: "Điều phối, phân tích và tìm nhanh" },
  { id: "content", label: "Nội dung học", description: "Khóa học, lộ trình và học liệu" },
  { id: "assessment", label: "Đánh giá", description: "Bài tập, bài thi và điểm" },
  { id: "learners", label: "Người học", description: "Ghi danh, chứng chỉ và portfolio" },
  { id: "communication", label: "Tương tác", description: "Thông báo, Q&A, live và deadline" },
  { id: "system", label: "Hệ thống", description: "Người dùng, quyền và tổ chức" }
];

export const groupedModuleRegistry = moduleGroups.map((group) => ({
  ...group,
  modules: moduleRegistry.filter((module) => module.group === group.id)
}));
