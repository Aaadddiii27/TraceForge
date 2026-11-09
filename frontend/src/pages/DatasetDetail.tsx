import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Play, XCircle } from 'lucide-react';
import { useState } from 'react';
import { useDataset } from '@/hooks/useApi';
import { evaluationApi } from '@/api/client';
import type { DatasetValidationResponse } from '@/types';
import {
  Badge,
  Button,
  Card,
  CardHeader,
  CardTitle,
  CodeBlock,
  EmptyState,
  ErrorState,
  LoadingState,
  statusBadge,
  Td,
  Table,
  Tr,
} from '@/components/ui';

export default function DatasetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: dataset, isLoading, error } = useDataset(id!);
  const [validation, setValidation] = useState<DatasetValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);

  const handleValidate = async () => {
    setValidating(true);
    try {
      const result = await evaluationApi.validateDataset(id!);
      setValidation(result);
    } finally {
      setValidating(false);
    }
  };

  if (isLoading) return <div className="p-6"><LoadingState /></div>;
  if (error || !dataset) return <div className="p-6"><ErrorState message="Dataset not found" /></div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Link to="/evaluations" className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200">
          <ArrowLeft size={14} /> Evaluations
        </Link>
        <span className="text-slate-600">/</span>
        <span className="text-sm text-slate-300">{dataset.name}</span>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100">{dataset.name}</h1>
          <p className="mt-0.5 font-mono text-xs text-slate-500">{dataset.id}</p>
          {dataset.description && (
            <p className="mt-1 text-sm text-slate-400">{dataset.description}</p>
          )}
        </div>
        <Button
          variant="secondary"
          loading={validating}
          onClick={handleValidate}
        >
          Validate Dataset
        </Button>
      </div>

      {/* Validation result */}
      {validation && (
        <Card className={validation.is_valid ? 'border-emerald-500/30' : 'border-rose-500/30'}>
          <div className="flex items-center gap-3 mb-3">
            {validation.is_valid
              ? <CheckCircle2 size={18} className="text-emerald-400" />
              : <XCircle size={18} className="text-rose-400" />}
            <CardTitle>{validation.is_valid ? 'Dataset is valid' : `${validation.invalid_cases} invalid case(s)`}</CardTitle>
          </div>
          <div className="text-sm text-slate-400">
            {validation.valid_cases}/{validation.total_cases} cases valid
          </div>
          {validation.errors.length > 0 && (
            <div className="mt-3 space-y-2">
              {validation.errors.map(e => (
                <div key={e.case_index} className="rounded-lg bg-rose-500/10 px-3 py-2 text-xs">
                  <span className="font-semibold text-rose-400">Case {e.case_index}: {e.case_name ?? '(unnamed)'}</span>
                  <ul className="mt-1 list-disc list-inside text-rose-300 space-y-0.5">
                    {e.errors.map((err, i) => <li key={i}>{err}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Cases */}
      <Card className="p-0">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">Test Cases</h3>
          <span className="text-xs text-slate-500">{dataset.cases.length} cases</span>
        </div>
        {dataset.cases.length === 0 ? (
          <EmptyState title="No test cases" description="Add cases to this dataset to run evaluations." />
        ) : (
          <Table headers={['Name', 'Assertion', 'Tags', 'Timeout', 'Expect Error', 'Input']}>
            {dataset.cases.map(c => (
              <Tr key={c.id}>
                <Td>
                  <span className="font-medium text-slate-200">{c.name ?? '(unnamed)'}</span>
                  <p className="font-mono text-xs text-slate-500 mt-0.5">{c.id.slice(0, 10)}…</p>
                </Td>
                <Td><Badge variant="info">{c.assertion_type}</Badge></Td>
                <Td>
                  <div className="flex flex-wrap gap-1">
                    {c.tags.map(tag => (
                      <Badge key={tag} variant="neutral">{tag}</Badge>
                    ))}
                  </div>
                </Td>
                <Td>{c.timeout_ms ? `${c.timeout_ms}ms` : 'default'}</Td>
                <Td>{c.expect_error ? <span className="text-amber-400">yes</span> : <span className="text-slate-500">no</span>}</Td>
                <Td>
                  <div className="max-w-xs overflow-hidden">
                    <CodeBlock value={c.input} />
                  </div>
                </Td>
              </Tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
