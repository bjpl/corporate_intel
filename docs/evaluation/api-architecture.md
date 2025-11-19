# API Architecture Evaluation Report

**Date:** 2025-11-19
**Evaluated By:** API Architecture Specialist
**Application:** Corporate Intelligence Platform
**Version:** 0.1.0

---

## Executive Summary

The Corporate Intelligence Platform implements a **FastAPI-based RESTful API** with strong architectural foundations. The API demonstrates excellent adherence to modern Python best practices, comprehensive security features, and well-structured endpoints. However, there are opportunities for improvement in API documentation, response consistency, and advanced features like HATEOAS.

**Overall Grade: B+ (87/100)**

### Key Strengths
- ✅ Clean separation of concerns with layered architecture
- ✅ Comprehensive authentication and authorization system
- ✅ Advanced rate limiting with token bucket algorithm
- ✅ Strong input validation using Pydantic models
- ✅ Proper error handling with custom exception hierarchy
- ✅ Effective caching strategy with Redis
- ✅ Good observability setup (OpenTelemetry, Sentry, Prometheus)

### Critical Improvements Needed
- ⚠️ Missing comprehensive OpenAPI documentation
- ⚠️ Inconsistent response envelope patterns
- ⚠️ No API versioning in URL paths
- ⚠️ Limited HATEOAS implementation
- ⚠️ Missing request/response examples in docstrings
- ⚠️ No standardized pagination metadata

---

## 1. API Endpoint Design & RESTful Principles

### Score: 85/100

#### ✅ Strengths

**1.1 Resource-Based URL Design**
```
/api/v1/companies              # Collection
/api/v1/companies/{id}         # Individual resource
/api/v1/companies/{id}/metrics # Sub-resource
/api/v1/filings                # Related collection
/api/v1/metrics                # Related collection
```
- File: `/home/user/corporate_intel/src/api/main.py:180-209`
- Properly uses nouns for resources (not verbs)
- Logical resource hierarchy and relationships

**1.2 HTTP Method Semantics**
```python
# GET - Read operations
@router.get("/", response_model=List[CompanyResponse])
@router.get("/{company_id}", response_model=CompanyResponse)

# POST - Create operations
@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)

# PUT - Update operations
@router.put("/{company_id}", response_model=CompanyResponse)

# DELETE - Delete operations
@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:72-278`
- Correctly uses HTTP methods for CRUD operations
- Proper status codes (200, 201, 204, 404, 409, 422, 500)

**1.3 Query Parameters for Filtering**
```python
@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    category: Optional[str] = Query(None, description="Filter by EdTech category"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
)
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:72-95`
- Uses query parameters for filtering and pagination
- Proper validation constraints (ge, le)

#### ⚠️ Issues Found

**1.4 Inconsistent Response Envelopes**
```python
# Some endpoints return bare arrays/objects
return companies  # Line 95

# Others return wrapped objects
return {
    "message": "User registered successfully",
    "user": {...}
}  # auth/routes.py:44-52
```
- **Issue**: Inconsistent response wrapping makes client implementation harder
- **Recommendation**: Standardize on envelope pattern:
  ```python
  {
    "data": [...],
    "meta": {"count": 10, "offset": 0, "limit": 100},
    "links": {"next": "...", "prev": "..."}
  }
  ```

**1.5 Missing HATEOAS Links**
- **Issue**: No hypermedia links in responses
- **Example**: Company response should include links to related resources:
  ```python
  {
    "id": "uuid",
    "ticker": "CHGG",
    "name": "Chegg Inc",
    "_links": {
      "self": "/api/v1/companies/uuid",
      "metrics": "/api/v1/companies/uuid/metrics",
      "filings": "/api/v1/filings?company_id=uuid"
    }
  }
  ```

**1.6 No Bulk Operations**
- **Issue**: No endpoints for bulk create/update/delete
- **Recommendation**: Add endpoints like:
  - `POST /api/v1/companies/bulk` for batch creation
  - `PATCH /api/v1/companies/bulk` for batch updates

---

## 2. Route Organization & Structure

### Score: 90/100

#### ✅ Strengths

**2.1 Excellent Modular Organization**
```
src/api/
├── main.py                    # Application factory
└── v1/
    ├── __init__.py
    ├── companies.py           # Company endpoints
    ├── filings.py             # SEC filings endpoints
    ├── intelligence.py        # Market intelligence endpoints
    ├── metrics.py             # Financial metrics endpoints
    ├── reports.py             # Analysis reports endpoints
    └── health.py              # Health check endpoints
```
- File: `/home/user/corporate_intel/src/api/v1/`
- Clean separation by domain/resource
- Each module handles a single resource type

**2.2 Centralized Router Registration**
```python
# src/api/main.py:176-209
app.include_router(auth_router)
app.include_router(companies.router, prefix=f"{settings.API_V1_PREFIX}/companies", tags=["companies"])
app.include_router(filings.router, prefix=f"{settings.API_V1_PREFIX}/filings", tags=["filings"])
app.include_router(metrics.router, prefix=f"{settings.API_V1_PREFIX}/metrics", tags=["metrics"])
app.include_router(intelligence.router, prefix=f"{settings.API_V1_PREFIX}/intelligence", tags=["intelligence"])
app.include_router(reports.router, prefix=f"{settings.API_V1_PREFIX}/reports", tags=["reports"])
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["health"])
```
- Clean and maintainable router registration
- Consistent tagging for OpenAPI documentation
- Prefix-based versioning setup

**2.3 Dependency Injection Pattern**
```python
async def list_companies(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
)
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:74-80`
- Excellent use of FastAPI dependency injection
- Separation of concerns (DB, auth, validation)

#### ⚠️ Issues Found

**2.4 Inconsistent Authentication Requirements**
```python
# Some endpoints require authentication
@router.get("/watchlist")
async def get_watchlist(
    current_user: User = Depends(get_current_user),  # Required
)

# Others don't
@router.get("/")
async def list_companies(
    # No authentication required
)
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:98-111, 72-95`
- **Issue**: Unclear which endpoints are public vs protected
- **Recommendation**: Document authentication requirements clearly or use consistent pattern

**2.5 Missing API Blueprint/Namespace Grouping**
- **Observation**: Auth routes use `/auth` prefix, others use `/api/v1`
- File: `/home/user/corporate_intel/src/auth/routes.py:23`
- **Recommendation**: Standardize all routes under `/api/v1` including auth:
  - `/api/v1/auth/login`
  - `/api/v1/auth/register`

---

## 3. Request/Response Patterns

