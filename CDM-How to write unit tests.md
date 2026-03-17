# How to Write Unit Tests

## 1. Dependency Injection for Testability

### Why Dependency Injection (DI)?

DI makes it easy to swap real collaborators (network, database, filesystem, time, randomness) for test doubles (fakes, stubs, spies, mocks).
That keeps unit tests fast, isolated, and deterministic.

**Goals**

* Isolate the unit’s logic from I/O and global state so it runs purely in memory.
* Control nondeterminism (time, UUIDs, random numbers) by injecting providers instead of calling globals.
* Allow unit tests to inject mocks in place of real dependencies.

**Core Patterns in Swift**

1. Protocol-based seams
2. Constructor (initializer) injection

   ```swift
   protocol RatesProvider { func rates(for userId: String) throws -> TaxRates }
   protocol ClockProtocol { var now: Date { get } }

   struct TaxService {
       let rates: RatesProvider
       let clock: ClockProtocol

       init(rates: RatesProvider, clock: ClockProtocol) {
           self.rates = rates
           self.clock = clock
       }

       func compute(userId: String, amount: Decimal) throws -> Decimal {
           let r = try rates.rates(for: userId).standard
           return amount * r
       }
   }
   ```
3. Closure injection (simple alternative to protocols)

   ```swift
   typealias UUIDGen = () -> UUID
   struct IdService { let generate: UUIDGen }
   ```
4. Environment container (group many dependencies)

   ```swift
   struct Env { let clock: ClockProtocol; let uuid: UUIDGen; let http: HTTPClient }
   ```
5. Default args for production

   ```swift
   struct SystemClock: ClockProtocol { var now: Date { Date() } }
   extension TaxService {
       init(rates: RatesProvider) { self.init(rates: rates, clock: SystemClock()) }
   }
   ```

**What to Inject**

* **I/O boundaries**: HTTP clients, database/repos, filesystem
* **Nondeterminism**: clock/timezone, random/UUID
* **Configuration**: feature flags, endpoints, secrets (never hard-code)

**Minimal End-to-End Example (Swift)**

```swift
import Testing

// 1) Production implementations
struct HttpRates: RatesProvider {
    let client: HTTPClient
    func rates(for userId: String) throws -> TaxRates { /* call API, map */ }
}
struct SystemClock: ClockProtocol { var now: Date { Date() } }

// 2) Unit under test with explicit seams
struct TaxService {
    let rates: RatesProvider
    let clock: ClockProtocol

    func tax(for userId: String, amount: Decimal) throws -> Decimal {
        let rate = try rates.rates(for: userId).standard
        return amount * rate
    }
}

// 3) Test doubles
struct StubRates: RatesProvider {
    let standard: Decimal
    func rates(for _: String) throws -> TaxRates { .init(standard: standard) }
}
struct FixedClock: ClockProtocol { let now: Date }

// 4) Unit test (Swift Testing)
@Test("calculates tax using injected rate provider")
func taxCalculation() throws {
    let svc = TaxService(
        rates: StubRates(standard: 0.12),
        clock: FixedClock(now: ISO8601DateFormatter().date(from: "2025-01-01T00:00:00Z")!)
    )
    #expect(try svc.tax(for: "u1", amount: 100) == 12)
}
```

**Pitfalls to Avoid**

* Hidden singletons/shared mutable state inside the unit.
* Starting servers/containers in unit tests (belongs to integration tests).
* Sleeping to wait for time (inject a fake clock instead).

---

## 2. Unit Test Principles

The purpose of unit tests is to **protect the current implementation**.
They should fail when production code changes in ways that alter behavior.

**Example: Constants trap**

* ❌ Bad: asserting against constants defined in production.
* ✅ Better: assert expected behavior directly.

```swift
// Production code
struct UIConstants {
    static let buttonHeight: Double = 44.0
}
struct MyButton {
    let height: Double = UIConstants.buttonHeight
}

// ❌ Problematic test (tautological - just checks constant against itself)
@Test("button height matches constant")
func buttonHeight() {
    #expect(MyButton().height == UIConstants.buttonHeight)
}

// ✅ Better test (verifies actual expected value)
@Test("button height is 44 points")
func buttonHeight() {
    #expect(MyButton().height == 44.0)
}
```

