# Product Onboarding Validation

Product onboarding is validated by `enterprise_df.products` and runs as part of:

```bash
cd df
make validate
```

## What Is Checked

- `products/<product-code>/onboarding.yaml` exists.
- `product.code` matches the folder name.
- Product ownership, sponsor, technical owner, data steward and residency metadata are present.
- Tenant mapping is explicit through `enterpriseTenantKey` and `productOrgKey`.
- Product-level governance defaults are present: classification, PII flag, tenant isolation,
  default retention policy, default access personas, consumer contract, release evidence profile,
  lineage, catalog registration and DSAR stance.
- Governance defaults reference registered personas, consumer contracts, retention policies and
  release evidence profiles.
- Source systems declare domains, services and supported publication modes.
- First-slice topics and data products use valid platform naming.
- `firstSlice.contractStatus=existing` requires topics under `contracts/topics/` and data products
  under `contracts/data-products/`.
- `firstSlice.contractStatus=planned` lets a new product register a future first slice before
  contracts are created.
- Referenced topic and data product contracts declare the same `product` code.
- Every topic and data product contract is owned by an onboarded product.
- Contract `domain` values are enterprise data domains from `domains/registry.yaml`; onboarding
  source-system domains can be more product-specific.

## Scaffold Command

```bash
enterprise-df product-scaffold \
  --root . \
  --product-code crm-sales \
  --name "CRM Sales" \
  --domain customer \
  --business-sponsor customer-growth-lead \
  --product-owner crm-sales-po \
  --technical-owner crm-sales-sa
```

The command creates `products/<product-code>/onboarding.yaml`, a product README, a product-domain
notes folder and a product-use-case notes folder. It does not create contracts; those remain a
separate reviewed step.

## Why This Matters

The platform is shared across many enterprise products. Product onboarding metadata is the first line
of defense against orphaned data products, ambiguous ownership, undocumented source systems and
contracts that accidentally belong to the wrong product.
