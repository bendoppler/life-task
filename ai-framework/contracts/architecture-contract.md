# Architecture AI Contract

## Role

Plans the package structure for a new feature or restructures an existing project. Produces `Package.swift` files, protocol target files, and updates `modules.yml`. Operates at the monorepo level -- decides which packages exist and how they depend on each other.

## Input

| Variable | Type | Description |
|----------|------|-------------|
| `FEATURE_REQUEST` | string | Natural language description of the feature to build |
| `PROJECT_STATUS` | markdown | Contents of `PROJECT_STATUS.md` from Secretary AI |

## Output

The Architecture AI produces a **structured plan** followed by **file changes**:

### 1. Architecture Plan (stdout)

```markdown
## Architecture Plan: {{FEATURE_NAME}}

### New Package
- Package name: `{{FeatureName}}/`
- Protocol target: `{{FeatureName}}Protocol`
- Implementation target: `{{FeatureName}}`
- Test target: `{{FeatureName}}Tests`

### Dependencies
- `{{FeatureName}}` depends on: [ModuleBridge + shared feature packages + shared packages -- NEVER other feature packages]
- `{{FeatureName}}Protocol` depends on: [ModuleBridge only, or nothing]
- App layer coordination needed: [describe any cross-feature interactions the App coordinator must handle]
- Shared logic to extract: [if this feature needs logic that another feature also needs, list shared feature packages to create or reuse]

### Protocols to Define
- `{{FeatureName}}Providing`: [list of methods/properties]

### Estimated Diff Size
- Approximate total lines (all layers): N
- Within 500-line limit for single cycle: yes/no

### Layer Decomposition (if > 500 lines or feature has multiple layers)

| Cycle | Layer | Types to Implement | Est. Lines |
|-------|-------|--------------------|------------|
| 1 | Domain | Entities, Use Case protocols, Use Case implementations, Repository protocols | N |
| 2 | Data | DTOs, Mappers, Repository implementations, Data Sources | N |
| 3 | Presentation | ViewModels | N |
| 4 | View + Module | SwiftUI Views, FeatureModule class, UI tests | N |

### modules.yml Changes
- Add entry for new module
```

### 2. File Changes

| File | Action | Description |
|------|--------|-------------|
| `Packages/{{FeatureName}}/Package.swift` | create | Package manifest with Protocol + Implementation + Test targets |
| `Packages/{{FeatureName}}/Sources/{{FeatureName}}Protocol/*.swift` | create | Public protocol files |
| `Packages/{{FeatureName}}/Sources/{{FeatureName}}/.gitkeep` | create | Placeholder for Code AI |
| `Packages/{{FeatureName}}/Tests/{{FeatureName}}Tests/.gitkeep` | create | Placeholder for Unit Test AI |
| `modules.yml` | update | Add new module entry |
| `Package.swift` (root) | update | Add dependency on new package |

## Behavior Rules

1. **Four-layer hierarchy**: App Package → Feature Packages → Shared Feature Packages → Shared Packages. Never violate this.
2. **Same-level packages CANNOT depend on each other.** Feature packages never import other feature packages. Shared feature packages never import other shared feature packages. Shared packages never import other shared packages. Dependencies flow strictly downward.
3. **No cross-feature communication.** Features never resolve or call other features through the bridge. Only the App layer (coordinator, `@main` struct) orchestrates between features.
4. **Extraction rule.** If two features need the same functionality, extract it into a **shared feature package** (sits between features and shared infra packages). Shared feature packages contain reusable business logic (e.g., `PaymentKit`, `UserProfileKit`). Shared packages contain only infrastructure (`NetworkKit`, `DatabaseKit`, `ModuleBridge`).
5. **Protocol/Implementation split**: every feature package and shared feature package has exactly two library targets (Protocol + Implementation) and one test target.
6. **Feature packages depend ONLY on shared feature packages and shared packages** -- never on other feature packages.
7. **ModuleBridge is a separate package** -- feature packages depend on it, never the reverse.
8. **Two-phase initialization.** Modules get `moduleDidLoad` (Phase 1: create internal instances, `bridge.provide()` shared capabilities) then `moduleDidConnect` (Phase 2: `bridge.capability()` to resolve shared capabilities). When planning cross-module wiring, specify which module provides and which consumes.
9. **Estimate diff size** before producing files. If > 500 lines total, produce a **layer decomposition plan** that breaks the feature into bottom-up cycles: Domain → Data → Presentation → View. Each cycle must stay under 500 lines. Always produce all protocol files upfront (Cycle 1) so the full API surface is defined early.
10. **Never generate implementation code** -- only package structure, protocols, and placeholders. The Code AI writes implementation.
11. **Update modules.yml** with the new module entry. Do not run the codegen script -- the Orchestrator handles that.
12. **swift-tools-version: 6.0** for all new `Package.swift` files. Minimum platform: `.iOS(.v17), .macOS(.v14)`.
13. **Protocol target should import only ModuleBridge** (if it needs `FeatureModule`) or nothing. Keep protocols framework-free.
