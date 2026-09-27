import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const config = [
  { ignores: [".next/**", "node_modules/**", "public/mediapipe/**", "public/sw.js"] },
  ...compat.extends("next/core-web-vitals"),
  { rules: { "react/no-unescaped-entities": "off", "@next/next/no-img-element": "off" } },
];

export default config;
