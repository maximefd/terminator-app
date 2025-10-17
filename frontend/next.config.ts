/** @type {import('next').NextConfig} */
const nextConfig = {
  // On ajoute cette section pour autoriser explicitement les adresses
  // utilisées pendant le développement et les tests.
  experimental: {
    allowedDevOrigins: [
      "http://localhost:3000",
      "http://192.168.1.56:3000", // On ajoute votre adresse IP réseau ici
    ],
  },
};

export default nextConfig;
