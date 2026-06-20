# Council 0066 - LLM Provider Secret Rotation Control Plane

Date: 2026-06-17

## Attendees

- SA AI Platform
- SA AI Engineer
- PO/BA
- Governance Reviewer
- Admin/Ops

## Decision

The AI Platform now treats live LLM provider credentials as a governed control-plane concern, not as application configuration. A provider can move from contract stub to live network only when secret-manager refs, runtime secret resolution, rotation automation refs, rotation evidence refs and rotation drill status are all present and tenant-safe.

## Delivered

- Added `llm-provider-secret-rotation-policy-v1` with allowed secret manager schemes, rotation schemes, evidence schemes and required live controls.
- Added `llm-provider-secret-rotation-v1` report builder and snapshot writer.
- Kept contract-stub providers CI-safe with `local://contract-stub/no-secret` and `not_required` rotation refs.
- Added live-provider validation paths for `vault://`, `aws-sm://`, `gcp-sm://` and `azure-kv://` refs without storing secret values.
- Projected secret rotation status into the operating cockpit, Admin/Ops dashboard and CLI output.

## PO/BA Translation

Business users can now ask whether the platform is ready to connect a real hosted LLM provider without reading service code. The answer is visible as a report-backed status:

- Current state: contract stubs are safe and do not require live rotation.
- Future live state: rollout is blocked unless secret manager binding, rotation automation and evidence refs pass.

## SA AI Platform Notes

- Secret values remain omitted from reports.
- The policy validates refs and evidence, not credentials.
- Live provider activation remains a controlled product/platform decision.

## SA AI Engineer Notes

- The test suite includes a valid live `vault://` binding scenario.
- Plaintext `sk-` style refs are rejected by the secret rotation report.
- Runtime secret probe evidence must align with the rotation control report.

## Admin/Ops Notes

- Dashboard now shows `LLM Secrets`.
- A future missing live rotation state will create `configure_llm_provider_secret_rotation` delivery work.
- Current contract-stub state remains safe for CI and local demo usage.

## Next Step

Enable a real network LLM provider only after product approval, tenant scope approval and a live secret-manager ref are available outside source control.
