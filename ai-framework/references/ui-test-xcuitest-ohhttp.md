# UI Test Reference: XCUITest + OHHTTPStubs

This is a project-specific reference for UI testing with XCUITest, OHHTTPStubs, and the CD_UITestPackage library. Include this reference when your project uses these libraries.

## Libraries

- **OHHTTPStubs** + **OHHTTPStubsSwift** -- HTTP stub interception at the `URLProtocol` level
- **CD_UITestPackage** -- provides `BasePageObject`, `UITestStubsConfiguring` protocol, `StubRegistry`, `UITestStubConfigurator`, and `UITestLoginBypass`
- **BasePageObject** -- base class for all page objects, provides `waitForElement()`, `waitForElementToDisappear()`, `step()`, and `attachScreenshot()`

## Page Object Example

```swift
import XCTest

final class TaskListPageObject: BasePageObject {

    // MARK: - UI Elements

    var titleLabel: XCUIElement {
        app.staticTexts[AccessibilityIdentifiers.TaskList.titleLabel]
    }
    var addButton: XCUIElement {
        app.buttons[AccessibilityIdentifiers.TaskList.addButton]
    }

    // MARK: - Verification Methods

    @discardableResult
    func verifyScreenDisplayed() -> Self {
        try waitForElement(titleLabel)
        return self
    }

    // MARK: - Interaction Methods

    @discardableResult
    func tapAdd() -> Self {
        step("Tap Add button") { _ in
            addButton.tap()
            return self
        }
    }

    // MARK: - Navigation Methods

    func tapAddAndNavigateToDetail() -> TaskDetailPageObject {
        step("Tap Add and navigate to detail") { _ in
            addButton.tap()
            return TaskDetailPageObject(app: app, testCase: testCase)
        }
    }
}
```

### XCTActivity (Test Activities)

`BasePageObject` provides `step()` and `attachScreenshot()` helpers that wrap `XCTContext.runActivity(named:block:)` to group test steps in Xcode's test report:

```swift
// BasePageObject helpers
@discardableResult
func step<T>(_ name: String, block: (XCTActivity) -> T) -> T {
    XCTContext.runActivity(named: name) { activity in
        block(activity)
    }
}

func attachScreenshot(to activity: XCTActivity, named name: String) {
    let screenshot = XCUIScreen.main.screenshot()
    let attachment = XCTAttachment(screenshot: screenshot)
    attachment.name = name
    attachment.lifetime = .keepAlways
    activity.add(attachment)
}
```

This produces a collapsible tree in Xcode's test report:
```
testAdminCanAssignHome
  Tap Set Pooling Location
  Tap pooling dropdown
  Select device home 'home-1'
  Tap Assign Pooling Location
  Verify device home name 'home-1' displayed
```

## Stub Type Examples

### Single-Endpoint Stub

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

### Multi-Endpoint Stub

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

The `name` property defaults to the type name automatically via the `UITestStubsConfiguring` protocol extension. OHHTTPStubs uses **LIFO ordering** -- last registered stub wins for overlapping matches.

## StubRegistry Example

Register stubs in `AppDelegate.swift`:

```swift
#if DEBUG
import CD_UITestPackage

let registry = StubRegistry()
    .register(AgencyEntryStubs.self)
    .register(DevicesAvailableGet200Stub.self)
    // ... existing registrations ...

UITestStubConfigurator.configureIfNeeded(registry: registry)
if UITestLoginBypass.shouldBypass {
    UITestLoginBypass.performBypass(/* project-specific dependencies */)
    // Navigate to the main view
}
#endif
```

## Test File Example

```swift
import XCTest

final class TaskListFlowUITests: XCTestCase {

    var app: XCUIApplication!
    var baseStubs: [String] { [AgencyFeatureStubs.name, DeviceHomesGet200Stub.name] }

    override func setUpWithError() throws {
        try super.setUpWithError()
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["--UITesting"]
        // Post-login: bypass WebView login
        app.launchArguments += ["-BypassLogin", "YES"]
        app.launchArguments += ["-TestDomain", "myagency.example.com"]
    }

    override func tearDownWithError() throws {
        if let failureCount = testRun?.failureCount, failureCount > 0 {
            let screenshot = XCUIScreen.main.screenshot()
            let attachment = XCTAttachment(screenshot: screenshot)
            attachment.name = "Failure Screenshot"
            attachment.lifetime = .keepAlways
            add(attachment)
        }
        app = nil
        try super.tearDownWithError()
    }

    // MARK: - Happy Path

    func test_whenLoadingTasks_thenShowsTaskList() throws {
        // Given
        let stubs = (baseStubs + [TasksGet200Stub.name]).joined(separator: ",")
        app.launchArguments += ["-Stubs", stubs]
        app.launch()

        // When
        let sut = TaskListPageObject(app: app, testCase: self)

        // Then
        sut.verifyScreenDisplayed()
    }

    // MARK: - Error Cases

    func test_whenServerError_thenShowsErrorMessage() throws {
        // Given
        let stubs = (baseStubs + [TasksGet500Stub.name]).joined(separator: ",")
        app.launchArguments += ["-Stubs", stubs]
        app.launch()

        // When -- app loads

        // Then
        let sut = TaskListPageObject(app: app, testCase: self)
        sut.verifyErrorDisplayed()
    }
}
```

## Login Bypass

- **Post-login tests:** Set `-BypassLogin YES` + `-TestDomain` + app-specific arguments in `setUpWithError()`
- **Pre-login tests:** Do NOT set `-BypassLogin` -- stub agency APIs instead

## Running UI Tests

Always use the **Debug scheme**:

```bash
xcodebuild test -scheme <AppTarget>-Debug -destination 'platform=iOS Simulator,name=iPad (A16)'
```

Fixtures are stripped from Release/Enterprise builds.

## Dependencies Setup

Both app target and UI test target need these dependencies:
- `OHHTTPStubs`
- `OHHTTPStubsSwift`
- `CD_UITestPackage`

All stub files need **dual target membership** (app + UI test).
