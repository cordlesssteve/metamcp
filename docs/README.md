# Documentation

**Status:** MIGRATED TO UNIVERSAL PROJECT DOCUMENTATION STANDARD
**Last Updated:** 2025-09-19

This directory follows the Universal Project Documentation Standard v2.0.

## Current Documentation Structure

### Status Files (Root Level)
- `../CURRENT_STATUS.md` - Current project reality and progress
- `../ACTIVE_PLAN.md` - Currently executing plan

### Plans Management
- `plans/archived/` - Completed plans
- `plans/superseded/` - Replaced plans

### Progress Tracking
- `progress/2025-09/` - Weekly progress logs

### Reference Documentation (9-Category System)
- `reference/01-architecture/` - System design & ADRs
- `reference/02-apis/` - API documentation (includes legacy i18n docs)
- `reference/03-development/` - Development practices & setup
- `reference/04-deployment/` - Operations & infrastructure
- `reference/05-security/` - Security policies
- `reference/06-integrations/` - External integrations
- `reference/07-troubleshooting/` - Support guides
- `reference/08-performance/` - Performance documentation
- `reference/09-compliance/` - Regulatory compliance

### Legacy Documentation (Archived)
- `reference/02-apis/legacy-i18n-en/` - Original English docs
- `reference/02-apis/legacy-i18n-cn/` - Original Chinese docs
- `reference/essentials/` - Original essential documentation

## Mintlify Documentation Building

The documentation is built using Mintlify and deployed to https://docs.metamcp.com

### Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mint) to preview your documentation changes locally:

```
npm i -g mint
```

Run the following command at the root of your documentation, where your `docs.json` is located:

```
mint dev
```

View your local preview at `http://localhost:3000`.

### Publishing changes

Install our GitHub app from your [dashboard](https://dashboard.mintlify.com/settings/organization/github-app) to propagate changes from your repo to your deployment. Changes are deployed to production automatically after pushing to the default branch.

For more information about contributing to the documentation, see the [Contributing Guide](../CONTRIBUTING.md).
