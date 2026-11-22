'use client';

import { AlertTriangle, BookOpen, Database, GitBranch, ShieldCheck } from 'lucide-react';
import { Badge, Card, CardHeader, PageHeading } from './ui';

const SECTIONS = [
  {
    icon: Database,
    title: 'Synthetic data methodology',
    bullets: [
      'Ten fictional hospitals form the NovaCare Health Network with deliberately different capacity, specialty mix and demand profiles.',
      'A fixed seed generates reproducible records across a 24-month reporting window; actual counts are reported in the pipeline manifest.',
      'Every patient, clinician, facility, transaction and financial value is fictional. No real patient data is used.',
    ],
  },
  {
    icon: GitBranch,
    title: 'Data model and ETL',
    bullets: [
      'Bronze retains raw source files; silver standardises types, statuses and identifiers; gold holds business-ready analytical tables.',
      'Invalid records are quarantined with rule IDs instead of being silently discarded.',
      'Fact grains are explicit: appointment, encounter, admission, bed snapshot, lab order, invoice line, payment and claim event.',
      'DuckDB materialises the gold tables that the FastAPI layer queries for every frontend metric.',
    ],
  },
  {
    icon: ShieldCheck,
    title: 'KPI definitions and validation',
    bullets: [
      'Each KPI has a documented definition, formula, numerator, denominator, grain, exclusions, source and caveat in the glossary.',
      'Rates are percentages (0–100) and a null denominator produces null, never a fabricated zero.',
      'Lower-is-better metrics invert change colour so that green always means favourable and red means unfavourable.',
      'The frontend never recalculates a business KPI: the API is the single source of truth.',
    ],
  },
  {
    icon: BookOpen,
    title: 'Analysis conventions',
    bullets: [
      'Global filters are stored in the URL, so any view can be shared or refreshed with the same context.',
      'Comparisons use the previous equivalent period supplied by the API.',
      'Unfiltered benchmarks are labelled explicitly wherever they appear.',
      'Sentiment labels and experience categories are synthetic or algorithmically generated for this educational dataset.',
    ],
  },
];

export function MethodologyPage() {
  return (
    <div className="min-w-0 space-y-6">
      <PageHeading title="Methodology & Disclaimer" description="How HOSPITAL 360 generates, validates and presents its synthetic healthcare analytics." badge={<Badge tone="info">Documentation</Badge>} />

      <div className="grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-2 [&>*]:min-w-0">
        {SECTIONS.map((section) => {
          const Icon = section.icon;
          return (
          <Card key={section.title}>
            <CardHeader title={section.title} action={<Icon className="h-4 w-4 text-teal" />} />
            <ul className="space-y-2 p-5 text-xs leading-relaxed text-muted">
              {section.bullets.map((bullet) => (
                <li key={bullet} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          </Card>
          );
        })}
      </div>

      <Card className="border-warning/30 bg-warning-light/50">
        <div className="flex gap-3 p-5">
          <AlertTriangle className="h-5 w-5 shrink-0 text-warning" />
          <div>
            <h2 className="text-sm font-semibold text-ink">Known limitations and disclaimer</h2>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              HOSPITAL 360 is an educational portfolio project built on entirely synthetic data. It is not a clinical system, does not use real
              patient records, and must not be used for diagnosis, treatment decisions, or operational management of a real healthcare
              organisation. Values shown in the interface come from the API; where the API is unavailable the interface shows an explicit
              error or empty state rather than invented numbers. Statistical assumptions, hospital-profile differences and intentional data
              quality issues are described by the generator, manifest and ETL documentation in the project repository.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