### Score: 82/100

#### ✅ Strengths

**3.1 Comprehensive Pydantic Models**
```python
class CompanyBase(BaseModel):
    ticker: str = Field(..., max_length=10)
    name: str = Field(..., max_length=255)
    cik: Optional[str] = Field(None, max_length=10)
    sector: Optional[str] = Field(None, max_length=100)
    subsector: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, pattern="^(k12|higher_education|...)$")
    delivery_model: Optional[str] = Field(None, pattern="^(b2b|b2c|...)$")
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:21-30`
- Strong type safety with field validation
- Regex patterns for enum-like fields
- Clear field constraints (max_length, patterns)

**3.2 Separate Create/Response Models**
```python
class CompanyCreate(CompanyBase):
    """Company creation model."""
    subcategory: Optional[List[str]] = None
    monetization_strategy: Optional[List[str]] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2100)

class CompanyResponse(CompanyBase):
    """Company response model."""
    id: UUID
    # Inherits from CompanyBase
    model_config = ConfigDict(from_attributes=True)
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:33-55`
- Proper separation of input/output models
- Prevents exposing internal fields

**3.3 Type-Safe Query Parameters**
```python
@router.get("/trending/top-performers")
async def get_top_performers(
    metric: str = Query("growth", description="Ranking metric: growth, revenue, score"),
    category: Optional[str] = Query(None, description="Filter by EdTech category"),
    limit: int = Query(10, ge=1, le=50, description="Number of companies to return"),
)
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:295-304`
- Excellent query parameter validation
- Clear descriptions for API documentation

#### ⚠️ Issues Found

**3.4 Missing Request/Response Examples in Models**
```python
class CompanyResponse(CompanyBase):
    """Company response model."""
    id: UUID
    # No model_config with json_schema_extra examples
```
- **Issue**: Pydantic models lack example values for OpenAPI docs
- **Recommendation**: Add examples like in health.py:
  ```python
  model_config = ConfigDict(json_schema_extra={
      "example": {
          "id": "123e4567-e89b-12d3-a456-426614174000",
          "ticker": "CHGG",
          "name": "Chegg Inc",
          "sector": "Technology"
      }
  })
  ```

**3.5 Inconsistent Date/Time Handling**
```python
# Some use datetime
metric_date: datetime

# Others use Optional[datetime]
last_login_at: Optional[datetime] = None

# Some return isoformat strings
"last_updated": datetime.utcnow().isoformat()
```
- Files: Various across `/home/user/corporate_intel/src/api/v1/`
- **Issue**: Inconsistent datetime serialization
- **Recommendation**: Standardize on ISO 8601 format with timezone info

**3.6 No Pagination Metadata**
```python
@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return companies  # Just the array, no metadata
```
- **Issue**: Clients don't know total count, next/prev pages
- **Recommendation**: Return pagination envelope:
  ```python
  {
    "data": [...],
    "pagination": {
      "total": 150,
      "limit": 100,
      "offset": 0,
      "has_more": true
    }
  }
  ```

---

## 4. Error Handling & Validation

### Score: 92/100

#### ✅ Strengths

**4.1 Comprehensive Exception Hierarchy**
```python
CorporateIntelException (base)
├── DatabaseException
│   ├── ConnectionException
│   ├── QueryException
│   └── IntegrityException
├── DataSourceException
│   ├── APIException
│   │   ├── RateLimitException
│   │   ├── AuthenticationException
│   │   └── APIResponseException
│   └── DataValidationException
├── PipelineException
│   ├── IngestionException
│   ├── TransformationException
│   └── LoadException
└── ConfigurationException
```
- File: `/home/user/corporate_intel/src/core/exceptions.py:8-27`
- Excellent structured error hierarchy
- All errors include status codes, error codes, and context
- Proper HTTP status code mapping

**4.2 Centralized Exception Handlers**
```python
@app.exception_handler(CorporateIntelException)
async def corporate_intel_exception_handler(request: Request, exc: CorporateIntelException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_code": exc.error_code},
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )
```
- File: `/home/user/corporate_intel/src/api/main.py:134-146`
- Global exception handlers for consistent error responses
- Proper error serialization

**4.3 Input Validation with Pydantic**
```python
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain special character')
        return v
```
- File: `/home/user/corporate_intel/src/auth/models.py:247-267`
- Complex validation logic with clear error messages
- Proper use of field validators

**4.4 Structured Error Context**
```python
class CorporateIntelException(Exception):
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs: Any
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.kwargs = kwargs  # Additional context
        self.original_error = original_error
```
- File: `/home/user/corporate_intel/src/core/exceptions.py:56-68`
- Rich error context for debugging
- Preserves original exception for logging

#### ⚠️ Issues Found

**4.5 Inconsistent Error Response Format**
```python
# Some return error_code
{"detail": "...", "error_code": "..."}

# Others return nested structure
{"error": "...", "message": "...", "details": {...}}

# Some just return detail
{"detail": "..."}
```
- **Issue**: Clients need to handle multiple error formats
- **Recommendation**: Standardize on RFC 7807 Problem Details:
  ```python
  {
    "type": "/errors/validation-error",
    "title": "Validation Failed",
    "status": 422,
    "detail": "Password must contain uppercase letter",
    "instance": "/api/v1/auth/register",
    "errors": [
      {
        "field": "password",
        "message": "Password must contain uppercase letter"
      }
    ]
  }
  ```

**4.6 Missing Error Correlation IDs**
- **Issue**: No correlation IDs in error responses for log tracing
- **Recommendation**: Add correlation ID to all responses:
  ```python
  {
    "error_code": "DATABASE_ERROR",
    "detail": "Connection failed",
    "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
  ```

---

## 5. Authentication & Authorization

### Score: 95/100

#### ✅ Strengths

**5.1 Comprehensive Auth System**
```python
# JWT Token Authentication
@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, response: Response)

# API Key Authentication
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(key_data: APIKeyCreate)

# Dual auth support
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
)
```
- Files:
  - `/home/user/corporate_intel/src/auth/routes.py:66-106, 238-258`
  - `/home/user/corporate_intel/src/auth/dependencies.py:51-67`
- Supports both JWT and API key authentication
- Proper OAuth2 bearer scheme implementation

