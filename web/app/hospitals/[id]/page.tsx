'use client';

import { useParams } from 'next/navigation';
import { AnalyticsPage } from '@/components/AnalyticsPage';
import { buildHospitalProfileConfig } from '@/lib/page-configs';

export default function Page() {
  const params = useParams<{ id: string }>();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;
  return <AnalyticsPage config={buildHospitalProfileConfig(id)} />;
}
