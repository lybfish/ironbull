module.exports = {
    root: true,
    env: {
        node: true,
        browser: true,
        es6: true
    },
    extends: [
        'plugin:vue/essential',
        'eslint:recommended'
    ],
    parserOptions: {
        parser: 'babel-eslint',
        ecmaVersion: 2020,
        sourceType: 'module'
    },
    rules: {
        // 关闭规则
        'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
        'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
        'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
        
        // Vue 相关规则
        'vue/multi-word-component-names': 'off',
        'vue/no-v-model-argument': 'off',
        
        // 代码风格
        'quotes': ['warn', 'single', { avoidEscape: true }],
        'semi': ['warn', 'never'],
        'comma-dangle': ['warn', 'never'],
        'indent': ['warn', 2, { SwitchCase: 1 }],
        'no-trailing-spaces': 'warn',
        'eol-last': ['warn', 'always'],
        
        // 最佳实践
        'eqeqeq': ['warn', 'always'],
        'curly': ['warn', 'all'],
        'no-var': 'warn',
        'prefer-const': 'warn',
        'prefer-arrow-callback': 'warn'
    }
}