**5.2 Role-Based Access Control (RBAC)**
```python
class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    SERVICE = "service"

ROLE_PERMISSIONS = {
    UserRole.VIEWER: {
        PermissionScope.READ_COMPANIES,
        PermissionScope.READ_FILINGS,
        ...
    },
    UserRole.ANALYST: {
        # Viewer permissions +
        PermissionScope.WRITE_ANALYSIS,
        PermissionScope.RUN_ANALYSIS,
        ...
    },
    UserRole.ADMIN: {
        # All permissions
    }
}
```
- File: `/home/user/corporate_intel/src/auth/models.py:17-243`
- Well-defined role hierarchy
- Fine-grained permission scopes

**5.3 Flexible Permission Dependencies**
```python
class RequirePermission:
    def __init__(self, scope: PermissionScope):
        self.scope = scope

    async def __call__(self, user: User = Depends(get_current_active_user)):
        auth_service.require_permission(user, self.scope)
        return user

# Usage
RequireReadCompanies = RequirePermission(PermissionScope.READ_COMPANIES)
RequireManageUsers = RequirePermission(PermissionScope.MANAGE_USERS)
```
- File: `/home/user/corporate_intel/src/auth/dependencies.py:82-203`
- Reusable permission dependencies
- Easy to apply to specific endpoints

**5.4 Secure Password Storage**
```python
# Password complexity requirements
@field_validator('password')
def validate_password(cls, v: str) -> str:
    if not any(c.isupper() for c in v):
        raise ValueError('Password must contain uppercase letter')
    if not any(c.islower() for c in v):
        raise ValueError('Password must contain lowercase letter')
    if not any(c.isdigit() for c in v):
        raise ValueError('Password must contain digit')
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
        raise ValueError('Password must contain special character')
    return v
```
- File: `/home/user/corporate_intel/src/auth/models.py:255-267`
- Strong password requirements
- Hashed password storage (implied from model)

**5.5 API Key Scoping**
```python
class APIKey(Base):
    scopes = Column(String)  # Comma-separated PermissionScope values
    rate_limit_per_hour = Column(Integer, default=1000)
    expires_at = Column(DateTime)

    def has_scope(self, scope: PermissionScope) -> bool:
        if not self.scopes:
            return False
        key_scopes = set(self.scopes.split(','))
        return scope.value in key_scopes
```
- File: `/home/user/corporate_intel/src/auth/models.py:138-191`
- API keys have limited scopes
- Expiration and rate limiting per key

**5.6 Session Management**
```python
class UserSession(Base):
    token_jti = Column(String, unique=True, nullable=False)  # JWT ID
    ip_address = Column(String)
    user_agent = Column(String)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
```
- File: `/home/user/corporate_intel/src/auth/models.py:194-213`
- Tracks active sessions
- Supports token revocation

#### ⚠️ Issues Found

**5.7 Missing OAuth2 Provider Support**
- **Issue**: No support for OAuth2 providers (Google, GitHub, etc.)
- **Recommendation**: Add OAuth2 social login support

**5.8 No Multi-Factor Authentication (MFA)**
- **Issue**: No 2FA/MFA implementation
- **Recommendation**: Add TOTP-based MFA for enhanced security

---

## 6. API Documentation Completeness

### Score: 65/100

#### ✅ Strengths

**6.1 FastAPI Auto-Generated Docs**
```python
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)
```
- File: `/home/user/corporate_intel/src/api/main.py:115-120`
- Automatic Swagger UI at `/api/v1/docs`
- ReDoc at `/api/v1/redoc`
- OpenAPI schema at `/api/v1/openapi.json`

**6.2 Endpoint Descriptions**
```python
@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(db: Session = Depends(get_db)):
    """Comprehensive health check including all system components.

    Checks:
    - API server status
    - Database connectivity and performance
    - Data freshness and metrics
    - Cache availability (future)

    This endpoint is more expensive than /health and should be called
    less frequently (e.g., every 30s instead of every 5s).
    """
```
- File: `/home/user/corporate_intel/src/api/v1/health.py:93-107`
- Good docstring documentation
- Usage guidance provided

**6.3 Query Parameter Descriptions**
```python
metric: str = Query(
    "growth",
    description="Ranking metric: growth (YoY growth), revenue (total revenue), score (overall performance score)"
)
category: Optional[str] = Query(None, description="Filter by EdTech category")
limit: int = Query(10, ge=1, le=50, description="Number of companies to return")
```
- File: `/home/user/corporate_intel/src/api/v1/companies.py:298-303`
- Clear parameter descriptions
- Shows up in auto-generated docs

#### ⚠️ Critical Gaps

**6.4 Missing Comprehensive OpenAPI Specification**
- **Issue**: No dedicated `openapi.yaml` or `openapi.json` file
- **Finding**: Search for OpenAPI files returned no results
- **Impact**:
  - No code generation for clients
  - No contract testing
  - No API versioning control
- **Recommendation**: Create comprehensive OpenAPI 3.0 specification:

```yaml
openapi: 3.0.0
info:
  title: Corporate Intelligence Platform API
  version: 1.0.0
  description: |
    Corporate Intelligence Platform provides comprehensive EdTech market data,
    financial metrics, SEC filings analysis, and competitive intelligence.
  contact:
    name: API Support
    email: support@corp-intel.example.com
  license:
    name: Proprietary

servers:
  - url: https://api.corp-intel.example.com/api/v1
    description: Production server
  - url: https://staging-api.corp-intel.example.com/api/v1
    description: Staging server
  - url: http://localhost:8000/api/v1
    description: Development server

paths:
  /companies:
    get:
      summary: List companies
      description: Retrieve a paginated list of companies with optional filtering
      operationId: listCompanies
      tags:
        - companies
      parameters:
        - $ref: '#/components/parameters/CategoryFilter'
        - $ref: '#/components/parameters/SectorFilter'
        - $ref: '#/components/parameters/Limit'
        - $ref: '#/components/parameters/Offset'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Company'
              examples:
                default:
                  $ref: '#/components/examples/CompanyList'
        '422':
          $ref: '#/components/responses/ValidationError'

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    apiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key

  schemas:
    Company:
      type: object
      required:
        - ticker
        - name
      properties:
        id:
          type: string
          format: uuid
          example: 123e4567-e89b-12d3-a456-426614174000
        ticker:
          type: string
          maxLength: 10
          example: CHGG
        name:
          type: string
          maxLength: 255
          example: Chegg Inc
        # ... additional fields

security:
  - bearerAuth: []
  - apiKeyAuth: []
```

**6.5 Missing Request/Response Examples**
- **Issue**: Most endpoints lack example requests/responses
- **Impact**: Developers must guess payload structure
- **Recommendation**: Add examples to all Pydantic models

