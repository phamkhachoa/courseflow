import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button, DataState, DescriptionList, SectionHeader, StatusBadge } from ".";

describe("admin UI kit primitives", () => {
  it("maps operational status values to semantic badge tones", () => {
    render(<StatusBadge value="COMMIT_FAILED" />);

    const badge = screen.getByText("COMMIT_FAILED");
    expect(badge).toHaveClass("bg-amber-100");
    expect(badge).toHaveClass("text-amber-700");
  });

  it("renders data state in deterministic priority order", () => {
    const { rerender } = render(
      <DataState loading error={new Error("boom")} empty>
        <p>content</p>
      </DataState>
    );
    expect(screen.getByRole("status")).toHaveTextContent("Đang tải");
    expect(screen.queryByText("content")).not.toBeInTheDocument();

    rerender(
      <DataState error={new Error("boom")} empty>
        <p>content</p>
      </DataState>
    );
    expect(screen.getByText("Không thể tải dữ liệu")).toBeInTheDocument();

    rerender(
      <DataState empty emptyMessage="Chưa có bản ghi">
        <p>content</p>
      </DataState>
    );
    expect(screen.getByText("Chưa có bản ghi")).toBeInTheDocument();

    rerender(
      <DataState>
        <p>content</p>
      </DataState>
    );
    expect(screen.getByText("content")).toBeInTheDocument();
  });

  it("renders dense description values without dropping zero", () => {
    render(
      <DescriptionList
        columns={2}
        items={[
          { label: "Pending", value: 0 },
          { label: "Correlation", value: "corr-1", mono: true }
        ]}
      />
    );

    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("corr-1")).toHaveClass("font-mono");
  });

  it("renders section actions with the shared button primitive", () => {
    render(
      <SectionHeader title="Queue" actions={<Button size="sm">Refresh</Button>} />
    );

    expect(screen.getByRole("heading", { name: "Queue" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });
});
