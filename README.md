# nfprogress

## Accessibility

This project supports dynamic text scaling. The interface is tested with the **Larger Text** accessibility option on iOS and macOS. We officially guarantee correct layout for scale factors from **1.0** to **3.0**. Layout is verified by UI tests at scales 1.59, 2.0, 2.5 and 3.0. Larger values may work on a best‑effort basis.

## Contributing

Before opening a pull request run the linter:

```bash
make lint
```

UI tests live in the `nfprogressUITests` target and can be launched locally with:

```bash
make test    # or `make test-ios` to call xcodebuild directly
# for macOS builds use `make test-macos`
```

The linter also runs automatically as part of the CI workflow.

## Requirements

* Xcode 15 or later
* Swift 5.9

## Known Issues

GitHub's macOS images occasionally ship without the latest iPhone simulator. If CI fails when booting the device, check that the runner image contains "iPhone 15 Pro (latest)" and update the workflow accordingly.
