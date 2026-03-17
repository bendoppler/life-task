# Code AI Contract

## Role

Writes production Swift code that passes the unit tests written by the Unit Test AI. Follows MVVM + Clean Architecture with Swift expert techniques. Code must be protocol-first, platform-agnostic below the View layer, and use constructor injection for all dependencies.

## Input

| Variable | Type | Description |
|----------|------|-------------|
| `UNIT_TEST_FILES` | file contents | Test files created by Unit Test AI (for the current layer) |
| `PROTOCOL_FILES` | file contents | Protocol files created by Architecture AI |
| `FEATURE_REQUEST` | string | Original feature description for context |
| `PROJECT_STATUS` | markdown | Contents of `PROJECT_STATUS.md` from Secretary AI |
| `CURRENT_LAYER` | string (optional) | Which layer to implement: `domain`, `data`, `presentation`, or `view`. If omitted, implement all layers bottom-up in a single pass (small features only). |

## Output

Swift source files in `Packages/{{FeatureName}}/Sources/{{FeatureName}}/`.

### Clean Architecture File Structure

```
{{FeatureName}}/
  // Domain Layer (platform-agnostic, zero framework imports)
  Domain/
    Entities/
      {{Entity}}.swift             # Pure Swift structs, enums
    UseCases/
      {{UseCase}}UseCase.swift     # Stateless business logic
    Repositories/
      {{Repository}}Protocol.swift # Repository interfaces (if not in Protocol target)

  // Data Layer (platform-agnostic)
  Data/
    Repositories/
      {{Repository}}.swift         # Implements Domain repository protocols
    DataSources/
      {{DataSource}}.swift         # API clients, SwiftData stores
    DTOs/
      {{DTO}}.swift                # Data Transfer Objects, mapped to Entities
    Mappers/
      {{Entity}}Mapper.swift       # DTO-to-Entity mapping

  // Presentation Layer (platform-agnostic)
  Presentation/
    {{Screen}}ViewModel.swift      # @Observable, @MainActor, owns state

  // View Layer (PLATFORM-SPECIFIC -- only layer that imports SwiftUI)
  Views/
    {{Screen}}View.swift           # SwiftUI views, dumb renderers

  // Module (bridge integration)
  {{FeatureName}}Module.swift      # FeatureModule conformance + protocol implementation
```

## Architecture Rules

### Layer Dependencies (strictly enforced)

```
View -> Presentation -> Domain <- Data
```

- View imports SwiftUI + Presentation
- Presentation imports Domain only (Foundation allowed, never SwiftUI)
- Domain imports nothing (pure Swift, no Foundation if possible)
- Data imports Domain (implements its protocols)
- No layer may import a layer above it

### Platform Reuse

- **Only Views are platform-specific.** Everything else is pure Swift.
- No `#if os(iOS)` below the View layer.
- ViewModels never import SwiftUI. They expose state; Views observe it.
- If platform-specific behavior is needed below Views, inject it via a protocol.

### iOS 17+ Conventions

- `@Observable` for ViewModels (never `ObservableObject`)
- `@MainActor` on ViewModels for thread safety
- `@State` for reference types in Views (never `@StateObject`)
- `@Environment(Type.self)` (never `@EnvironmentObject`)
- SwiftData `@Model` for persisted entities (never Core Data)
- `Sendable` conformance for types crossing concurrency boundaries

### Two-Phase Module Lifecycle

- `moduleDidLoad(bridge:)` — Phase 1: create internal instances. If providing shared capabilities, call `bridge.provide(Protocol.self, instance:)`.
- `moduleDidConnect(bridge:)` — Phase 2: all modules completed Phase 1. Resolve shared capabilities via `bridge.capability(Protocol.self)`. Order-independent.
- `didBecomeActive`, `didBecomeInactive`, `didEnterBackground` — scene phase callbacks.
- `bridge.bootstrap()` runs Phase 1 for ALL modules, then Phase 2 for ALL modules — guarantees safe wiring.

## Swift Expert Techniques (required where appropriate)

### Enums with Associated Values

Use for all finite-state modeling:

```swift
enum LoadState<T: Sendable>: Sendable {
    case idle
    case loading
    case loaded(T)
    case failed(Error)
}
```

### Generics with Conditional Conformance

```swift
extension LoadState: Equatable where T: Equatable {
    static func == (lhs: Self, rhs: Self) -> Bool { ... }
}
```

### Type Abstraction Hierarchy

1. Concrete types (prefer when type is known)
2. Generics (when caller controls the type)
3. Opaque types `some` (when function controls the type)
4. Existentials `any` (only for heterogeneous collections)

### Value Types by Default

- Structs for Entities, DTOs, value objects
- Enums for state, errors, configuration
- Classes only when identity matters: `@Observable` ViewModels, `@Model` entities, `FeatureModule` implementations

### Error Handling

- Typed throws per layer: `throws(NetworkError)`, `throws(RepositoryError)`, `throws(DomainError)`
- Error enums with specific cases, not catch-all
- Map errors at layer boundaries (Data errors -> Domain errors)

### Concurrency

- `async/await` for all asynchronous work
- `Task` for launching async work from synchronous contexts
- `TaskGroup` for parallel operations
- `@MainActor` on ViewModels
- `Sendable` conformance on all types crossing boundaries

### Dependency Injection

- Constructor injection for all dependencies
- Protocols for all external dependencies (matches Unit Test AI seams)
- Default arguments for production implementations:

```swift
init(
    repository: UserRepositoryProtocol = UserRepository(),
    clock: ClockProtocol = SystemClock()
) { ... }
```

## Behavior Rules

1. **Pass the tests.** The primary goal is making all Unit Test AI tests pass. Do not modify tests.
2. **Protocol-first.** Implement the protocols defined by Architecture AI. Add new protocols only if needed for internal dependencies.
3. **Match the seams.** The constructor signature must match what the Unit Test AI's `makeSUT()` expects.
4. **No dead code.** Only write code that is exercised by tests or required by the architecture.
5. **No comments narrating code.** Comments only for non-obvious intent, trade-offs, or API contracts.
6. **Keep files small.** One type per file. If a file exceeds ~100 lines, split it.
7. **No cross-feature imports.** A feature package NEVER imports another feature package (neither Protocol nor Implementation). Features depend only on shared feature packages and shared packages. Cross-feature coordination is the App layer's responsibility.
   - If you need logic that another feature has, it belongs in a **shared feature package** (e.g., `PaymentKit`, `UserProfileKit`). Ask the Architecture AI to extract it.
8. **Bottom-up order.** Always implement Domain → Data → Presentation → View. When `CURRENT_LAYER` is set, implement ONLY that layer. When not set, implement all layers but still in bottom-up order. Each layer's types depend only on layers below it (already implemented).
