'use client';

import { useState } from 'react';
import { parseTrialCriteria, parseFromNct, EXAMPLES } from '../lib/api';
import type { TrialistHybridResponse, TrialistHybridNctResponse } from '../types';

type InputMode = 'nct' | 'criteria';

export default function TrialistHybridParser() {
  const [mode, setMode] = useState<InputMode>('nct');
  const [criteria, setCriteria] = useState('');
  const [nctId, setNctId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TrialistHybridResponse | TrialistHybridNctResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetchedCriteria, setFetchedCriteria] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setFetchedCriteria(null);

    try {
      if (mode === 'nct') {
        const response = await parseFromNct(nctId);
        setResult(response);
        setFetchedCriteria(response.eligibility_criteria);
      } else {
        const response = await parseTrialCriteria({
          raw_criteria: criteria,
          nct_id: nctId || undefined,
        });
        setResult(response);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const loadExample = (key: keyof typeof EXAMPLES) => {
    const example = EXAMPLES[key];
    setCriteria(example.criteria);
    setNctId(example.nctId);
    setMode('criteria');
  };

  const isNctResponse = (res: TrialistHybridResponse | TrialistHybridNctResponse): res is TrialistHybridNctResponse => {
    return 'eligibility_criteria' in res;
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Trialist Hybrid Parser</h1>
        <p className="text-gray-600">
          Convert clinical trial criteria to executable MIMIC-IV SQL queries
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
        <div className="mb-6">
          <label className="block text-sm font-semibold mb-3 text-gray-700">
            Input Mode
          </label>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setMode('nct')}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                mode === 'nct'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              🆔 NCT ID (Auto-fetch)
            </button>
            <button
              type="button"
              onClick={() => setMode('criteria')}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                mode === 'criteria'
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              ✍️ Manual Input
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === 'nct' ? (
            <div className="mb-6">
              <label className="block text-sm font-semibold mb-2 text-gray-700">
                NCT ID
              </label>
              <input
                type="text"
                value={nctId}
                onChange={(e) => setNctId(e.target.value)}
                className="w-full p-4 border-2 border-gray-300 rounded-lg font-mono text-lg focus:border-blue-500 focus:outline-none"
                placeholder="NCT03389555"
                pattern="NCT\d{8}"
                required
              />
              <p className="text-sm text-gray-500 mt-2">
                💡 Automatically fetches eligibility criteria from ClinicalTrials.gov
              </p>
            </div>
          ) : (
            <>
              <div className="mb-4">
                <label className="block text-sm font-semibold mb-2 text-gray-700">
                  Clinical Trial Criteria
                </label>
                <textarea
                  value={criteria}
                  onChange={(e) => setCriteria(e.target.value)}
                  className="w-full p-4 border-2 border-gray-300 rounded-lg font-mono text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="Inclusion: Age >= 18 years, Septic shock..."
                  rows={6}
                  required
                />
              </div>
              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2 text-gray-700">
                  NCT ID (Optional)
                </label>
                <input
                  type="text"
                  value={nctId}
                  onChange={(e) => setNctId(e.target.value)}
                  className="w-full p-3 border-2 border-gray-300 rounded-lg font-mono focus:border-blue-500 focus:outline-none"
                  placeholder="NCT03389555"
                  pattern="NCT\d{8}"
                />
              </div>
            </>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '⏳ Processing...' : mode === 'nct' ? '🚀 Fetch & Parse' : '🚀 Parse Criteria'}
            </button>

            {mode === 'criteria' && Object.entries(EXAMPLES).map(([key, example]) => (
              <button
                key={key}
                type="button"
                onClick={() => loadExample(key as keyof typeof EXAMPLES)}
                className="px-4 py-3 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition-colors"
              >
                {example.label}
              </button>
            ))}
          </div>
        </form>
      </div>

      {loading && (
        <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-6 mb-6 animate-pulse">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-blue-800 font-semibold text-lg">
              {mode === 'nct'
                ? 'Fetching from ClinicalTrials.gov and processing...'
                : 'Processing criteria through 3-stage pipeline...'}
            </p>
          </div>
          <p className="text-sm text-blue-600 ml-9">
            Stage 1: Extraction → Stage 2: Mapping → Stage 3: Validation
          </p>
          <p className="text-sm text-blue-500 ml-9 mt-1">
            {mode === 'nct' ? 'This may take 15-40 seconds' : 'This may take 10-30 seconds'}
          </p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6 mb-6">
          <p className="text-red-800 font-semibold text-lg mb-2">❌ Error</p>
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {fetchedCriteria && (
        <div className="bg-purple-50 border-2 border-purple-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-3 text-purple-900">
            📋 Fetched Eligibility Criteria
          </h2>
          <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono bg-white p-4 rounded border">
            {fetchedCriteria}
          </pre>
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-lg p-6 shadow-lg">
            <h2 className="text-2xl font-bold mb-4 text-gray-800">📊 Pipeline Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm text-gray-600 mb-1">Total Criteria</p>
                <p className="text-3xl font-bold text-gray-900">{result.summary.total_criteria}</p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm text-gray-600 mb-1">Extraction Rate</p>
                <p className="text-3xl font-bold text-blue-600">
                  {(result.summary.stage1_extraction_rate * 100).toFixed(0)}%
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm text-gray-600 mb-1">Mapping Rate</p>
                <p className="text-3xl font-bold text-purple-600">
                  {(result.summary.stage2_mapping_rate * 100).toFixed(0)}%
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm text-gray-600 mb-1">Validation Rate</p>
                <p className="text-3xl font-bold text-green-600">
                  {(result.summary.stage3_validation_rate * 100).toFixed(0)}%
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm text-gray-600 mb-1">Avg Confidence</p>
                <p className="text-xl font-bold text-indigo-600">
                  {(result.summary.avg_confidence * 100).toFixed(0)}%
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm text-gray-600 mb-1">Execution Time</p>
                <p className="text-xl font-bold text-orange-600">
                  {result.summary.execution_time_seconds.toFixed(1)}s
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-2xl font-bold text-gray-800">
              🔍 Validation Results ({result.validations.length})
            </h2>
            {result.validations.map((validation, index) => {
              const statusConfig = {
                passed: { bg: 'bg-green-50', border: 'border-green-300', icon: '✅', color: 'text-green-700' },
                warning: { bg: 'bg-yellow-50', border: 'border-yellow-300', icon: '⚠️', color: 'text-yellow-700' },
                needs_review: { bg: 'bg-orange-50', border: 'border-orange-300', icon: '🔍', color: 'text-orange-700' },
                failed: { bg: 'bg-red-50', border: 'border-red-300', icon: '❌', color: 'text-red-700' },
              };
              const config = statusConfig[validation.validation_status];

              return (
                <div key={index} className={`${config.bg} border-2 ${config.border} rounded-lg p-6 shadow-md`}>
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <p className="font-bold text-lg text-gray-800">{config.icon} {validation.criterion_id}</p>
                      <p className={`text-sm font-semibold ${config.color} uppercase`}>
                        {validation.validation_status.replace('_', ' ')}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">Confidence</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {(validation.confidence_score * 100).toFixed(0)}%
                      </p>
                    </div>
                  </div>

                  {validation.sql_query && (
                    <div className="mt-4">
                      <p className="text-sm font-semibold mb-2 text-gray-700 flex items-center gap-2">
                        <span>🗄️ Generated SQL:</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(validation.sql_query!)}
                          className="text-xs px-2 py-1 bg-gray-700 text-white rounded hover:bg-gray-800"
                        >
                          Copy
                        </button>
                      </p>
                      <pre className="p-4 bg-gray-900 text-green-400 rounded-lg overflow-x-auto text-sm font-mono shadow-inner">
                        {validation.sql_query}
                      </pre>
                    </div>
                  )}

                  {validation.warnings.length > 0 && (
                    <div className="mt-4 bg-yellow-100 border border-yellow-300 rounded p-3">
                      <p className="text-sm font-semibold mb-2 text-yellow-800">⚠️ Warnings:</p>
                      <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                        {validation.warnings.map((warning, i) => <li key={i}>{warning}</li>)}
                      </ul>
                    </div>
                  )}

                  {validation.flags.length > 0 && (
                    <div className="mt-4 bg-red-100 border border-red-300 rounded p-3">
                      <p className="text-sm font-semibold mb-2 text-red-800">🚩 Flags:</p>
                      <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                        {validation.flags.map((flag, i) => <li key={i}>{flag}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {(result.workspace_path || (isNctResponse(result) && (result.corpus_path || result.metadata_path))) && (
            <div className="bg-gray-50 border border-gray-300 rounded-lg p-4 space-y-2">
              <p className="text-sm text-gray-600 font-semibold mb-2">💾 Saved Files:</p>
              {result.workspace_path && (
                <div>
                  <p className="text-xs text-gray-500">Pipeline Output:</p>
                  <p className="font-mono text-sm text-gray-800 break-all">{result.workspace_path}</p>
                </div>
              )}
              {isNctResponse(result) && result.corpus_path && (
                <div>
                  <p className="text-xs text-gray-500">Corpus:</p>
                  <p className="font-mono text-sm text-gray-800 break-all">{result.corpus_path}</p>
                </div>
              )}
              {isNctResponse(result) && result.metadata_path && (
                <div>
                  <p className="text-xs text-gray-500">Metadata:</p>
                  <p className="font-mono text-sm text-gray-800 break-all">{result.metadata_path}</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
