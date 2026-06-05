# Adapters

Adapters provide technology-specific integration for `sdlc`. Each adapter defines detection patterns, framework components, applicable rule sets, and required knowledge base entries.

## How Detection Works

`AdapterDetector` scans a project root directory against each adapter's `detect_patterns`. A pattern consists of:

- **glob**: file path pattern (e.g., `**/pom.xml`)
- **contains**: substring to search for within matched files

An adapter matches if **any** of its patterns succeeds. The `no-tech` adapter has no patterns and serves as a fallback.

```python
from sdlc.adapter import AdapterDetector, AdapterRegistry
from sdlc.cli.deps import _register_all_adapters

registry = AdapterRegistry()
_register_all_adapters(registry)

detector = AdapterDetector(registry)
matches = detector.detect(Path("/path/to/project"))
for adapter in matches:
    print(adapter.id, adapter.name)
```

## All 18 Adapters

### Backend — Java

#### dongboot

JD microservice framework (DongBoot).

| Property | Value |
|----------|-------|
| ID | `dongboot` |
| Detection | `**/pom.xml` contains `dong-boot-starter`; `**/application.yml` contains `dongboot` |
| Rule Sets | `dongboot-must`, `jd-coding-must` |
| Required KB | `rules/MUST.yaml`, `standards/coding-style.md`, `architecture/component-catalog.md` |

Components:

| ID | Type | Detect |
|----|------|--------|
| dong-log | logging | `BizLogger` |
| dong-thread | threadpool | `DongThread` |
| dong-dal | db | `DongDAL` |
| dong-cache | cache | `DongCache` |
| dong-mq | mq | `DongMQ` |
| dong-web | web | `DongWeb` |
| dong-config | config | `DongConfig` |
| dong-hot-deploy | deploy | `hot_deploy` |

#### jd-spring-boot

JD Spring Boot framework.

| Property | Value |
|----------|-------|
| ID | `jd-spring-boot` |
| Detection | `**/pom.xml` contains `spring-boot-starter` |
| Rule Sets | `jd-coding-must`, `spring-boot-must` |
| Required KB | `rules/MUST.yaml`, `standards/spring-boot-guide.md` |

Components:

| ID | Type | Detect |
|----|------|--------|
| spring-mvc | web | `@Controller` |
| spring-data | db | `@Repository` |
| spring-security | security | `@EnableWebSecurity` |
| spring-actuator | monitor | `@Endpoint` |

### Backend — Python

#### python-flask

| Property | Value |
|----------|-------|
| ID | `python-flask` |
| Detection | `**/requirements.txt` contains `flask` |
| Rule Sets | `python-must` |
| Required KB | `rules/python-must.yaml` |

Components: flask-restful (web), flask-sqlalchemy (db), flask-caching (cache)

#### python-django

| Property | Value |
|----------|-------|
| ID | `python-django` |
| Detection | `**/requirements.txt` contains `django` |
| Rule Sets | `python-must`, `django-must` |
| Required KB | `rules/python-must.yaml`, `rules/django-must.yaml` |

Components: django-rest (web), django-orm (db), django-admin (admin), django-auth (security)

#### python-fastapi

| Property | Value |
|----------|-------|
| ID | `python-fastapi` |
| Detection | `**/requirements.txt` or `**/pyproject.toml` contains `fastapi` |
| Rule Sets | `python-must` |
| Required KB | `rules/python-must.yaml` |

Components: uvicorn (server), pydantic (validation), sqlalchemy (db), redis (cache)

### Backend — Node.js

#### node-express

| Property | Value |
|----------|-------|
| ID | `node-express` |
| Detection | `**/package.json` contains `express` |
| Rule Sets | `node-must` |
| Required KB | `rules/node-must.yaml` |

Components: express-router (web), express-middleware (middleware), body-parser (parser)

#### node-nestjs