### FIRST Principles

* **Fast**: Run in milliseconds.
* **Independent (Isolated)**: No coupling/order dependence.
* **Repeatable**: Same result anywhere, anytime.
* **Self-Validating**: Only assertions decide pass/fail.
* **Timely**: Written before/alongside code; guide design.

---

### 1) Fast

* Keep runtime ≤ 0.1s per test.
* Avoid servers, containers, sleep.
* Use fakes instead of real I/O.

### 2) Independent

* Reset global state.
* Use ephemeral resources.
* Randomize test order.

**Example**

```swift
@Test("calculates tax without network using fake provider")
func taxCalculation() throws {
    struct FakeRates: RatesProvider { func rates(for: String) throws -> TaxRates { .init(standard: 0.10) } }
    let svc = TaxService(rates: FakeRates(), clock: FixedClock(now: Date()))
    #expect(try svc.tax(for: "u", amount: 100) == 10)
}
```

---

### 3) Repeatable

* Eliminate flakes (control nondeterminism, stub APIs).
* Avoid hidden dependencies.

### 4) Self-Validating

* No screenshots/log eyeballing.
* Use precise assertions.
* Prefer public API assertions.

**Example**

```swift
@Test("formats money rounded to 2 decimal places")
func moneyFormatting() {
    #expect(Money.format(12.345) == "12.35")
}
```

### 5) Timely

* Write tests **before or alongside** code.
* Add characterization tests before refactors.
* For bugs: write a failing test first, then fix.

---

## 3. Structure of Unit Tests — Given / When / Then

**Why this structure?**

* **Given**: setup state, fakes/mocks
* **When**: perform one action
* **Then**: assert outcomes

**Swift Testing Template**

Swift Testing encourages concise function names with descriptive display names in the `@Test` attribute:

```swift
@Test("should <expected behavior> when <context>")
func conciseName() throws {
    // Given
    // When
    // Then
    #expect(true) // replace with real expectation
}
```

**Examples:**
```swift
@Test("calculates tax using standard rate")
func taxCalculation() throws { }

@Test("throws error when user not found")
func missingUser() throws { }

@Test("formats currency with two decimal places")
func currencyFormatting() throws { }
```

**Benefits of Display Names:**
* **Readability**: Test output shows descriptive sentences, not function names
* **Conciseness**: Function names can be short and simple
* **Flexibility**: Can use spaces, punctuation, and natural language in display names
* **Refactoring**: Changing function name doesn't affect test output display

**Best Practices:**
* Use lowercase, sentence-style display names (e.g., "calculates total price")
* Keep function names short and focused on the subject (e.g., `func priceCalculation()`)
* Display names should read naturally in test reports
* Group related tests in `@Suite` with descriptive suite names

### Example with SUT Factory

```swift
@Suite("Tax Service Tests")
struct TaxServiceTests {
    func makeSUT(
        rates: RatesProvider = StubRates(standard: 0.10),
        clock: ClockProtocol = FixedClock(now: ISO8601DateFormatter().date(from: "2025-01-01T00:00:00Z")!)
    ) -> TaxService {
        TaxService(rates: rates, clock: clock)
    }

    @Test("applies standard rate to calculate tax for amount")
    func taxCalculation() throws {
        // Given
        let sut = makeSUT(rates: StubRates(standard: 0.12))
        let userId = "u1"
        let amount: Decimal = 100

        // When
        let result = try sut.tax(for: userId, amount: amount)

        // Then
        #expect(result == 12)
    }
}
```

### Example Asserting Interactions (Spy)

