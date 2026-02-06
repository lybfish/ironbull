const CompressionWebpackPlugin = require('compression-webpack-plugin');

module.exports = {
  assetsDir: 'assets',
  outputDir: 'dist',
  publicPath: process.env.NODE_ENV === 'production' ? '/' : '/',
  productionSourceMap: false,
  transpileDependencies: ['element-ui', 'ele-admin', 'vue-i18n'],

  devServer: {
    port: 5174,
    proxy: {
      // data-api 后端（/api/*）
      '/api': {
        target: process.env.VUE_APP_API_PROXY || 'http://127.0.0.1:8026',
        changeOrigin: true,
        secure: false,
        ws: true
      },
      // signal-monitor 后端（/signal-api/*  → 8020/api/*）
      '/signal-api': {
        target: process.env.VUE_APP_SIGNAL_PROXY || 'http://127.0.0.1:8020',
        changeOrigin: true,
        secure: false,
        pathRewrite: {'^/signal-api': '/api'}
      }
    }
  },

  chainWebpack: (config) => {
    config.plugins.delete('prefetch');
    if (process.env.NODE_ENV === 'production') {
      config.plugin('compressionPlugin').use(new CompressionWebpackPlugin({
        test: /\.(js|css|html)$/,
        threshold: 10240,
        deleteOriginalAssets: false
      }));
    }
  },

  css: {
    loaderOptions: {
      sass: {
        sassOptions: {
          outputStyle: 'expanded'
        }
      }
    }
  }
};
