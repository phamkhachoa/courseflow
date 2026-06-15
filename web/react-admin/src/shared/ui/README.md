# CourseFlow Admin UI Kit

This folder is the internal enterprise UI kit for the admin console.

## Direction

- Use Tailwind tokens from `tailwind.config.ts` instead of one-off colors.
- Prefer these primitives before creating page-local UI: `Button`, `Card`, `CardHeader`,
  `SectionHeader`, `Badge`, `StatusBadge`, `FormField`, `Input`, `Select`, `Textarea`,
  `Notice`, `StatCard`, `Toolbar`, `Table`, `DescriptionList`, `DataState`.
- Keep operational screens dense, scannable, and action-oriented.
- Use `Notice` for readiness warnings, validation summaries, and operator guidance.
- Use `StatCard` for page metrics instead of custom metric cards.
- Use `Toolbar` for filter/search rows so spacing and responsive behavior stay consistent.
- Use `SectionHeader` for titled sub-sections inside a page or panel.
- Use `DescriptionList` for compact key/value details instead of page-local `KeyValue` clones.
- Use `DataState` to keep loading, error, empty, and content priority consistent.

## Tone Map

- `brand`: primary CourseFlow action or navigation.
- `success`: ready, published, completed, healthy.
- `info`: uploaded media, reference data, neutral progress.
- `warning`: draft, missing content, review required.
- `danger`: destructive, revoked, failed, blocked.
- `neutral/slate`: archived, inactive, secondary metadata.

## Enterprise UX Rules

- Every destructive action must use `Button variant="danger"`.
- Every async/error state must use `Spinner`, `EmptyState`, or `ErrorState`.
- New async tables or panels should prefer `DataState` so loading wins over error, error wins over
  empty, and empty wins over content consistently.
- Every content-readiness warning must include the reason and a next action.
- Tables should use `Table`, `Th`, and `Td` so density and borders remain consistent.
