import type { Metadata } from "next";
import "./styles.css";
import { LearnerHeader } from "@/features/auth/LearnerHeader";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "CourseFlow Learning",
  description: "CourseFlow learner experience and public course discovery"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Providers>
          <LearnerHeader />
          {children}
        </Providers>
      </body>
    </html>
  );
}
