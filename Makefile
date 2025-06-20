lint:
	bash Scripts/checkTextScale.sh


test-ios:
	xcodebuild test -workspace nfprogress.xcworkspace -scheme nfprogress -destination 'platform=iOS Simulator,OS=latest,name=iPhone 15 Pro' CODE_SIGNING_ALLOWED=NO -parallel-testing-enabled YES


test: test-ios


test-macos:
	xcodebuild test -workspace nfprogress.xcworkspace -scheme nfprogress -destination 'platform=macOS' CODE_SIGNING_ALLOWED=NO -skipPackagePluginValidation YES


test-clean:
	rm -rf ~/Library/Developer/Xcode/DerivedData