```swift
struct SpyLogger: Logger {
    private(set) var messages: [String] = []
    mutating func log(_ message: String) { messages.append(message) }
}

@Test("logs tax computation when calculating tax")
func auditLogging() throws {
    // Given
    var logger = SpyLogger()
    let sut = AuditedTaxService(
        inner: TaxService(rates: StubRates(standard: 0.10), clock: FixedClock(now: Date())),
        logger: { logger.log($0) }
    )

    // When
    _ = try sut.tax(for: "u1", amount: 50)

    // Then
    #expect(logger.messages.last == "computed tax: 5.0")
}
```

---

## Swift Testing-Specific Tips

### Assertions

**`#expect`** – For most assertions (similar to XCTest's `XCTAssert*`)
```swift
#expect(result == 42)
#expect(user.name == "Alice")
#expect(!isLoading)
#expect(items.count == 3)
```

**`#require`** – For critical preconditions that must pass (similar to XCTest's `XCTUnwrap`)
* Stops test execution immediately if the requirement fails
* Use for unwrapping optionals or validating preconditions
* Returns the unwrapped value

```swift
@Test("processes valid user data")
func userProcessing() throws {
    // Given
    let response = try fetchUserResponse()
    
    // Use #require to unwrap - test stops here if nil
    let user = try #require(response.user)
    let email = try #require(user.email)
    
    // When - this only runs if requirements above passed
    let result = processUser(user)
    
    // Then
    #expect(result.isValid)
}
```

**When to use `#require` vs `#expect`:**
* Use `#require` when the value is essential for the rest of the test (e.g., unwrapping optionals)
* Use `#expect` for verifying behavior and outcomes
* `#require` stops test execution on failure; `#expect` continues

### Confirmation (Testing Async Callbacks)

**`await confirmation`** – Verifies that a callback or closure is called (similar to XCTest's `XCTestExpectation`)

Use this when testing asynchronous code where you need to verify a completion handler or delegate method is called:

```swift
@Test("calls completion handler after data loads")
func dataLoadingCompletion() async throws {
    // Given
    let service = DataService()
    
    // When & Then
    await confirmation("completion handler called") { confirm in
        service.loadData { result in
            #expect(result.isSuccess)
            confirm() // Signal that the callback was invoked
        }
    }
}

@Test("invokes multiple callbacks")
func multipleCallbacks() async throws {
    await confirmation("delegate called twice", expectedCount: 2) { confirm in
        delegate.onUpdate = { _ in
            confirm() // Called multiple times
        }
        viewModel.performUpdates()
    }
}
```

**Key points:**
* Use `await confirmation` in async test functions
* Call `confirm()` when the expected callback/closure executes
* Can specify `expectedCount` for callbacks that should fire multiple times
* Replaces XCTest's `XCTestExpectation` and `fulfill()`

### Test Organization with `@Suite`

Use `@Suite` to group related tests with descriptive names. You can also nest suites to create a hierarchical test structure:

```swift
@Suite("User Service Tests")
struct UserServiceTests {
    
    @Suite("Authentication")
    struct AuthenticationTests {
        @Test("validates correct credentials")
        func validCredentials() { }
        
        @Test("rejects invalid password")
        func invalidPassword() { }
    }
    
    @Suite("Profile Management")
    struct ProfileTests {
        @Test("updates user profile successfully")
        func profileUpdate() { }
        
        @Test("validates email format")
        func emailValidation() { }
    }
}
```

**Benefits of nested suites:**
* Organizes tests by feature or component
* Creates clear hierarchy in test reports
* Groups setup/teardown logic at appropriate levels
* Makes large test files more navigable

### Other Tips

* Prefer protocols and value types for determinism.
* Use async/await instead of sleeps.
* Inject time/UUID/random for repeatability.
* Keep tests sub-ms, parallelizable, order-independent.
* Leverage display names in `@Test("description")` for readable test output.

---

## Glossary of Test Doubles and Seams

* **Seam**: a point where behavior can be changed (protocol, closure, injected dependency).
* **Stub**: canned answers; verify outputs.
* **Mock**: verify interactions (method calls, args).
* **Spy**: hybrid stub/mock; records calls.
* **Fake**: lightweight working impl (e.g., in-memory DB).
