# Documentation for Commit 47a5e7a

**Commit Hash:** 47a5e7a077912f334a7b57b81d15ed626e6582e7
**Commit Message:** refactor(git): Update doc filename to use commit message
**Generated:** Mon Oct 13 18:04:08 EDT 2025
**Repository:** CommitLM

---

### **Commit Documentation Filename Enhancement**

This document outlines the changes to the filename generation logic for automatically created commit documentation.

---

### 1. Summary

The naming convention for generated documentation files has been updated to be more descriptive and human-readable. Previously, filenames were generated using a timestamp and a short commit hash. The new implementation uses a sanitized version of the commit message, making it easier to identify the content of a document directly from its filename.

### 2. Changes

The core modification is within the git hook script responsible for triggering the documentation generation.

#### **Previous Logic (Removed)**

The old method created a filename based on the current timestamp and the short commit hash.

*   **Format:** `docs/commit_<SHORT_HASH>_<TIMESTAMP>.md`
*   **Example:** `docs/commit_a1b2c3d_20231027_103000.md`

```bash
# Generate timestamp for filename
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
DOC_FILENAME="docs/commit_${COMMIT_SHORT}_${TIMESTAMP}.md"
```

#### **New Logic (Added)**

The new method generates a filename by sanitizing the commit message and appending the short commit hash for uniqueness.

*   **Format:** `docs/commit_<SANITIZED_MESSAGE>_<SHORT_HASH>.md`
*   **Example:** `docs/commit_feat-add-new-login-button_a1b2c3d.md`

The sanitization process involves the following steps:
1.  Convert the commit message to lowercase.
2.  Remove all special characters except for letters, numbers, spaces, and hyphens.
3.  Replace one or more spaces with a single hyphen.
4.  Collapse multiple consecutive hyphens into a single one.
5.  Truncate the string to a maximum of 50 characters.
6.  Remove any trailing hyphens.
7.  If the sanitization process results in an empty string, it defaults to `unnamed`.

```bash
# Sanitize commit message for use in filename
SANITIZED_MSG=$(echo "$COMMIT_MSG" | \\
    tr '[:upper:]' '[:lower:]' | \\
    sed 's/[^a-z0-9 -]//g' | \\
    sed 's/ /-/g' | \\
    sed 's/--*/-/g' | \\
    cut -c1-50)

# Remove trailing hyphens
SANITIZED_MSG=$(echo "$SANITIZED_MSG" | sed 's/-*$//')

# Fallback to "unnamed" if sanitization results in empty string
if [ -z "$SANITIZED_MSG" ]; then
    SANITIZED_MSG="unnamed"
fi

# Generate filename with sanitized message and short hash for uniqueness
DOC_FILENAME="docs/commit_${SANITIZED_MSG}_${COMMIT_SHORT}.md"
```

### 3. Impact

*   **Improved Readability:** Filenames are now descriptive, allowing developers to understand the purpose of a commit's documentation without opening the file.
*   **Enhanced Discoverability:** Searching for documentation related to a specific feature or fix is now more straightforward using standard file system search tools.
*   **Better Organization:** The `docs/` directory becomes easier to navigate and browse.
*   The core functionality of generating documentation content remains unchanged.

### 4. Usage

This change is an internal improvement to the `commitlm` git integration. Users do not need to alter their workflow. The new filename format will be applied automatically to all new commits once this update is in place.

**Example Scenario:**

Consider a commit with the message: `feat(auth): Implement the new 'Forgot Password' flow!` and a short hash of `f4a3b2c`.

*   **Before:** The generated file would be named `docs/commit_f4a3b2c_20231027_114515.md`.
*   **After:** The new file will be named `docs/commit_feat-auth-implement-the-new-forgot-password-flow_f4a3b2c.md`.

### 5. Breaking Changes

While there are no API or command-line breaking changes, this update alters a file generation pattern. Any external scripts or tooling that relied on the previous `commit_<HASH>_<TIMESTAMP>.md` format for parsing or file management will need to be updated to accommodate the new, more descriptive format.

### 6. Migration Notes

No manual migration is required for existing documentation files; they will retain their original timestamp-based names. All documentation generated after this change will automatically use the new naming convention. If consistency is desired, a separate script could be written to rename old files, but this is not required for the tool to function.