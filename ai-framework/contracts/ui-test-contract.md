# UI Test AI Contract

## Role

Writes XCUITest UI tests after production code passes unit tests. Follows all conventions from the `cd-ios-tools` write-ui-tests skill exactly: Page Object pattern, OHHTTPStubs for HTTP mocking, fixtures from real captured traffic, and BDD Given/When/Then structure.

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
| `<AppTarget>UITests/<FlowName>FlowUITests.swift` | Test file | XCUITest class with BDD tests |
| `<AppTarget>UITests/PageObjects/<Screen>PageObject.swift` | Page object | `final class` extending `BasePageObject` |
| `<AppTarget>/AccessibilityIdentifiers.swift` | Accessibility IDs | Enum entries (update, not replace) |
| `<AppTarget>/.../Testing/Stubs/<StubName>.swift` | Stub types | `enum` conforming to `UITestStubsConfiguring`, dual target membership |
| `<AppTarget>/Resources/TestFixtures/<flow>/*.json` | Fixtures | Raw JSON response bodies from real traffic |
| `docs/tests/ui-test-inventory.md` | Inventory | Updated with new assets |

### Page Object Structure

```swift
import XCTest

final class <Screen>PageObject: BasePageObject {
    // MARK: - UI Elements
    var titleLabel: XCUIElement {
        app.staticTexts[AccessibilityIdentifiers.<Screen>.titleLabel]
    }

    // MARK: - Verification Methods
    @discardableResult
    func verifyScreenDisplayed() -> Self {
        try waitForElement(titleLabel)
        return self
    }

    // MARK: - Interaction Methods
    @discardableResult
    func tapAction() -> Self {
        actionButton.tap()
        return self
    }

    // MARK: - Navigation Methods
    func tapAndNavigateToNext() -> NextPageObject {
        actionButton.tap()
        return NextPageObject(app: app, testCase: testCase)
    }

    // MARK: - Helper Methods
}
```

### Stub Type Structures

**Single-endpoint stub:**

```swift
#if DEBUG
import CD_UITestPackage
import OHHTTPStubs
import OHHTTPStubsSwift

enum DevicesAvailableGet200Stub: UITestStubsConfiguring {
    static func registerStubs() {
        guard let path = OHPathForFileInBundle("devices-available-get-200-02-27-2026.json", .main) else { return }
        stub(condition: pathEndsWith("/devicepooling/assignabledevices") && isMethodGET()) { _ in
            fixture(filePath: path, status: 200, headers: ["Content-Type": "application/json"])
        }
    }
}
#endif
```

**Multi-endpoint stub (endpoints always called together):**

```swift
#if DEBUG
import CD_UITestPackage
import OHHTTPStubs
import OHHTTPStubsSwift

enum AgencyEntryStubs: UITestStubsConfiguring {
    static func registerStubs() {
        if let path = OHPathForFileInBundle("agencies-get-200-02-27-2026.json", .main) {
            stub(condition: isPath("/api/internal/v1/agencies") && isMethodGET()) { _ in
                fixture(filePath: path, status: 200, headers: ["Content-Type": "application/json"])
            }
        }
        if let path = OHPathForFileInBundle("oauth2-configuration-get-200-02-27-2026.json", .main) {
            stub(condition: isPath("/api/oauth2/configuration") && isMethodGET()) { _ in
                fixture(filePath: path, status: 200, headers: ["Content-Type": "application/json"])
            }
        }
    }
}
#endif
```

### Test File Structure

```swift
import XCTest

class <FlowName>FlowUITests: XCTestCase {

    var app: XCUIApplication!
    var baseStubs: [String] { [AgencyFeatureStubs.name, DeviceHomesGet200Stub.name] }

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--UITesting"]
    }

    override func tearDownWithError() throws {
        app = nil
        try super.tearDownWithError()
    }

    func test_when<Action>_then<Expected>() throws {
        // GIVEN
        app.launchEnvironment["STUBS"] = (baseStubs + [SpecificStub.name]).joined(separator: ",")
        app.launch()

        // WHEN
        let sut = <Screen>PageObject(app: app, testCase: self)
        sut.tapAction()

        // THEN
        sut.verifyExpectedState()
    }

}
```

## Behavior Rules

1. **Fixtures must come from real captured traffic.** Never fabricate JSON responses. If fixtures don't exist, instruct the developer to capture them. Provide the endpoint list for capture. When in doubt about any step — ask the developer.
2. **Discover project structure first.** Find app target, UI test target, TestFixtures dir, StubRegistry, Debug scheme before writing any tests.
3. **Check existing inventory first.** Read `docs/tests/ui-test-inventory.md` to reuse existing page objects, fixtures, and stubs.
4. **Page objects are the SUT.** Never scatter raw `XCUIElement` queries in tests. Every screen interaction goes through a page object.
5. **`AccessibilityIdentifiers` enum only** for project-owned views. Never use raw string literals. For dependency/third-party views (WebViews, SDK screens), query by label or type via Accessibility Inspector.
6. **Three-file touch for new stubs**: (1) stub type file with dual target membership wrapped in `#if DEBUG`, (2) register in `StubRegistry`, (3) reference `StubType.name` in test file.
7. **Given/When/Then** with comments. Test naming: `test_when<Action>_then<Expected>()`. One scenario per test method.
8. **XCTWaiter for waiting.** Never `Thread.sleep`. Use `BasePageObject.waitForElement()` / `waitForElementToDisappear()`.
9. **Debug scheme only.** Fixtures are stripped from Release/Enterprise builds via the "Strip TestFixtures from Release" Run Script.
11. **Dual target membership** for stub files: app target + UI test target. Both targets need `OHHTTPStubs`, `OHHTTPStubsSwift`, `CD_UITestPackage`.
12. **`#if DEBUG`** wraps all stub code and configurator code in the app target.
13. **OHHTTPStubs only** for HTTP mocking. Do NOT add any other mocking library.
14. **LIFO ordering** — last registered stub wins for overlapping matches. Be aware of registration order.
15. **Never change stubs after `app.launch()`** — stubs are read once at launch.
16. **Fixture naming**: `{endpoint}-{method}-{status}[-{info}]-{mm-dd-yyyy}.json`. Raw JSON body only, no metadata wrapper.
17. **Production code changes limited to**: `.accessibilityIdentifier()` modifiers and `AccessibilityIdentifiers` enum entries. Do NOT refactor, restructure, or modify any production logic, ViewModels, Services, or views to support UI tests.
18. **Update inventory** in `docs/tests/ui-test-inventory.md` after creating new test assets.
