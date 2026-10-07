/**
 * Expo config plugin: adopt the UIScene life cycle in the generated iOS project (Expo's own ExpoAppSceneDelegate).
 *
 * Apps built with the iOS 27 SDK (Xcode 27) must use the scene-based life cycle, otherwise they are stopped at launch:
 *   "UIScene life cycle is required for apps built with this SDK."
 * Expo SDK 57 (57.0.23+) ships ExpoAppSceneDelegate, but the prebuild template still uses the app life cycle
 * (SDK 58 is expected to use scenes by default). This plugin applies the opt-in:
 *   - Info.plist: add UIApplicationSceneManifest pointing at SceneDelegate
 *   - AppDelegate.swift: conform to ExpoReactNativeFactoryProvider, stop creating the window there, add
 *     `class SceneDelegate: ExpoAppSceneDelegate {}` (window creation, React Native start, deep links and
 *     life-cycle events are handled by ExpoAppSceneDelegate).
 *
 * ios/ is generated (git-ignored), so the change is applied at prebuild time. Idempotent.
 * Remove this plugin once the Expo template does it by default.
 */
const { withAppDelegate, withInfoPlist } = require('expo/config-plugins');

const TAG = 'withSceneLifecycle';

const SCENE_DELEGATE = `
// ${TAG}: UIScene life cycle (required by the iOS 27 SDK). Everything is done by ExpoAppSceneDelegate.
class SceneDelegate: ExpoAppSceneDelegate {}
`;

/** AppDelegate.swift: conform to ExpoReactNativeFactoryProvider, drop the window creation, append SceneDelegate. */
function patchAppDelegateSwift(src) {
  if (src.includes(`// ${TAG}`)) return src;

  const classRe = /class AppDelegate: ExpoAppDelegate \{/;
  if (!classRe.test(src)) throw new Error(`${TAG}: could not find "class AppDelegate: ExpoAppDelegate" in AppDelegate.swift`);
  let out = src.replace(classRe, 'class AppDelegate: ExpoAppDelegate, ExpoReactNativeFactoryProvider { // ' + TAG);

  const blockRe = /[ \t]*#if os\(iOS\) \|\| os\(tvOS\)\s*\n\s*window = UIWindow\(frame: UIScreen\.main\.bounds\)\s*\n\s*factory\.startReactNative\(\s*\n\s*withModuleName: "([^"]+)",\s*\n\s*in: window,\s*\n\s*launchOptions: launchOptions\)\s*\n[ \t]*#endif\n/;
  const m = out.match(blockRe);
  if (!m) throw new Error(`${TAG}: could not find the window creation block in AppDelegate.swift`);
  if (m[1] !== 'main') throw new Error(`${TAG}: module name is "${m[1]}"; add "var reactNativeFactoryModuleName" to AppDelegate`);
  out = out.replace(blockRe, `    // ${TAG}: the window and the React Native root view are created by SceneDelegate (ExpoAppSceneDelegate).\n`);

  return out.replace(/\s*$/, '\n') + SCENE_DELEGATE;
}

/** Info.plist: add the scene manifest. */
function addSceneManifest(plist) {
  plist.UIApplicationSceneManifest = {
    UIApplicationSupportsMultipleScenes: false,
    UISceneConfigurations: {
      UIWindowSceneSessionRoleApplication: [
        {
          UISceneConfigurationName: 'Default Configuration',
          UISceneDelegateClassName: '$(PRODUCT_MODULE_NAME).SceneDelegate',
        },
      ],
    },
  };
  return plist;
}

const withSceneLifecycle = (config) => {
  config = withAppDelegate(config, (cfg) => {
    if (cfg.modResults.language !== 'swift') {
      throw new Error(`${TAG}: only the Swift AppDelegate is supported`);
    }
    cfg.modResults.contents = patchAppDelegateSwift(cfg.modResults.contents);
    return cfg;
  });
  return withInfoPlist(config, (cfg) => {
    cfg.modResults = addSceneManifest(cfg.modResults);
    return cfg;
  });
};

module.exports = withSceneLifecycle;
module.exports.patchAppDelegateSwift = patchAppDelegateSwift;
module.exports.addSceneManifest = addSceneManifest;
