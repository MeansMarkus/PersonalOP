/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        heading: ["Space Grotesk", "ui-sans-serif", "sans-serif"],
        body: ["Manrope", "ui-sans-serif", "sans-serif"]
      },
      colors: {
        ink: "#0f1221",
        mist: "#eef5ff",
        coral: "#ff5d3d",
        tide: "#0f7bff",
        moss: "#196f4f"
      }
    }
  },
  plugins: []
};
