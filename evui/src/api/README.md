## evui 前端 API 目录说明

本目录用于统一管理前端接口调用，业务页面尽量不要直接写 `this.$http.get/post('/xxx')`。

### 约定
- **每个模块一个文件**：`evui/src/api/<module>.js`
- **字典公共接口**：`evui/src/api/dict.js`
- **axios 实例**：直接 `import axios from 'axios'`（拦截器在 `src/config/axios-config.js` 中已全局配置）


