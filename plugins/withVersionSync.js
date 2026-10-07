// Make app.json the single source of truth for the version shown in Xcode.
// Expo writes CFBundleShortVersionString/CFBundleVersion into Info.plist, but leaves the Xcode project's
// MARKETING_VERSION / CURRENT_PROJECT_VERSION at their template defaults (1.0 / 1).
const { withXcodeProject } = require('@expo/config-plugins');

module.exports = (config) =>
  withXcodeProject(config, (c) => {
    const version = c.version;
    const build = String(c.ios?.buildNumber ?? '1');
    const configs = c.modResults.pbxXCBuildConfigurationSection();
    for (const key of Object.keys(configs)) {
      const settings = configs[key].buildSettings;
      if (settings && settings.PRODUCT_NAME) {
        settings.MARKETING_VERSION = version;
        settings.CURRENT_PROJECT_VERSION = build;
      }
    }
    return c;
  });
