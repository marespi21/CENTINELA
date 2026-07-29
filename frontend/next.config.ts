import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Salida autónoma para contenedores (Sprint 6): Next empaqueta un server.js
  // mínimo con SOLO las dependencias que el runtime necesita, en vez de
  // arrastrar todo node_modules. Mismo criterio que las imágenes del backend.
  output: "standalone",
};

export default nextConfig;
