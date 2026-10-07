// Build Expo modules from source instead of the precompiled xcframeworks.
// With Xcode 27 the precompiled ExpoModulesCore breaks ExpoDomWebView ("AppContext has no member 'runtime'").
const { withPodfileProperties } = require('@expo/config-plugins');

module.exports = (config) =>
  withPodfileProperties(config, (c) => {
    c.modResults.EXPO_USE_PRECOMPILED_MODULES = 'false';
    return c;
  });
