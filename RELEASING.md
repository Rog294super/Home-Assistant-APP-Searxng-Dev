# Releasing SearXNG

1. Develop on feature branches. Image-affecting changes do not bump `version` while the app remains unreleased.
2. For a release, keep the final PR focused on the version bump and the changelog finish, including the base-image update line.
3. Merge only when the quality workflow is green. The publish workflow pushes the image before users can install the new version, so do not merge a version bump while the build is failing. Manual publish runs are restricted to `main`.
4. After the first-ever publish, make the GHCR package public and link it to the repository in GitHub package settings.
5. Once a version is published, any change to an image-affecting file, including Dependabot base-image bumps, requires a new `version`.

This repo intentionally treats the unpublished 1.4.0 version as a development version until the owner is ready to publish the first GHCR-backed release.
