// PostCSS 处理链。
// 先由 Tailwind 展开工具类，再由 Autoprefixer 补浏览器兼容前缀。
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
