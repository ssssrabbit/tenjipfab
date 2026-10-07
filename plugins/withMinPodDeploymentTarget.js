/**
 * Expo config plugin: raise too-old IPHONEOS_DEPLOYMENT_TARGET of Pods targets.
 *
 * Xcode 27 (iOS 27 SDK) only supports deployment targets 15.0 and later, but some pods (e.g. the
 * RNCAsyncStorage resource bundle, podspec says 13.4) still declare an older one, which fails the build:
 *   "The iOS Simulator deployment target 'IPHONEOS_DEPLOYMENT_TARGET' is set to 13.4, but the range of
 *    supported deployment target versions is 15.0 to 27.0.x"
 *
 * ios/ is generated (git-ignored), so the fix is applied to the Podfile at prebuild time.
 */
const fs = require('fs');
const path = require('path');
const { withDangerousMod } = require('expo/config-plugins');

const TAG = 'withMinPodDeploymentTarget';
const SNIPPET = `
    # ${TAG}: Xcode 27 rejects pod deployment targets below 15.0
    min_pod_target = Gem::Version.new(podfile_properties['ios.deploymentTarget'] || '15.1')
    installer.pods_project.targets.each do |pod_target|
      pod_target.build_configurations.each do |build_config|
        current = build_config.build_settings['IPHONEOS_DEPLOYMENT_TARGET']
        if current && Gem::Version.new(current) < min_pod_target
          build_config.build_settings['IPHONEOS_DEPLOYMENT_TARGET'] = min_pod_target.to_s
        end
      end
    end
`;

/** Insert SNIPPET right after the react_native_post_install(...) call. Idempotent. */
function patchPodfile(src) {
  if (src.includes(`# ${TAG}:`)) return src;
  const re = /(react_native_post_install\([\s\S]*?\n\s*\)\n)/;
  if (!re.test(src)) {
    throw new Error(`${TAG}: could not find react_native_post_install(...) in the Podfile`);
  }
  return src.replace(re, `$1${SNIPPET}`);
}

const withMinPodDeploymentTarget = (config) =>
  withDangerousMod(config, [
    'ios',
    async (cfg) => {
      const file = path.join(cfg.modRequest.platformProjectRoot, 'Podfile');
      fs.writeFileSync(file, patchPodfile(fs.readFileSync(file, 'utf8')));
      return cfg;
    },
  ]);

module.exports = withMinPodDeploymentTarget;
module.exports.patchPodfile = patchPodfile;
