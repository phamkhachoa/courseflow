import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type SearchResult = {
  id: string;
  code?: string;
  title: string;
  slug?: string;
  summary?: string;
};

/** Public read-model search. The internal endpoint is an indexing command, not a query. */
export async function searchCourses(q: string): Promise<SearchResult[]> {
  const { data } = await apiClient.get("/v1/search/courses", { params: { q } });
  return unwrapList<SearchResult>(data);
}

/** Re-index a course into the search read model. */
export async function indexCourse(input: {
  courseId: string;
  title: string;
  summary: string;
}): Promise<SearchResult> {
  const { data } = await apiClient.post("/admin/v1/search/courses", input);
  return unwrap<SearchResult>(data);
}
