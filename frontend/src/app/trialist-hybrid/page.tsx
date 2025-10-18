import TrialistHybridParser from '@/features/trialist-hybrid/components/parser';

export const metadata = {
  title: 'Trialist Hybrid Parser | RWE Platform',
  description: 'Convert clinical trial criteria to executable MIMIC-IV SQL queries',
};

export default function TrialistHybridPage() {
  return <TrialistHybridParser />;
}
