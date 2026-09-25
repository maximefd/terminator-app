import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ImageResponse } from "next/og";
import { site } from "@/config/site";
import { OG_IMAGE } from "@/lib/seo";

// Image de partage (réseaux sociaux, messageries), écrite au build dans out/og.png. Une route plutôt que
// opengraph-image.tsx : l'export statique écrirait ce dernier sans extension, et Pages le servirait sans type.
export const dynamic = "force-static";

const size = { width: OG_IMAGE.width, height: OG_IMAGE.height };

// Le motif de la recherche, en cases de grille : ce que le site sait faire, lisible en vignette
const PATTERN = ["P", "?", "?", "L", "E"];

export async function GET() {
  const font = await readFile(join(process.cwd(), "public/fonts/archivo-narrow-700.ttf"));
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "#ffffff",
          color: "#0f172a",
          fontFamily: "Archivo Narrow",
        }}
      >
        <div style={{ display: "flex", gap: "12px", marginBottom: "48px" }}>
          {PATTERN.map((letter, index) => (
            <div
              key={index}
              style={{
                width: "96px",
                height: "96px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "4px solid #0f172a",
                fontSize: "64px",
                color: letter === "?" ? "#94a3b8" : "#0f172a",
              }}
            >
              {letter}
            </div>
          ))}
        </div>
        <div style={{ fontSize: "112px", lineHeight: 1 }}>{site.name}</div>
        <div style={{ fontSize: "52px", marginTop: "24px", color: "#475569" }}>{site.tagline.charAt(0).toUpperCase() + site.tagline.slice(1)}</div>
      </div>
    ),
    { ...size, fonts: [{ name: "Archivo Narrow", data: font, weight: 700, style: "normal" }] },
  );
}
