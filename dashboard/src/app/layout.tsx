import "./styles.css";
import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