**6.6 No API Changelog**
- **Issue**: No documentation of API changes over time
- **Recommendation**: Create `CHANGELOG.md` for API:
  ```markdown
  # API Changelog

  ## [1.0.0] - 2025-11-19
  ### Added
  - Initial API release
  - Company management endpoints
  - Authentication with JWT and API keys
  - Rate limiting with token bucket algorithm
  ```

**6.7 Missing Postman/Insomnia Collections**
- **Issue**: No ready-to-use API collections for testing
- **Recommendation**: Export Postman collection from OpenAPI spec

**6.8 No API Versioning Documentation**
- **Issue**: No clear deprecation policy or version migration guide
- **Recommendation**: Document versioning strategy and lifecycle

---

## 7. Versioning Strategy

### Score: 70/100

#### ✅ Strengths

**7.1 URL Path Versioning Setup**
```python
API_V1_PREFIX: str = "/api/v1"

app.include_router(
    companies.router,
    prefix=f"{settings.API_V1_PREFIX}/companies",
    tags=["companies"],
)
```
- Files:
  - `/home/user/corporate_intel/src/core/config.py:25`
  - `/home/user/corporate_intel/src/api/main.py:180-184`
- Version prefix configured centrally
- Easy to add v2 in future

**7.2 Versioned Module Structure**
```
src/api/
├── main.py
└── v1/
    ├── __init__.py
    ├── companies.py
    ├── filings.py
    └── ...
```
- Clean separation by version
- Allows parallel v1/v2 support

#### ⚠️ Issues Found

**7.3 No Actual Version in URLs**
```
Current:  /api/v1/companies
Expected: /v1/companies  (or /api/v1/companies if "api" is mandatory)
```
- **Issue**: Config says `/api/v1` but could be clearer
- **Observation**: This is actually correct, just needs documentation

**7.4 No Version Negotiation**
- **Issue**: No header-based version negotiation
- **Example**: Some APIs support:
  ```
  Accept: application/vnd.corpintel.v1+json
  ```
- **Recommendation**: Document that URL-based versioning is the chosen strategy

**7.5 No Deprecation Headers**
- **Issue**: No way to signal deprecated endpoints
- **Recommendation**: Add deprecation warnings:
  ```python
  response.headers["Deprecation"] = "true"
  response.headers["Sunset"] = "Sat, 31 Dec 2025 23:59:59 GMT"
  response.headers["Link"] = '</api/v2/companies>; rel="successor-version"'
  ```

**7.6 Missing Version Lifecycle Policy**
- **Issue**: No documented policy for:
  - How long old versions are supported
  - When breaking changes are allowed
  - Migration guide for version upgrades

---

## 8. Rate Limiting & Security

### Score: 93/100

#### ✅ Strengths

**8.1 Advanced Token Bucket Rate Limiting**
```python
class RateLimiter:
    """Token bucket rate limiter with Redis backend."""

    def __init__(
        self,
        redis_client: Redis,
        requests_per_minute: int = 60,
        burst_size: int = 100,
    ):
        self.rate = requests_per_minute / 60.0  # Requests per second
        self.burst_size = burst_size
        self.refill_rate = self.rate
```
- File: `/home/user/corporate_intel/src/middleware/rate_limiting.py:22-42`
- Sophisticated token bucket algorithm
- Redis-backed for distributed systems
- Atomic operations with Lua scripts

**8.2 Lua Script for Atomic Rate Limiting**
```python
lua_script = """
local bucket_key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local tokens_requested = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

-- Get current bucket state
local bucket = redis.call('HMGET', bucket_key, 'tokens', 'last_refill')
local tokens = tonumber(bucket[1])
local last_refill = tonumber(bucket[2])

-- Initialize bucket if doesn't exist
if tokens == nil then
    tokens = capacity
    last_refill = now
end

-- Calculate tokens to add based on time elapsed
local time_elapsed = now - last_refill
local tokens_to_add = time_elapsed * refill_rate
tokens = math.min(capacity, tokens + tokens_to_add)

-- Check if we can consume requested tokens
local allowed = 0
if tokens >= tokens_requested then
    tokens = tokens - tokens_requested
    allowed = 1
end

-- Update bucket state
redis.call('HMSET', bucket_key, 'tokens', tokens, 'last_refill', now)
redis.call('EXPIRE', bucket_key, 3600)

return {allowed, math.floor(tokens), capacity}
"""
```
- File: `/home/user/corporate_intel/src/middleware/rate_limiting.py:63-98`
- Ensures atomic token consumption
- No race conditions in distributed environment
- Auto-cleanup with TTL

**8.3 Tiered Rate Limiting**
```python
RATE_LIMIT_TIERS = {
    "free": {
        "requests_per_minute": 60,
        "burst_size": 100,
    },
    "basic": {
        "requests_per_minute": 300,
        "burst_size": 500,
    },
    "premium": {
        "requests_per_minute": 1000,
        "burst_size": 2000,
    },
    "enterprise": {
        "requests_per_minute": 5000,
        "burst_size": 10000,
    },
}
```
- File: `/home/user/corporate_intel/src/middleware/rate_limiting.py:275-292`
- Multiple tiers for different user levels
- Easily extensible

**8.4 Rate Limit Headers**
```python
response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
```
- File: `/home/user/corporate_intel/src/middleware/rate_limiting.py:219-221`
- Standard rate limit headers
- Clients can implement backoff strategies

**8.5 Flexible Rate Limit Keys**
```python
def _get_rate_limit_key(self, request: Request) -> str:
    """Priority order:
    1. API Key (from X-API-Key header)
    2. User ID (from authentication)
    3. Client IP address
    """
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"

    if hasattr(request.state, "user") and request.state.user:
        user_id = getattr(request.state.user, "id", None)
        if user_id:
            return f"user:{user_id}"

    client_ip = self._get_client_ip(request)
    return f"ip:{client_ip}"
```
- File: `/home/user/corporate_intel/src/middleware/rate_limiting.py:225-247`
- Intelligent key selection
- Falls back to IP if no auth

**8.6 Security Best Practices**

✅ **CORS Configuration**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
- File: `/home/user/corporate_intel/src/api/main.py:124-131`

✅ **Secure Cookie Settings**
```python
response.set_cookie(
    key="refresh_token",
    value=tokens.refresh_token,
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=7 * 24 * 60 * 60
)
```
- File: `/home/user/corporate_intel/src/auth/routes.py:83-90`

✅ **Password Hashing** (implied from models)

✅ **SQL Injection Prevention** (SQLAlchemy ORM)

✅ **Input Validation** (Pydantic)

