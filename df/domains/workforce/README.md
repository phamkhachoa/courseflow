# Workforce Data Domain

This domain owns workforce skills, training compliance, readiness and learning intelligence for
employees, partners and organization-managed learners.

## Business Capability

Workforce connects learning activity, roles, skills, mandatory training requirements, certifications
and readiness signals so people operations and business leaders can understand capability gaps and
compliance status.

## First Data Products

| Data product | Purpose | First source or contribution |
|---|---|---|
| `gold.workforce_skill_profile` | Person-level skill, certification and proficiency profile. | CourseFlow course taxonomy, completions, grades and certificates. |
| `gold.training_compliance_status` | Mandatory training completion and overdue status by person, org and requirement. | CourseFlow completion, certificate and assignment signals. |
| `gold.workforce_readiness_daily` | Daily team, role and organization readiness indicators. | CourseFlow learning progress, final grade and certificate outcomes. |

## First Consumers

- People operations for workforce planning and compliance.
- Learning and development for curriculum effectiveness and capability gaps.
- Managers for team readiness and mandatory training follow-up.
- Enterprise reporting for workforce capability KPIs.

## CourseFlow LMS Contribution

CourseFlow LMS contributes course taxonomy, learner-to-organization scope, enrollments, progress,
gradebook outcomes, completion events, certificates and training evidence.

## Future Product Onboarding

- HRIS for employee profile, organization, role, manager and employment status.
- Talent management for skills, goals, performance and career paths.
- Identity directory for active workforce population and access scope.
- Project staffing tools for assignment, utilization and role demand.

## Domain-Specific Rules

- Workforce data products must distinguish employees, contractors, partners and external learners.
- Skill and certification facts must include source evidence and effective dates.
- Mandatory training compliance must preserve requirement version and due-date basis.
- Person-level workforce views require HR access controls and privacy classification.
