/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // On garde cette option pour les tests locaux, mais elle peut causer des avertissements.
    // La configuration ci-dessous est une version plus robuste.
  },
};

// LA CORRECTION DÉFINITIVE EST ICI :
// On applique la configuration expérimentale uniquement en mode développement.
if (process.env.NODE_ENV === 'development') {
  nextConfig.experimental = {
    ...nextConfig.experimental,
    allowedDevOrigins: [
      "http://localhost:3000",
      "http://192.168.1.56:3000",
      "http://192.0.0.2:3000", // On garde les adresses possibles
    ],
  };
}

export default nextConfig;