#### ⚠️ Minor Issues

**8.7 CORS Allow All Methods/Headers**
```python
allow_methods=["*"],
allow_headers=["*"],
```
- **Issue**: Overly permissive for production
- **Recommendation**: Restrict to specific methods and headers:
  ```python
  allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
  allow_headers=["Authorization", "Content-Type", "X-API-Key"],
  ```

**8.8 Missing Security Headers**
- **Issue**: No security headers middleware
- **Recommendation**: Add headers:
  - `Strict-Transport-Security`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy`

**8.9 No Request Size Limits**
- **Issue**: No explicit request body size limits
- **Recommendation**: Add middleware to limit request sizes

---

## Detailed Findings by File

### `/home/user/corporate_intel/src/api/main.py`
**Lines 111-220 | Application Factory**
- ✅ Clean lifespan management with startup/shutdown hooks
- ✅ Comprehensive observability setup (Sentry, OpenTelemetry, Prometheus)
- ✅ Centralized exception handlers
- ⚠️ CORS configuration is overly permissive (line 129-130)
- ⚠️ Missing security headers middleware

### `/home/user/corporate_intel/src/api/v1/companies.py`
**Lines 72-95 | List Companies Endpoint**
- ✅ Proper query parameter validation
- ✅ Caching with TTL
- ⚠️ Missing pagination metadata in response
- ⚠️ No authentication required (may be intentional)

**Lines 115-130 | Get Company Endpoint**
- ✅ Proper 404 handling
- ✅ UUID path parameter
- ⚠️ Missing HATEOAS links

**Lines 188-218 | Create Company Endpoint**
- ✅ Requires authentication
- ✅ Duplicate checking
- ✅ Cache invalidation
- ✅ Proper 201 status code
- ⚠️ No bulk create endpoint

**Lines 295-372 | Top Performers Endpoint**
- ✅ Complex query with data warehouse integration
- ✅ Good error handling
- ✅ Flexible metric selection
- ⚠️ Raw SQL query (no ORM) - acceptable for analytics

### `/home/user/corporate_intel/src/api/v1/health.py`
**Lines 65-80 | Basic Health Check**
- ✅ Lightweight endpoint
- ✅ No dependencies
- ✅ Good for load balancer checks

**Lines 93-139 | Detailed Health Check**
- ✅ Comprehensive component checks
- ✅ Performance metrics
- ✅ Clear documentation about usage
- ⚠️ Could add more components (cache, message queue)

**Lines 142-166 | Readiness Check**
- ✅ Kubernetes-friendly
- ⚠️ Returns tuple instead of proper HTTPException for 503

### `/home/user/corporate_intel/src/auth/routes.py`
**Lines 26-63 | Registration Endpoint**
- ✅ Rate limiting
- ✅ Password complexity validation
- ✅ Clear error messages
- ⚠️ No email verification workflow

**Lines 66-105 | Login Endpoint**
- ✅ Secure cookie for refresh token
- ✅ Rate limiting
- ✅ Proper authentication errors
- ⚠️ No MFA support

**Lines 238-258 | Create API Key**
- ✅ Scoped API keys
- ✅ Expiration support
- ✅ Rate limiting per key
- ✅ Shows key only once

### `/home/user/corporate_intel/src/middleware/rate_limiting.py`
**Lines 22-150 | Token Bucket Implementation**
- ✅ Excellent algorithm implementation
- ✅ Redis-backed for distributed systems
- ✅ Atomic Lua script
- ✅ Graceful error handling (allows request on Redis failure)

**Lines 152-264 | Rate Limit Middleware**
- ✅ Skips health checks
- ✅ Proper rate limit headers
- ✅ 429 status code with Retry-After
- ✅ Intelligent key selection

### `/home/user/corporate_intel/src/core/exceptions.py`
**Lines 8-441 | Exception Hierarchy**
- ✅ Comprehensive exception types
- ✅ Proper HTTP status code mapping
- ✅ Rich error context
- ✅ Helper functions for error wrapping
- ⚠️ Could add more specific business exceptions

---

## Recommendations Summary

### Priority 1: Critical (Implement Immediately)

1. **Create Comprehensive OpenAPI Specification**
   - Create `/docs/openapi.yaml` with complete API documentation
   - Include all endpoints, schemas, examples, and security definitions
   - Generate client SDKs from spec

2. **Standardize Error Response Format**
   - Adopt RFC 7807 Problem Details for HTTP APIs
   - Add correlation IDs for log tracing
   - Ensure consistent error structure across all endpoints

3. **Add Pagination Metadata**
   - Include `total`, `limit`, `offset`, `has_more` in list responses
   - Add `next` and `prev` links for easy navigation
   - Implement cursor-based pagination for large datasets

4. **Add Security Headers Middleware**
   - Implement `Strict-Transport-Security`
   - Add `X-Content-Type-Options`, `X-Frame-Options`
   - Configure `Content-Security-Policy`

### Priority 2: Important (Next Sprint)

5. **Improve API Documentation**
   - Add request/response examples to all Pydantic models
   - Create API changelog
   - Generate Postman/Insomnia collections
   - Document authentication flows

6. **Implement Response Envelopes**
   - Standardize on consistent response structure
   - Include metadata in all responses
   - Add HATEOAS links for resource navigation

7. **Add Bulk Operations**
   - `POST /api/v1/companies/bulk` for batch creation
   - `PATCH /api/v1/companies/bulk` for batch updates
   - `DELETE /api/v1/companies/bulk` for batch deletion

8. **Enhance Rate Limiting**
   - Restrict CORS to specific methods/headers
   - Add request size limits
   - Implement adaptive rate limiting based on load

### Priority 3: Nice to Have (Future)

9. **Add Advanced Features**
   - OAuth2 social login support
   - Multi-factor authentication (MFA)
   - Webhook subscriptions
   - GraphQL endpoint for flexible queries

10. **API Versioning Enhancements**
    - Document version lifecycle policy
    - Add deprecation headers to old endpoints
    - Create migration guides for version upgrades
    - Implement header-based version negotiation

11. **Observability Improvements**
    - Add distributed tracing correlation
    - Enhance API analytics and usage metrics
    - Implement SLA monitoring
    - Add API performance dashboards

---

## OpenAPI Specification Template

### File: `/docs/api/openapi.yaml`

```yaml
openapi: 3.0.3
info:
  title: Corporate Intelligence Platform API
  version: 1.0.0
  description: |
    # Corporate Intelligence Platform API

    Comprehensive EdTech market intelligence, financial metrics,
    SEC filings analysis, and competitive insights.

    ## Features
    - Real-time financial metrics tracking
    - SEC filings analysis
    - Competitive intelligence reports
    - Market trend analysis

    ## Authentication
    The API supports two authentication methods:
    1. **JWT Bearer Tokens** - For user-based access
    2. **API Keys** - For programmatic access

    ## Rate Limiting
    - **Free Tier**: 60 requests/minute, 100 burst
    - **Basic Tier**: 300 requests/minute, 500 burst
    - **Premium Tier**: 1000 requests/minute, 2000 burst
    - **Enterprise Tier**: 5000 requests/minute, 10000 burst

    Rate limit information is provided in response headers:
    - `X-RateLimit-Limit` - Maximum requests allowed
    - `X-RateLimit-Remaining` - Remaining requests
    - `X-RateLimit-Reset` - Unix timestamp when limit resets

  contact:
    name: API Support Team
    email: api-support@corp-intel.example.com
    url: https://corp-intel.example.com/support
  license:
    name: Proprietary
    url: https://corp-intel.example.com/terms
  termsOfService: https://corp-intel.example.com/terms

