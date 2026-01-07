const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

config.resolver.sourceExts = [...config.resolver.sourceExts, 'mjs'];

// Configure path aliases
config.resolver.alias = {
  ...(config.resolver.alias || {}),
  '@': path.resolve(__dirname, 'app'),
  '@services': path.resolve(__dirname, 'services'),
  '@data': path.resolve(__dirname, 'data'),
  '@theme': path.resolve(__dirname, 'theme'),
};

module.exports = config;
