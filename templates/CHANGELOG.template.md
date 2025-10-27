# Changelog

All notable changes to this hook will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- List new features added but not yet released

### Changed
- List changes to existing functionality

### Deprecated
- List features that will be removed in future versions

### Removed
- List features that have been removed

### Fixed
- List bug fixes

### Security
- List security fixes or improvements

## [2.0.0] - 2025-01-03 - MAJOR RELEASE EXAMPLE

### ⚠️ BREAKING CHANGES
- **Changed hook signature**: The `process()` function now requires a `context` parameter
  - Migration: Update all calls to include context object
  - Old: `process(data)`
  - New: `process(data, context)`
- **Removed deprecated `--legacy` flag**
  - Migration: Use `--compatibility-mode` instead
- **Changed output format from JSON to YAML**
  - Migration: Update parsers to handle YAML output

### Added
- New `context` parameter for better state management
- Support for async operations with `--async` flag
- Performance monitoring with `--metrics` option
- Batch processing capability for multiple inputs

### Changed
- Default timeout increased from 30s to 60s
- Improved error messages with actionable suggestions
- Optimized memory usage by 40%

### Deprecated
- The `--format=json` flag is deprecated, use `--output-format=json` instead
  - Will be removed in version 3.0.0
  - Migration guide: docs/migration/output-format.md

### Removed
- Removed support for Python 3.7 (minimum now Python 3.8)
- Removed deprecated `validate_old()` function
- Removed legacy configuration format support

### Fixed
- Fixed memory leak in long-running processes (#123)
- Fixed race condition in parallel execution (#456)
- Fixed incorrect validation of email addresses (#789)

### Security
- Updated dependencies to patch CVE-2025-0001
- Improved input sanitization to prevent injection attacks
- Added rate limiting to prevent DoS attacks

## [1.2.0] - 2024-12-15 - MINOR RELEASE EXAMPLE

### Added
- New optional `--cache` flag for performance improvement
- Support for environment variable configuration
- Added Welsh language support for error messages
- New helper function `validate_input()` for common validations

### Changed
- Improved logging with structured output option
- Updated documentation with more examples
- Performance improvement: 25% faster execution for large datasets

### Deprecated
- The `process_legacy()` function is deprecated
  - Use `process()` instead
  - Will be removed in version 2.0.0

### Fixed
- Fixed edge case in date parsing for leap years
- Corrected typo in error message for invalid input
- Fixed compatibility issue with Git 2.40+

## [1.1.3] - 2024-11-20 - PATCH RELEASE EXAMPLE

### Fixed
- Fixed critical bug in configuration parsing (#321)
- Fixed memory leak when processing large files (#654)
- Fixed incorrect regex pattern for URL validation (#987)
- Corrected documentation typos and broken links

### Security
- Updated third-party library to patch security vulnerability
- Improved permission checking for file operations

## [1.1.2] - 2024-11-01

### Fixed
- Performance optimization: reduced startup time by 15%
- Fixed issue with special characters in filenames
- Corrected behavior with symbolic links

## [1.1.1] - 2024-10-15

### Fixed
- Fixed compatibility with macOS 14
- Resolved issue with Unicode handling
- Fixed test failures on CI pipeline

## [1.1.0] - 2024-10-01

### Added
- Support for configuration profiles
- New `--dry-run` mode for testing
- Integration with external monitoring systems

### Changed
- Improved error recovery mechanism
- Enhanced debug output with `--verbose` flag

### Fixed
- Fixed timeout handling in network operations
- Resolved path resolution issues on Windows

## [1.0.0] - 2024-09-01 - INITIAL RELEASE

### Added
- Initial implementation of core hook functionality
- Basic validation and processing capabilities
- Support for JSON and YAML input formats
- Comprehensive test suite with 100% coverage
- Documentation and usage examples
- CI/CD pipeline integration
- Performance benchmarks

### Known Issues
- Large file processing (>100MB) may be slow
- Limited to single-threaded execution
- Windows support is experimental

## Version History Guidelines

### Format for Each Release

```markdown
## [VERSION] - YYYY-MM-DD - RELEASE TYPE

### ⚠️ BREAKING CHANGES (Only for MAJOR releases)
- **Description of breaking change**: Brief explanation
  - Migration: Step-by-step migration instructions
  - Old: Example of old usage
  - New: Example of new usage

### Added
- New features or capabilities

### Changed
- Changes to existing functionality

### Deprecated
- Features marked for future removal
  - Will be removed in version X.Y.Z
  - Migration guide: link/to/guide

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security-related fixes
```

## Examples of Good Changelog Entries

### Good ✅
- "Added support for PostgreSQL 14 with automatic migration"
- "Fixed memory leak when processing files larger than 2GB (#123)"
- "Changed default timeout from 30s to 60s to handle slower networks"
- "Deprecated `--legacy` flag in favor of `--compatibility-mode` (removal in 3.0.0)"

### Bad ❌
- "Fixed stuff" (too vague)
- "Updated code" (not specific)
- "Performance improvements" (needs metrics)
- "Bug fixes" (which bugs?)

## Migration Guide References

For breaking changes, always reference the migration guide:

```markdown
### ⚠️ BREAKING CHANGES
- **API endpoint changed from /v1 to /v2**
  - Migration guide: [docs/migration/v2-upgrade.md](docs/migration/v2-upgrade.md)
  - Deprecation notice: [blog/deprecating-v1.md](blog/deprecating-v1.md)
  - Support timeline: v1 supported until 2025-12-31
```

## Links Section (at end of file)

[Unreleased]: https://github.com/username/project/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/username/project/compare/v1.2.0...v2.0.0
[1.2.0]: https://github.com/username/project/compare/v1.1.3...v1.2.0
[1.1.3]: https://github.com/username/project/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/username/project/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/username/project/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/username/project/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/username/project/releases/tag/v1.0.0