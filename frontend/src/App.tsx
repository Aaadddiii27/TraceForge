import { Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import OverviewPage from '@/pages/Overview';
import ExecutionsPage from '@/pages/Executions';
import ExecutionDetailPage from '@/pages/ExecutionDetail';
import EvaluationsPage from '@/pages/Evaluations';
import DatasetDetailPage from '@/pages/DatasetDetail';
import EvaluationRunDetailPage from '@/pages/EvaluationRunDetail';
import EvaluationComparePage from '@/pages/EvaluationCompare';
import ToolRegistryPage from '@/pages/Tools';
import ObservabilityPage from '@/pages/Observability';
import HealthPage from '@/pages/Health';

export default function App() {
  return <Layout><Routes>
    <Route path="/" element={<OverviewPage />} />
    <Route path="/executions" element={<ExecutionsPage />} />
    <Route path="/executions/:id" element={<ExecutionDetailPage />} />
    <Route path="/evaluations" element={<EvaluationsPage />} />
    <Route path="/evaluations/datasets/:id" element={<DatasetDetailPage />} />
    <Route path="/evaluations/runs/:id" element={<EvaluationRunDetailPage />} />
    <Route path="/evaluations/compare/:runAId/:runBId" element={<EvaluationComparePage />} />
    <Route path="/tools" element={<ToolRegistryPage />} />
    <Route path="/observability" element={<ObservabilityPage />} />
    <Route path="/health" element={<HealthPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></Layout>;
}
