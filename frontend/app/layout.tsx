import "./globals.css";

export const metadata = {
  title: "MedLens - Clinical Report Clarity",
  description: "A source-grounded medical report reader for clearer lab, scan and clinical note review.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
