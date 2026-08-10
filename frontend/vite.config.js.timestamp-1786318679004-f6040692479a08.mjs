// vite.config.js
import { defineConfig } from "file:///C:/Users/Fabian%20Paternina/OneDrive%20-%20Hogar%20y%20Moda%20S.A.S/Documentos/ADMIN%20DA/it-admin-platform/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///C:/Users/Fabian%20Paternina/OneDrive%20-%20Hogar%20y%20Moda%20S.A.S/Documentos/ADMIN%20DA/it-admin-platform/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import tailwindcss from "file:///C:/Users/Fabian%20Paternina/OneDrive%20-%20Hogar%20y%20Moda%20S.A.S/Documentos/ADMIN%20DA/it-admin-platform/frontend/node_modules/@tailwindcss/vite/dist/index.mjs";
import path from "path";
var __vite_injected_original_dirname = "C:\\Users\\Fabian Paternina\\OneDrive - Hogar y Moda S.A.S\\Documentos\\ADMIN DA\\it-admin-platform\\frontend";
var vite_config_default = defineConfig({
  plugins: [
    vue(),
    tailwindcss()
  ],
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src")
    }
  },
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxVc2Vyc1xcXFxGYWJpYW4gUGF0ZXJuaW5hXFxcXE9uZURyaXZlIC0gSG9nYXIgeSBNb2RhIFMuQS5TXFxcXERvY3VtZW50b3NcXFxcQURNSU4gREFcXFxcaXQtYWRtaW4tcGxhdGZvcm1cXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkM6XFxcXFVzZXJzXFxcXEZhYmlhbiBQYXRlcm5pbmFcXFxcT25lRHJpdmUgLSBIb2dhciB5IE1vZGEgUy5BLlNcXFxcRG9jdW1lbnRvc1xcXFxBRE1JTiBEQVxcXFxpdC1hZG1pbi1wbGF0Zm9ybVxcXFxmcm9udGVuZFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vQzovVXNlcnMvRmFiaWFuJTIwUGF0ZXJuaW5hL09uZURyaXZlJTIwLSUyMEhvZ2FyJTIweSUyME1vZGElMjBTLkEuUy9Eb2N1bWVudG9zL0FETUlOJTIwREEvaXQtYWRtaW4tcGxhdGZvcm0vZnJvbnRlbmQvdml0ZS5jb25maWcuanNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xuaW1wb3J0IHZ1ZSBmcm9tICdAdml0ZWpzL3BsdWdpbi12dWUnXG5pbXBvcnQgdGFpbHdpbmRjc3MgZnJvbSAnQHRhaWx3aW5kY3NzL3ZpdGUnXG5pbXBvcnQgcGF0aCBmcm9tICdwYXRoJ1xuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbXG4gICAgdnVlKCksXG4gICAgdGFpbHdpbmRjc3MoKSxcbiAgXSxcbiAgcmVzb2x2ZToge1xuICAgIGFsaWFzOiB7XG4gICAgICAnQCc6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsICcuL3NyYycpLFxuICAgIH0sXG4gIH0sXG4gIHNlcnZlcjoge1xuICAgIHByb3h5OiB7XG4gICAgICAnL2FwaSc6IHtcbiAgICAgICAgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMTo4MDAwJyxcbiAgICAgICAgY2hhbmdlT3JpZ2luOiB0cnVlXG4gICAgICB9XG4gICAgfVxuICB9XG59KVxuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUFrZ0IsU0FBUyxvQkFBb0I7QUFDL2hCLE9BQU8sU0FBUztBQUNoQixPQUFPLGlCQUFpQjtBQUN4QixPQUFPLFVBQVU7QUFIakIsSUFBTSxtQ0FBbUM7QUFLekMsSUFBTyxzQkFBUSxhQUFhO0FBQUEsRUFDMUIsU0FBUztBQUFBLElBQ1AsSUFBSTtBQUFBLElBQ0osWUFBWTtBQUFBLEVBQ2Q7QUFBQSxFQUNBLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssS0FBSyxRQUFRLGtDQUFXLE9BQU87QUFBQSxJQUN0QztBQUFBLEVBQ0Y7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFFBQVE7QUFBQSxRQUNOLFFBQVE7QUFBQSxRQUNSLGNBQWM7QUFBQSxNQUNoQjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
