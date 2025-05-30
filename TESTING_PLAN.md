# Testing Plan for Thywill Prayer Application

## Overview
This document outlines the comprehensive testing strategy for the Thywill prayer application, covering both automated functional testing of the running application and unit tests for individual components.

## 1. Automated Functional Testing

### 1.1 Test Framework Selection
- **Framework**: pytest with httpx for async testing
- **Test Client**: FastAPI TestClient for API endpoint testing
- **Browser Testing**: Playwright for end-to-end UI testing
- **Database**: SQLite in-memory database for test isolation

### 1.2 Core Functional Test Areas

#### Authentication & Authorization
- [ ] User registration via invite tokens
- [ ] Multi-device authentication workflows
- [ ] Session management and expiration
- [ ] Admin vs regular user permissions
- [ ] Rate limiting for auth requests
- [ ] Authentication request approval flows

#### Prayer Management
- [ ] Prayer submission and LLM generation
- [ ] Prayer flagging/unflagging by admins
- [ ] Prayer marking (praying for prayers)
- [ ] Feed filtering (all, new_unprayed, most_prayed, etc.)
- [ ] Prayer statistics and counts

#### User Interface Workflows
- [ ] Navigation between different feeds
- [ ] HTMX dynamic updates (marking prayers, flagging)
- [ ] Responsive design on mobile/desktop
- [ ] Error handling and user feedback

#### Administrative Functions
- [ ] Admin panel access and functionality
- [ ] Bulk operations for authentication requests
- [ ] Audit log viewing and security monitoring
- [ ] User management capabilities

### 1.3 Test Data Management
- [ ] Factory functions for creating test users, prayers, and sessions
- [ ] Database seeding scripts for consistent test environments
- [ ] Test data cleanup between test runs

### 1.4 Integration Test Coverage
- [ ] Database operations and migrations
- [ ] External API integrations (Anthropic Claude)
- [ ] Session storage and retrieval
- [ ] HTMX request/response cycles

## 2. Unit Testing

### 2.1 Model Testing
- [ ] SQLModel validation and constraints
- [ ] Database field defaults and relationships
- [ ] Model serialization/deserialization

#### User Model Tests
- [ ] User creation with valid/invalid data
- [ ] Display name validation and length limits
- [ ] User ID generation and uniqueness

#### Prayer Model Tests
- [ ] Prayer creation with required fields
- [ ] Text length validation (500 char limit)
- [ ] Generated prayer field handling
- [ ] Project tag validation

#### Authentication Models Tests
- [ ] AuthenticationRequest lifecycle
- [ ] AuthApproval creation and validation
- [ ] Session model with multi-device fields
- [ ] Audit logging model integrity

### 2.2 Helper Function Testing

#### Session Management
- [ ] `create_session()` with various parameters
- [ ] `current_user()` authentication logic
- [ ] `require_full_auth()` permission checking
- [ ] Session security validation

#### Authentication Helpers
- [ ] `create_auth_request()` rate limiting
- [ ] `approve_auth_request()` approval logic
- [ ] `get_pending_requests_for_approval()` filtering
- [ ] Rate limiting logic (`check_rate_limit()`)

#### Business Logic
- [ ] `generate_prayer()` with mocked Anthropic API
- [ ] `get_feed_counts()` statistical calculations
- [ ] `todays_prompt()` YAML file reading
- [ ] `is_admin()` role checking

### 2.3 Route Handler Testing
- [ ] Request/response validation
- [ ] Authentication middleware behavior
- [ ] Error handling and HTTP status codes
- [ ] Form data processing

### 2.4 Security Testing
- [ ] SQL injection prevention
- [ ] XSS protection in templates
- [ ] CSRF protection for state-changing operations
- [ ] Session hijacking prevention
- [ ] Rate limiting effectiveness

## 3. Test Infrastructure

### 3.1 Test Configuration
```python
# pytest.ini or pyproject.toml configuration
- Test discovery patterns
- Coverage reporting settings
- Database isolation settings
- Environment variable management
```

### 3.2 Test Database Setup
- [ ] In-memory SQLite for unit tests
- [ ] Temporary database files for integration tests
- [ ] Database migration testing
- [ ] Test data factories using Factory Boy

### 3.3 Mocking Strategy
- [ ] Mock external APIs (Anthropic Claude)
- [ ] Mock datetime for time-sensitive tests
- [ ] Mock file system operations
- [ ] Mock email/notification services (future)

### 3.4 Continuous Integration
- [ ] GitHub Actions workflow for automated testing
- [ ] Test coverage reporting
- [ ] Performance regression testing
- [ ] Security vulnerability scanning

## 4. Test Implementation Strategy - 5 Stages

### Stage 1: Foundation & Setup
**Goal**: Establish testing infrastructure and basic model validation
- [ ] Set up pytest configuration and test database
- [ ] Create test utilities and factories
- [ ] Model unit tests (User, Prayer, Session, InviteToken)
- [ ] Basic database operations (create, read, update, delete)
- [ ] Test data cleanup and isolation

**Success Criteria**: All models can be created, validated, and persisted correctly

### Stage 2: Core Authentication & Security
**Goal**: Verify user authentication and session management works correctly
- [ ] Invite token creation and validation
- [ ] User registration via invite links
- [ ] Session creation and validation
- [ ] Basic authentication middleware (`current_user()`)
- [ ] Admin role checking (`is_admin()`)
- [ ] Rate limiting functionality

**Success Criteria**: Users can register, log in, and maintain sessions securely

### Stage 3: Prayer Management & Business Logic  
**Goal**: Test core prayer functionality and data operations
- [ ] Prayer submission with text validation
- [ ] LLM prayer generation (mocked Anthropic API)
- [ ] Prayer marking functionality
- [ ] Prayer flagging/unflagging
- [ ] Feed counting and statistics (`get_feed_counts()`)
- [ ] Basic feed filtering (all prayers)

**Success Criteria**: Users can submit, mark, and view prayers with correct statistics

### Stage 4: Advanced Features & Workflows
**Goal**: Test complex multi-device auth and administrative functions
- [ ] Multi-device authentication request workflows
- [ ] Authentication approval processes (admin, self, peer)
- [ ] Advanced feed filtering (new_unprayed, most_prayed, my_prayers, etc.)
- [ ] Admin panel functionality
- [ ] Audit logging and security monitoring
- [ ] Bulk operations for admins

**Success Criteria**: Complete authentication workflows and admin features work end-to-end

### Stage 5: Integration & User Experience
**Goal**: Full system integration testing and UI validation
- [ ] End-to-end API testing with FastAPI TestClient
- [ ] HTMX dynamic updates (prayer marking, flagging)
- [ ] Template rendering and form submissions
- [ ] Error handling and user feedback
- [ ] Performance testing and optimization
- [ ] Browser testing with Playwright (critical user journeys)

**Success Criteria**: Complete user workflows function correctly in realistic scenarios

## 5. Test Coverage Goals
- **Unit Tests**: 90% code coverage
- **Integration Tests**: All critical user journeys
- **Functional Tests**: All API endpoints
- **UI Tests**: Core user workflows

## 6. Testing Commands
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/functional/
pytest tests/integration/

# Run performance tests
pytest tests/performance/ --benchmark-only
```

## 7. Test Maintenance
- [ ] Regular test review and cleanup
- [ ] Update tests for new features
- [ ] Monitor test execution times
- [ ] Maintain test documentation