| Property | Value |
|----------|-------|
| ID | `node-nestjs` |
| Detection | `**/package.json` contains `@nestjs/core` |
| Rule Sets | `node-must` |
| Required KB | `rules/node-must.yaml` |

Components: nest-modules (module), nest-guards (security), nest-interceptors (interceptor), typeorm (db)

### Backend — Go

#### go-gin

| Property | Value |
|----------|-------|
| ID | `go-gin` |
| Detection | `**/go.mod` contains `gin-gonic/gin` |
| Rule Sets | `go-must` |
| Required KB | `rules/go-must.yaml` |

Components: gin-router (web), gin-middleware (middleware), gorm (db)

#### go-kratos

| Property | Value |
|----------|-------|
| ID | `go-kratos` |
| Detection | `**/go.mod` contains `go-kratos/kratos` |
| Rule Sets | `go-must` |
| Required KB | `rules/go-must.yaml` |

Components: kratos-proto (proto), kratos-wire (di), kratos-config (config)

### Backend — Rust

#### rust-axum

| Property | Value |
|----------|-------|
| ID | `rust-axum` |
| Detection | `**/Cargo.toml` contains `axum` |
| Rule Sets | `rust-must` |
| Required KB | `rules/rust-must.yaml` |

Components: axum-router (web), tokio-runtime (runtime), sqlx (db)

### Frontend

#### frontend-react

| Property | Value |
|----------|-------|
| ID | `frontend-react` |
| Detection | `**/package.json` contains `react` |
| Rule Sets | `frontend-must` |
| Required KB | `rules/frontend-must.yaml` |

Components: react-router (routing), redux (state), axios (http), jest (testing)

#### frontend-vue

| Property | Value |
|----------|-------|
| ID | `frontend-vue` |
| Detection | `**/package.json` contains `vue` |
| Rule Sets | `frontend-must` |
| Required KB | `rules/frontend-must.yaml` |

Components: vue-router (routing), vuex (state), axios (http), vitest (testing)

### Infrastructure

#### infra-terraform

| Property | Value |
|----------|-------|
| ID | `infra-terraform` |
| Detection | `**/*.tf` |
| Rule Sets | `infra-must` |
| Required KB | `rules/infra-must.yaml` |

Components: terraform-aws (cloud), terraform-k8s (orchestration)

### Mobile

#### mobile-android

| Property | Value |
|----------|-------|
| ID | `mobile-android` |
| Detection | `**/build.gradle` or `**/build.gradle.kts` contains `com.android.application` |
| Rule Sets | `mobile-must` |
| Required KB | `rules/mobile-must.yaml` |

Components: android-activity (ui), android-fragment (ui), retrofit (http), room (db)

#### mobile-flutter

| Property | Value |
|----------|-------|
| ID | `mobile-flutter` |
| Detection | `**/pubspec.yaml` contains `flutter` |
| Rule Sets | `mobile-must` |
| Required KB | `rules/mobile-must.yaml` |

Components: flutter-bloc (state), dio (http), hive (db)

#### mobile-ios

| Property | Value |
|----------|-------|
| ID | `mobile-ios` |
| Detection | `**/Package.swift` or `**/*.xcodeproj` |
| Rule Sets | `mobile-must` |
| Required KB | `rules/mobile-must.yaml` |

Components: uikit (ui), alamofire (http), coredata (db)

### Data

#### data-spark

| Property | Value |
|----------|-------|
| ID | `data-spark` |
| Detection | `**/pom.xml` contains `spark-core` or `**/requirements.txt` contains `pyspark` |
| Rule Sets | `data-must` |
| Required KB | `rules/data-must.yaml` |

Components: spark-sql (sql), spark-streaming (streaming), spark-ml (ml)

### Generic

#### no-tech

| Property | Value |
|----------|-------|
| ID | `no-tech` |
| Detection | (none — fallback adapter) |
| Rule Sets | (none) |
| Required KB | (none) |

The `no-tech` adapter is used when no technology-specific adapter matches. It disables rule enforcement and has no components.