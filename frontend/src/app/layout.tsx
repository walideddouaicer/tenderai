import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TenderAI — Analyse de marchés publics",
  description: "Interrogez vos documents d'appel d'offres en langage naturel.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
