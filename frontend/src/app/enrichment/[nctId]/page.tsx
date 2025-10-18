import { EnrichmentView } from '@/features/enrichment/components/EnrichmentView';
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from '@tanstack/react-query';
import { fetchEnrichmentData } from '@/features/enrichment/api';
import { notFound } from 'next/navigation';

interface PageProps {
  params: Promise<{
    nctId: string;
  }>;
}

export default async function EnrichmentResultPage({ params }: PageProps) {
  const { nctId } = await params;

  // Validate NCT ID format
  if (!/^NCT\d{8}$/i.test(nctId)) {
    notFound();
  }

  const queryClient = new QueryClient();
  const normalizedNctId = nctId.toUpperCase();

  // Pre-fetch the data on the server for faster initial load
  try {
    await queryClient.prefetchQuery({
      queryKey: ['enrichment', normalizedNctId],
      queryFn: () => fetchEnrichmentData(normalizedNctId),
    });
  } catch (error) {
    // Don't fail server-side render if pre-fetch fails
    // Let client-side query handle the error
    console.error('Failed to prefetch enrichment data:', error);
  }

  return (
    <main className="container mx-auto px-4 py-8">
      <HydrationBoundary state={dehydrate(queryClient)}>
        <EnrichmentView nctId={normalizedNctId} />
      </HydrationBoundary>
    </main>
  );
}
