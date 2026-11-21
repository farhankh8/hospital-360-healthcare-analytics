import type { Metadata } from 'next';
import { Suspense } from 'react';
import './globals.css';
import { AppShell } from '@/components/AppShell';
import { DrilldownProvider } from '@/components/DrilldownDrawer';
import { QueryProvider } from '@/components/QueryProvider';
import { FilterProvider } from '@/lib/filters';

export const metadata: Metadata = {
  title: 'HOSPITAL 360 | Healthcare Intelligence',
  description: 'Synthetic multi-hospital healthcare operations and analytics platform.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <Suspense
            fallback={
              <div className="flex min-h-screen items-center justify-center bg-canvas text-sm text-slate-600">
                Loading HOSPITAL 360…
              </div>
            }
          >
            <FilterProvider>
              <DrilldownProvider>
                <AppShell>{children}</AppShell>
              </DrilldownProvider>
            </FilterProvider>
          </Suspense>
        </QueryProvider>
      </body>
    </html>
  );
}
