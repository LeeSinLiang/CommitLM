# Documentation for Commit c29e14a

**Commit Hash:** c29e14a0f4cdd6b06411b530e637106229e3dcef
**Commit Message:** chore(pyproject): update version and license format
**Generated:** Tue Oct 14 17:40:52 EDT 2025
**Repository:** CommitLM

---

# Documentation: Project Metadata Update and Version Bump

This update introduces changes to the project's packaging metadata for improved standards compliance and bumps the package version.

### Summary

The project version has been updated from `1.0.6` to `1.0.8`. Additionally, the `pyproject.toml` file has been modified to align with modern Python packaging standards (PEP 621) by simplifying the license declaration format.

### Changes

1.  **Version Increment**:
    *   The package version in `pyproject.toml` has been bumped to `1.0.8`.
        ```diff
        - version = "1.0.6"
        + version = "1.0.8"
        ```

2.  **License Metadata Standardization**:
    *   The `license` field in `pyproject.toml` was updated from a table format to a direct string value. This is a syntax simplification that aligns with current best practices.
        ```diff
        - license = {text = "Apache-2.0"}
        + license = "Apache-2.0"
        ```

3.  **Classifier Cleanup**:
    *   The redundant `License :: OSI Approved :: Apache Software License` classifier was removed. The primary `license` field is sufficient for modern packaging tools to correctly identify and categorize the license.
        ```diff
        - "License :: OSI Approved :: Apache Software License",
        ```

### Impact

*   **No Functional Change**: These modifications affect project metadata and packaging only. There are no changes to the application's runtime behavior, features, or API.
*   **Improved Packaging Compliance**: The changes ensure the project's configuration is clean and compliant with the latest packaging specifications, improving interoperability with tools like `pip` and `build`.
*   **New Release**: The version bump signifies a new release that will be available on package repositories like PyPI.

### Usage

There are no changes to how the `commitlm` tool is used. All existing commands and workflows remain the same.

### Breaking Changes

There are no breaking changes in this update.

### Migration Notes

No migration steps are required for end-users of the package. This update is fully backward compatible.