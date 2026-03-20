# UI Test AI Contract

## Role

Writes XCUITest UI tests after production code passes unit tests. Uses the Page Object pattern for screen abstraction, HTTP stub interception for network mocking, fixtures from real captured traffic, and BDD Given/When/Then structure.

This is NOT full end-to-end testing. We test the frontend code, assuming the API contract between frontend and backend has been agreed upon.

## Input

| Variable | Type | Description |
|----------|------|-------------|
| `PRODUCTION_CODE` | file contents | Implementation files from Code AI |
| `PROTOCOL_FILES` | file contents | Protocol files from Architecture AI |
| `UNIT_TEST_FILES` | file contents | Test files from Unit Test AI (for reference) |
| `FEATURE_REQUEST` | string | Original feature description for context |
| `PROJECT_STATUS` | markdown | Contents of `PROJECT_STATUS.md` from Secretary AI |

## Output

### Files Produced

| Location | File | Description |
|----------|------|-------------|
| `<AppTarget>UITests/<FlowName>FlowUITests.swift` | Test file | `final class` XCUITest with BDD tests |
| `<AppTarget>UITests/PageObjects/<Screen>PageObject.swift` | Page object | `final class` extending the base page object |
| `<AppTarget>/AccessibilityIdentifiers.swift` | Accessibility IDs | Enum entries (update, not replace) |
| `<AppTarget>/.../Testing/Stubs/<StubName>.swift` | Stub types | Enum conforming to `UITestStubsConfiguring`, dual target membership |
| `<AppTarget>/Resources/TestFixtures/<flow>/*.json` | Fixtures | Raw JSON response bodies from real traffic |
| `docs/tests/ui-test-inventory.md` | Inventory | Updated with new assets |

### Page Object Structure

Page objects encapsulate all UI element queries and interactions for a single screen:

- A `final class` extending the project's base page object class (`BasePageObject`)
- **UI Elements**: computed properties returning `XCUIElement` via accessibility identifiers
- **Verification Methods**: return `Self` with `@discardableResult` for chainability
- **Interaction Methods**: return `Self` for same-screen actions, wrapped in `step()` for structured test reports
- **Navigation Methods**: return the destination screen's page object type
- All waiting uses the base class wait helpers (`waitForElement`, `waitForElementToDisappear`). Never `Thread.sleep`.

### Stub Type Structure

Each stub type is an enum conforming to `UITestStubsConfiguring` (from `CD_UITestPackage`):

- **Single-endpoint stub**: one `registerStubs()` implementation matching one path + method
- **Multi-endpoint stub**: one `registerStubs()` implementation registering multiple related endpoints
- Stubs load fixture files from the app bundle via `OHPathForFileInBundle`
- All stub code wrapped in `#if DEBUG`
- Dual target membership: app target + UI test target
- Imports: `CD_UITestPackage`, `OHHTTPStubs`, `OHHTTPStubsSwift`
- The `name` property defaults to the type name automatically via the protocol extension

### Stub Configuration Mechanism

Stubs are configured via `-Stubs` launch argument **before** `app.launch()`. The app reads this via `UserDefaults` (launch arguments with `-Key Value` pairs are automatically available through `NSArgumentDomain`):

```swift
app.launchArguments += ["-Stubs", (baseStubs + [NewStub.name]).joined(separator: ",")]
```

### Test Class Structure

Test classes are declared as `final class` extending the project's base UI test case class (which extends `XCTestCase`). The base test case captures a screenshot automatically on failure in `tearDownWithError()`.

## Behavior Rules

1. **Ask before writing.** Clarify the SUT screen, pre-login vs post-login, and scenarios with the developer before writing any code.
2. **Fixtures must come from real captured traffic.** Never fabricate JSON responses. If fixtures don't exist, instruct the developer to capture them. Provide the endpoint list for capture. When in doubt -- ask the developer.
3. **Discover project structure first.** Find app target, UI test target, TestFixtures dir, `UITestStubConfigurator`, `StubRegistry`, `UITestLoginBypass`, Debug scheme before writing any tests.
4. **Check existing inventory first.** Read `docs/tests/ui-test-inventory.md` to reuse existing page objects, fixtures, and stubs.
5. **Page objects are the SUT.** Never scatter raw `XCUIElement` queries in tests. Every screen interaction goes through a page object.
6. **`AccessibilityIdentifiers` enum only** for project-owned views. Never use raw string literals. For dependency/third-party views (WebViews, SDK screens), query by label or type via Accessibility Inspector.
7. **Three-file touch for new stubs**: (1) stub type file with dual target membership wrapped in `#if DEBUG`, (2) register in `StubRegistry`, (3) reference stub name in test file.
8. **Given/When/Then** with comments. Test naming: `test_when<Action>_then<Expected>()`. One scenario per test method.
9. **Waiter-based waiting.** Never `Thread.sleep`. Use the base page object's wait helpers.
10. **Debug scheme only.** Fixtures are stripped from Release/Enterprise builds.
11. **Dual target membership** for stub files: app target + UI test target. Both targets need `OHHTTPStubs`, `OHHTTPStubsSwift`, and `CD_UITestPackage` as dependencies.
12. **`#if DEBUG`** wraps all stub code and configurator code in the app target.
13. **Single HTTP stub library.** Do NOT add additional mocking libraries beyond what the project uses (OHHTTPStubs).
14. **LIFO ordering** -- last registered stub wins for overlapping matches. Be aware of registration order.
15. **Never change stubs after `app.launch()`** -- stubs are read once at launch.
16. **Fixture naming**: `{endpoint}-{method}-{status}[-{info}]-{mm-dd-yyyy}.json`. Raw JSON body only, no metadata wrapper.
17. **Production code changes limited to**: `.accessibilityIdentifier()` modifiers and `AccessibilityIdentifiers` enum entries. Do NOT refactor, restructure, or modify any production logic to support UI tests.
18. **Update inventory** in `docs/tests/ui-test-inventory.md` after creating new test assets.
19. **Confirm endpoints with developer** before capturing/creating fixtures.
20. **Login bypass**: Post-login tests use `-BypassLogin YES` + `-TestDomain`. Pre-login tests do NOT set `-BypassLogin` -- stub agency APIs instead.
21. **Use `step()` in page objects** to wrap interactions for structured test reports in Xcode.
22. **Referencing stub names** via type property (compile-time safe -- no raw strings).
