import "./globals.css";

export const metadata = {
  title: "RGV — Medical Simplification",
  description: "Research prototype exploring retrieval-grounded verification for patient-oriented medical report simplification.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
