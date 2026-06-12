import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  PageHeader,
  Select,
  Spinner,
  Table,
  Td,
  Th
} from "@/shared/ui";
import { useCourses } from "../hooks";

const STATUS_OPTIONS = ["", "DRAFT", "PUBLISHED", "ARCHIVED"];

export function CourseListPage() {
  const [status, setStatus] = useState("");
  const { data: courses, isLoading, isError, error } = useCourses(status || undefined);

  return (
    <div>
      <PageHeader
        title="Khóa học"
        description="Quản lý danh mục, xuất bản và lưu trữ khóa học"
        actions={
          <Link to="new">
            <Button>
              <Plus size={16} />
              Tạo khóa học
            </Button>
          </Link>
        }
      />
      <Card>
        <CardHeader
          title="Danh sách khóa học"
          actions={
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-44">
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s || "Tất cả trạng thái"}
                </option>
              ))}
            </Select>
          }
        />
        {isLoading && <Spinner />}
        {isError && <ErrorState error={error} />}
        {!isLoading && !isError && courses && courses.length === 0 && (
          <EmptyState message="Chưa có khóa học nào" />
        )}
        {!isLoading && !isError && courses && courses.length > 0 && (
          <Table>
            <thead>
              <tr>
                <Th>Mã</Th>
                <Th>Tiêu đề</Th>
                <Th>Cấp độ</Th>
                <Th>Trạng thái</Th>
                <Th>Chủ sở hữu</Th>
              </tr>
            </thead>
            <tbody>
              {courses.map((course) => (
                <tr key={course.id} className="hover:bg-slate-50">
                  <Td>
                    <Link className="font-medium text-brand-600 hover:underline" to={course.id}>
                      {course.code}
                    </Link>
                  </Td>
                  <Td>{course.title}</Td>
                  <Td>{course.level}</Td>
                  <Td>
                    <Badge value={course.status} />
                  </Td>
                  <Td>{course.ownerId}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}
