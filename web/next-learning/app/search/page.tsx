import { SearchView } from "@/features/search/SearchView";
import { PageShell } from "@/shared/ui";

export default function SearchPage() {
  return (
    <PageShell
      eyebrow="Khám phá"
      title="Catalog khóa học"
      description="Tìm khóa học, mở chi tiết và bắt đầu học từ một nơi."
    >
      <SearchView />
    </PageShell>
  );
}
