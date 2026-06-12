import { getFeaturedCourses } from "@/features/course-catalog/api";
import { MyLearningDashboard } from "@/features/my-learning/MyLearningDashboard";

export default async function HomePage() {
  const courses = await getFeaturedCourses();
  return <MyLearningDashboard initialCourses={courses.slice(0, 12)} />;
}
