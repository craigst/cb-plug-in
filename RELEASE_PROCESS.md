# Release Process

This document describes how to create new releases for the Chaturbate Bridge integration.

## Prerequisites

- Git access to the repository
- Write access to GitHub repository
- Version number decided (following semantic versioning)

## Release Steps

### 1. Update Version Numbers

Update the version in two files:

**`custom_components/chaturbate_bridge/manifest.json`:**
```json
{
  "version": "X.Y.Z",
  ...
}
```

**`custom_components/chaturbate_bridge/const.py`:**
```python
INTEGRATION_VERSION = "X.Y.Z"
```

### 2. Commit and Push Changes

```bash
git add custom_components/chaturbate_bridge/manifest.json custom_components/chaturbate_bridge/const.py
git commit -m "chore: Bump version to X.Y.Z"
git push origin main
```

### 3. Create Git Tag

```bash
git tag -a vX.Y.Z -m "vX.Y.Z - Release Title"
git push origin vX.Y.Z
```

### 4. Create GitHub Release

Go to: https://github.com/craigst/cb-plug-in/releases/new

1. Click "Choose a tag" and select `vX.Y.Z`
2. Set release title: `vX.Y.Z - Release Title`
3. Add release notes (see template below)
4. Click "Publish release"

## Release Notes Template

```markdown
# vX.Y.Z - Release Title

## New Features
- Feature 1 description
- Feature 2 description

## Improvements
- Improvement 1
- Improvement 2

## Bug Fixes
- Fix 1
- Fix 2

## Configuration
New/changed options:
- Option 1
- Option 2

## Installation

### New Installation
1. Add this repository to HACS
2. Download "Chaturbate Bridge"
3. Restart Home Assistant
4. Add integration via Settings → Integrations

### Upgrade from Previous Version
1. Update via HACS
2. Restart Home Assistant
3. [Any specific upgrade steps]

## Files Changed
- Added: [files]
- Modified: [files]
- Removed: [files]
```

## How HACS Detects Updates

With `"zip_release": true` in `hacs.json`, HACS:

1. **Checks for new releases** on GitHub
2. **Compares version** in manifest.json with installed version
3. **Shows update notification** to users
4. **Downloads release** when user clicks Update

### Update Timing
- HACS checks for updates every 30 minutes
- Users can force check: HACS → ⋮ → Reload HACS data

## Semantic Versioning

Follow [Semantic Versioning](https://semver.org/):

- **Major (X.0.0)**: Breaking changes, incompatible API changes
- **Minor (x.Y.0)**: New features, backward compatible
- **Patch (x.y.Z)**: Bug fixes, backward compatible

### Examples:
- `7.6.0` → `7.7.0`: New storage management features (minor)
- `7.7.0` → `7.7.1`: Bug fix in file manager (patch)
- `7.7.0` → `8.0.0`: Breaking config changes (major)

## Checklist

Before creating a release:

- [ ] All changes committed and pushed
- [ ] Version updated in `manifest.json`
- [ ] Version updated in `const.py`
- [ ] Git tag created and pushed
- [ ] GitHub release created with notes
- [ ] Release notes are clear and complete
- [ ] Any breaking changes are clearly documented
- [ ] Upgrade instructions provided (if needed)

## After Release

1. **Verify HACS**: Check that HACS shows the new version (may take 30 mins)
2. **Test Update**: Update on a test instance before announcing
3. **Announce**: Post in relevant communities if significant changes

## Quick Reference

```bash
# Update version files
# Edit manifest.json and const.py manually

# Commit and push
git add custom_components/chaturbate_bridge/manifest.json custom_components/chaturbate_bridge/const.py
git commit -m "chore: Bump version to X.Y.Z"
git push origin main

# Create and push tag
git tag -a vX.Y.Z -m "vX.Y.Z - Release Title"
git push origin vX.Y.Z

# Then create release on GitHub web interface
```

## Troubleshooting

### HACS Not Showing Update
1. Wait 30 minutes for HACS to check
2. Force reload: HACS → ⋮ → Reload HACS data
3. Verify manifest.json version is higher than installed
4. Check GitHub release exists and is published

### Users Can't See Update
1. Verify release is published (not draft)
2. Check `zip_release: true` in hacs.json
3. Ensure tag matches manifest.json version
4. Tell users to reload HACS data

### Wrong Version Showing
1. Clear Home Assistant cache
2. Restart Home Assistant
3. Reinstall integration via HACS