servers:
  - url: https://api.corp-intel.example.com/api/v1
    description: Production server
  - url: https://staging-api.corp-intel.example.com/api/v1
    description: Staging server
  - url: http://localhost:8000/api/v1
    description: Development server

tags:
  - name: companies
    description: Company management and information
  - name: filings
    description: SEC filings and regulatory documents
  - name: metrics
    description: Financial and operational metrics
  - name: intelligence
    description: Market intelligence and insights
  - name: reports
    description: Analysis reports and exports
  - name: health
    description: System health and status checks
  - name: auth
    description: Authentication and authorization

paths:
  /companies:
    get:
      summary: List companies
      description: |
        Retrieve a paginated list of companies with optional filtering.

        Supports filtering by category, sector, and pagination parameters.
      operationId: listCompanies
      tags:
        - companies
      parameters:
        - name: category
          in: query
          description: Filter by EdTech category
          required: false
          schema:
            type: string
            enum:
              - k12
              - higher_education
              - corporate_learning
              - direct_to_consumer
              - enabling_technology
          example: higher_education
        - name: sector
          in: query
          description: Filter by business sector
          required: false
          schema:
            type: string
          example: Technology
        - name: limit
          in: query
          description: Maximum number of results to return
          required: false
          schema:
            type: integer
            minimum: 1
            maximum: 500
            default: 100
        - name: offset
          in: query
          description: Number of results to skip
          required: false
          schema:
            type: integer
            minimum: 0
            default: 0
      responses:
        '200':
          description: Successful response
          headers:
            X-RateLimit-Limit:
              $ref: '#/components/headers/X-RateLimit-Limit'
            X-RateLimit-Remaining:
              $ref: '#/components/headers/X-RateLimit-Remaining'
            X-RateLimit-Reset:
              $ref: '#/components/headers/X-RateLimit-Reset'
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Company'
                  pagination:
                    $ref: '#/components/schemas/PaginationMetadata'
              examples:
                success:
                  $ref: '#/components/examples/CompanyListSuccess'
        '422':
          $ref: '#/components/responses/ValidationError'
        '429':
          $ref: '#/components/responses/RateLimitExceeded'
        '500':
          $ref: '#/components/responses/InternalServerError'
      security:
        - {}  # Public endpoint

    post:
      summary: Create a new company
      description: Create a new company record in the system
      operationId: createCompany
      tags:
        - companies
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CompanyCreate'
            examples:
              edtech_company:
                $ref: '#/components/examples/CompanyCreateRequest'
      responses:
        '201':
          description: Company created successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Company'
              examples:
                success:
                  $ref: '#/components/examples/CompanyCreateSuccess'
        '400':
          $ref: '#/components/responses/BadRequest'
        '401':
          $ref: '#/components/responses/Unauthorized'
        '409':
          $ref: '#/components/responses/Conflict'
        '422':
          $ref: '#/components/responses/ValidationError'
      security:
        - bearerAuth: []
        - apiKeyAuth: []

  /companies/{companyId}:
    get:
      summary: Get company by ID
      description: Retrieve detailed information about a specific company
      operationId: getCompany
      tags:
        - companies
      parameters:
        - name: companyId
          in: path
          required: true
          description: Unique identifier of the company
          schema:
            type: string
            format: uuid
          example: 123e4567-e89b-12d3-a456-426614174000
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Company'
              examples:
                success:
                  $ref: '#/components/examples/CompanyDetailSuccess'
        '404':
          $ref: '#/components/responses/NotFound'
      security:
        - {}

    put:
      summary: Update company
      description: Update an existing company's information
      operationId: updateCompany
      tags:
        - companies
      parameters:
        - name: companyId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CompanyUpdate'
      responses:
        '200':
          description: Company updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Company'
        '404':
          $ref: '#/components/responses/NotFound'
        '422':
          $ref: '#/components/responses/ValidationError'
      security:
        - bearerAuth: []
        - apiKeyAuth: []

    delete:
      summary: Delete company
      description: Delete a company from the system
      operationId: deleteCompany
      tags:
        - companies
      parameters:
        - name: companyId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Company deleted successfully
        '404':
          $ref: '#/components/responses/NotFound'
      security:
        - bearerAuth: []

  /companies/{companyId}/metrics:
    get:
      summary: Get company metrics
      description: Retrieve latest financial and operational metrics for a company
      operationId: getCompanyMetrics
      tags:
        - companies
        - metrics
      parameters:
        - name: companyId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CompanyMetrics'
        '404':
          $ref: '#/components/responses/NotFound'

  /health:
    get:
      summary: Basic health check
      description: Lightweight health check for load balancers
      operationId: healthCheck
      tags:
        - health
      responses:
        '200':
          description: Service is healthy
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'
      security:
        - {}

  /health/detailed:
    get:
      summary: Detailed health check
      description: Comprehensive health check including all system components
      operationId: detailedHealthCheck
      tags:
        - health
      responses:
        '200':
          description: Detailed health status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DetailedHealthResponse'

  /auth/register:
    post:
      summary: Register new user
      description: Create a new user account
      operationId: registerUser
      tags:
        - auth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
            examples:
              new_user:
                summary: New user registration
                value:
                  email: user@example.com
                  username: johndoe
                  password: SecureP@ssw0rd!
                  full_name: John Doe
                  organization: Example Corp
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                  user:
                    type: object
                    properties:
                      id:
                        type: string
                        format: uuid
                      email:
                        type: string
                      username:
                        type: string
                      role:
                        type: string
        '400':
          $ref: '#/components/responses/BadRequest'
        '422':
          $ref: '#/components/responses/ValidationError'
      security:
        - {}

  /auth/login:
    post:
      summary: Login
      description: Authenticate user and receive JWT tokens
      operationId: loginUser
      tags:
        - auth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserLogin'
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TokenResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
      security:
        - {}

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT bearer token authentication.

        To obtain a token, use the `/auth/login` endpoint with your credentials.

        Include the token in the Authorization header:
        ```
        Authorization: Bearer <your-jwt-token>
        ```

    apiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: |
        API key authentication for programmatic access.

        Create an API key through the `/auth/api-keys` endpoint after logging in.

        Include the key in the X-API-Key header:
        ```
        X-API-Key: ci_<your-api-key>
        ```

  headers:
    X-RateLimit-Limit:
      description: Maximum number of requests allowed per time window
      schema:
        type: integer
      example: 1000

    X-RateLimit-Remaining:
      description: Number of requests remaining in current time window
      schema:
        type: integer
      example: 950

    X-RateLimit-Reset:
      description: Unix timestamp when the rate limit resets
      schema:
        type: integer
      example: 1700000000

  schemas:
    Company:
      type: object
      required:
        - id
        - ticker
        - name
      properties:
        id:
          type: string
          format: uuid
          description: Unique identifier
          example: 123e4567-e89b-12d3-a456-426614174000
        ticker:
          type: string
          maxLength: 10
          description: Stock ticker symbol
          example: CHGG
        name:
          type: string
          maxLength: 255
          description: Company name
          example: Chegg Inc
        cik:
          type: string
          maxLength: 10
          nullable: true
          description: SEC Central Index Key
          example: "0001364954"
        sector:
          type: string
          maxLength: 100
          nullable: true
          description: Business sector
          example: Technology
        subsector:
          type: string
          maxLength: 100
          nullable: true
          description: Business subsector
          example: Education Technology
        category:
          type: string
          enum:
            - k12
            - higher_education
            - corporate_learning
            - direct_to_consumer
            - enabling_technology
          nullable: true
          description: EdTech category
          example: higher_education
        delivery_model:
          type: string
          enum:
            - b2b
            - b2c
            - b2b2c
            - marketplace
            - hybrid
          nullable: true
          description: Business delivery model
          example: b2c
        subcategory:
          type: array
          items:
            type: string
          nullable: true
          description: EdTech subcategories
          example: ["online_tutoring", "test_prep"]
        monetization_strategy:
          type: array
          items:
            type: string
          nullable: true
          description: Revenue models
          example: ["subscription", "transactional"]
        founded_year:
          type: integer
          minimum: 1800
          maximum: 2100
          nullable: true
          description: Year company was founded
          example: 2005
        headquarters:
          type: string
          maxLength: 255
          nullable: true
          description: Headquarters location
          example: Santa Clara, CA
        website:
          type: string
          maxLength: 255
          nullable: true
          description: Company website URL
          example: https://www.chegg.com
        employee_count:
          type: integer
          minimum: 0
          nullable: true
          description: Number of employees
          example: 3500

    CompanyCreate:
      type: object
      required:
        - ticker
        - name
      properties:
        ticker:
          type: string
          maxLength: 10
          example: CHGG
        name:
          type: string
          maxLength: 255
          example: Chegg Inc
        cik:
          type: string
          maxLength: 10
          nullable: true
          example: "0001364954"
        sector:
          type: string
          maxLength: 100
          nullable: true
          example: Technology
        subsector:
          type: string
          maxLength: 100
          nullable: true
        category:
          type: string
          enum:
            - k12
            - higher_education
            - corporate_learning
            - direct_to_consumer
            - enabling_technology
          nullable: true
        delivery_model:
          type: string
          enum:
            - b2b
            - b2c
            - b2b2c
            - marketplace
            - hybrid
          nullable: true
        subcategory:
          type: array
          items:
            type: string
          nullable: true
        monetization_strategy:
          type: array
          items:
            type: string
          nullable: true
        founded_year:
          type: integer
          nullable: true
        headquarters:
          type: string
          nullable: true
        website:
          type: string
          nullable: true
        employee_count:
          type: integer
          nullable: true

    CompanyUpdate:
      type: object
      properties:
        ticker:
          type: string
          maxLength: 10
        name:
          type: string
          maxLength: 255
        cik:
          type: string
          maxLength: 10
          nullable: true
        sector:
          type: string
          nullable: true
        # ... other updatable fields

    CompanyMetrics:
      type: object
      required:
        - company_id
        - ticker
        - last_updated
      properties:
        company_id:
          type: string
          format: uuid
        ticker:
          type: string
        latest_revenue:
          type: number
          format: float
          nullable: true
          description: Latest revenue in USD
          example: 776500000
        revenue_growth_yoy:
          type: number
          format: float
          nullable: true
          description: Year-over-year revenue growth percentage
          example: 12.5
        monthly_active_users:
          type: integer
          nullable: true
          description: Monthly active users
          example: 4200000
        arpu:
          type: number
          format: float
          nullable: true
          description: Average revenue per user
          example: 185.0
        cac:
          type: number
          format: float
          nullable: true
          description: Customer acquisition cost
          example: 75.0
        nrr:
          type: number
          format: float
          nullable: true
          description: Net revenue retention percentage
          example: 105.0
        last_updated:
          type: string
          format: date-time
          description: Timestamp of last metrics update

    PaginationMetadata:
      type: object
      required:
        - total
        - limit
        - offset
        - has_more
      properties:
        total:
          type: integer
          description: Total number of items available
          example: 150
        limit:
          type: integer
          description: Maximum items per page
          example: 100
        offset:
          type: integer
          description: Number of items skipped
          example: 0
        has_more:
          type: boolean
          description: Whether more items are available
          example: true

    HealthResponse:
      type: object
      required:
        - status
        - timestamp
        - version
        - environment
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
          example: healthy
        timestamp:
          type: string
          format: date-time
        version:
          type: string
          example: 0.1.0
        environment:
          type: string
          enum: [development, staging, production]
          example: production

    DetailedHealthResponse:
      type: object
      required:
        - status
        - timestamp
        - version
        - environment
        - components
        - metrics
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          type: string
          format: date-time
        version:
          type: string
        environment:
          type: string
        components:
          type: object
          properties:
            database:
              type: object
              properties:
                status:
                  type: string
                response_time_ms:
                  type: number
            cache:
              type: object
              properties:
                status:
                  type: string
                response_time_ms:
                  type: number
        metrics:
          type: object
          properties:
            companies_tracked:
              type: integer
            total_metrics:
              type: integer
            last_ingestion:
              type: string
              format: date-time

    UserCreate:
      type: object
      required:
        - email
        - username
        - password
      properties:
        email:
          type: string
          format: email
          example: user@example.com
        username:
          type: string
          minLength: 3
          maxLength: 50
          example: johndoe
        password:
          type: string
          minLength: 8
          format: password
          description: Must contain uppercase, lowercase, digit, and special character
          example: SecureP@ssw0rd!
        full_name:
          type: string
          nullable: true
          example: John Doe
        organization:
          type: string
          nullable: true
          example: Example Corp

    UserLogin:
      type: object
      required:
        - username
        - password
      properties:
        username:
          type: string
          description: Username or email
          example: johndoe
        password:
          type: string
          format: password
          example: SecureP@ssw0rd!

    TokenResponse:
      type: object
      required:
        - access_token
        - refresh_token
        - token_type
        - expires_in
      properties:
        access_token:
          type: string
          description: JWT access token
          example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        refresh_token:
          type: string
          description: JWT refresh token
          example: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        token_type:
          type: string
          enum: [bearer]
          example: bearer
        expires_in:
          type: integer
          description: Access token expiration in seconds
          example: 3600

    Error:
      type: object
      required:
        - type
        - title
        - status
        - detail
      properties:
        type:
          type: string
          description: Error type URI
          example: /errors/validation-error
        title:
          type: string
          description: Short error summary
          example: Validation Failed
        status:
          type: integer
          description: HTTP status code
          example: 422
        detail:
          type: string
          description: Detailed error message
          example: Password must contain uppercase letter
        instance:
          type: string
          description: API endpoint that generated the error
          example: /api/v1/auth/register
        correlation_id:
          type: string
          format: uuid
          description: Unique ID for error tracking
          example: a1b2c3d4-e5f6-7890-abcd-ef1234567890
        errors:
          type: array
          description: Field-specific validation errors
          items:
            type: object
            properties:
              field:
                type: string
                example: password
              message:
                type: string
                example: Password must contain uppercase letter

  responses:
    BadRequest:
      description: Bad request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/bad-request
            title: Bad Request
            status: 400
            detail: Invalid request parameters

    Unauthorized:
      description: Unauthorized
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/unauthorized
            title: Unauthorized
            status: 401
            detail: Authentication required

    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/not-found
            title: Not Found
            status: 404
            detail: Company with ID 123e4567-e89b-12d3-a456-426614174000 not found

    Conflict:
      description: Resource conflict
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/conflict
            title: Conflict
            status: 409
            detail: Company with ticker CHGG already exists

    ValidationError:
      description: Validation error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/validation-error
            title: Validation Failed
            status: 422
            detail: Invalid input parameters
            errors:
              - field: limit
                message: Value must be less than or equal to 500

    RateLimitExceeded:
      description: Rate limit exceeded
      headers:
        X-RateLimit-Limit:
          $ref: '#/components/headers/X-RateLimit-Limit'
        X-RateLimit-Remaining:
          $ref: '#/components/headers/X-RateLimit-Remaining'
        X-RateLimit-Reset:
          $ref: '#/components/headers/X-RateLimit-Reset'
        Retry-After:
          description: Seconds until rate limit resets
          schema:
            type: integer
          example: 3600
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/rate-limit-exceeded
            title: Rate Limit Exceeded
            status: 429
            detail: Too many requests. Please try again later.

    InternalServerError:
      description: Internal server error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            type: /errors/internal-server-error
            title: Internal Server Error
            status: 500
            detail: An unexpected error occurred
            correlation_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890

  examples:
    CompanyListSuccess:
      summary: Successful company list response
      value:
        data:
          - id: 123e4567-e89b-12d3-a456-426614174000
            ticker: CHGG
            name: Chegg Inc
            sector: Technology
            category: higher_education
            delivery_model: b2c
          - id: 234e5678-e89b-12d3-a456-426614174001
            ticker: DUOL
            name: Duolingo Inc
            sector: Technology
            category: direct_to_consumer
            delivery_model: b2c
        pagination:
          total: 27
          limit: 100
          offset: 0
          has_more: false

    CompanyDetailSuccess:
      summary: Company detail response
      value:
        id: 123e4567-e89b-12d3-a456-426614174000
        ticker: CHGG
        name: Chegg Inc
        cik: "0001364954"
        sector: Technology
        subsector: Education Technology
        category: higher_education
        delivery_model: b2c
        subcategory: ["online_tutoring", "test_prep"]
        monetization_strategy: ["subscription", "transactional"]
        founded_year: 2005
        headquarters: Santa Clara, CA
        website: https://www.chegg.com
        employee_count: 3500

    CompanyCreateRequest:
      summary: Create company request
      value:
        ticker: CHGG
        name: Chegg Inc
        cik: "0001364954"
        sector: Technology
        subsector: Education Technology
        category: higher_education
        delivery_model: b2c
        subcategory: ["online_tutoring", "test_prep"]
        monetization_strategy: ["subscription", "transactional"]
        founded_year: 2005
        headquarters: Santa Clara, CA
        website: https://www.chegg.com
        employee_count: 3500

    CompanyCreateSuccess:
      summary: Company created successfully
      value:
        id: 123e4567-e89b-12d3-a456-426614174000
        ticker: CHGG
        name: Chegg Inc
        cik: "0001364954"
        sector: Technology
        subsector: Education Technology
        category: higher_education
        delivery_model: b2c

security:
  - bearerAuth: []
  - apiKeyAuth: []
```

---

## Conclusion

The Corporate Intelligence Platform API demonstrates **strong architectural foundations** with modern best practices, comprehensive security, and excellent error handling. The use of FastAPI, Pydantic validation, and sophisticated rate limiting shows a mature understanding of API development.

**Key achievements:**
- Clean, modular code organization
- Robust authentication and authorization
- Advanced rate limiting with token bucket algorithm
- Comprehensive exception handling
- Good observability integration

**Primary improvement areas:**
- API documentation needs enhancement
- Response format consistency
- HATEOAS implementation
- Pagination metadata
- Security headers

By implementing the Priority 1 and Priority 2 recommendations, the API will achieve production-ready status with best-in-class developer experience.

**Final Grade: B+ (87/100)**

---

*Report generated: 2025-11-19*
*Next review recommended: Q1 2026*
