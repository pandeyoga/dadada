export default [
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      "no-use-before-define": ["error", { functions: false, classes: false, variables: true, allowNamedExports: true }],
    },
  },
];
