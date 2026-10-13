'use client';

import { useState } from 'react';
import { Editor } from '@monaco-editor/react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAppStore, ApiService } from '@/lib/store';
import { PromptSession } from '@/lib/types';
import { Loader2, Play, Download, Save, CheckCircle, AlertTriangle, MessageSquare } from 'lucide-react';

export default function AnalyzePage() {
  const {
    currentSession,
    setCurrentSession,
    updateAnalysis,
    isLoading,
    setLoading,
    error,
    setError
  } = useAppStore();

  const [promptText, setPromptText] = useState('');
  const [selectedPatches, setSelectedPatches] = useState<string[]>([]);

  // Helper function to safely format numbers
  const formatNumber = (value: unknown, decimals: number = 1): string => {
    if (typeof value === 'number' && !isNaN(value)) {
      return value.toFixed(decimals);
    }
    return 'N/A';
  };

  const handleAnalyze = async () => {
    if (!promptText.trim()) {
      setError('Please enter a prompt to analyze');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const sessionId = Date.now().toString();
      const session: PromptSession = {
        id: sessionId,
        originalPrompt: promptText,
        currentPrompt: promptText,
        appliedPatches: [],
        isAnalyzing: true,
      };

      setCurrentSession(session);

      const analysis = await ApiService.analyzePrompt(promptText);
      updateAnalysis(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPatches = async () => {
    if (!currentSession || selectedPatches.length === 0) return;

    setLoading(true);
    try {
      const result = await ApiService.applyPatches(currentSession.id, selectedPatches);
      setPromptText(result.improved_prompt);

      setCurrentSession({
        ...currentSession,
        currentPrompt: result.improved_prompt,
        appliedPatches: [...currentSession.appliedPatches, ...selectedPatches],
      });

      setSelectedPatches([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply patches');
    } finally {
      setLoading(false);
    }
  };

  const handlePatchSelection = (patchId: string) => {
    setSelectedPatches(prev =>
      prev.includes(patchId)
        ? prev.filter(id => id !== patchId)
        : [...prev, patchId]
    );
  };

  const applySafePatches = () => {
    if (!currentSession?.analysis) return;

    const safePatches = currentSession.analysis.patches
      .filter(patch => patch.type === 'safe')
      .map(patch => patch.id);

    setSelectedPatches(safePatches);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Prompt Analysis Studio</h1>
          <p className="text-gray-600">Analyze and optimize your prompts with AI-powered insights</p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Left Column - Editor */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Prompt Editor</CardTitle>
                <CardDescription>
                  Enter your prompt below and click analyze to get comprehensive insights
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="border rounded-md overflow-hidden">
                  <Editor
                    height="400px"
                    defaultLanguage="markdown"
                    value={promptText}
                    onChange={(value) => setPromptText(value || '')}
                    options={{
                      minimap: { enabled: false },
                      wordWrap: 'on',
                      lineNumbers: 'on',
                      theme: 'vs-light',
                    }}
                  />
                </div>
                <div className="flex gap-2 mt-4">
                  <Button
                    onClick={handleAnalyze}
                    disabled={isLoading || !promptText.trim()}
                    className="flex-1"
                  >
                    {isLoading ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Analyze Prompt
                  </Button>
                  {currentSession?.analysis && (
                    <>
                      <Button variant="outline">
                        <Save className="mr-2 h-4 w-4" />
                        Save to Prompt-base
                      </Button>
                      <Button variant="outline">
                        <Download className="mr-2 h-4 w-4" />
                        Export
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Error Display */}
            {error && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="pt-6">
                  <div className="flex items-center text-red-700">
                    <AlertTriangle className="mr-2 h-4 w-4" />
                    {error}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Analysis Results */}
          <div className="space-y-4">
            {currentSession?.analysis?.report && (
              <>
                {/* Metrics Dashboard */}
                <Card>
                  <CardHeader>
                    <CardTitle>Analysis Metrics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center p-3 bg-blue-50 rounded">
                        <div className="text-2xl font-bold text-blue-600">
                          {formatNumber(currentSession.analysis.report.judge_score?.score, 1)}
                        </div>
                        <div className="text-sm text-gray-600">Judge Score</div>
                      </div>
                      <div className="text-center p-3 bg-green-50 rounded">
                        <div className="text-2xl font-bold text-green-600">
                          {formatNumber(currentSession.analysis.report.semantic_entropy?.entropy, 2)}
                        </div>
                        <div className="text-sm text-gray-600">Entropy</div>
                      </div>
                      <div className="text-center p-3 bg-purple-50 rounded">
                        <div className="text-2xl font-bold text-purple-600">
                          {currentSession.analysis.report.semantic_entropy?.clusters ?? 'N/A'}
                        </div>
                        <div className="text-sm text-gray-600">Clusters</div>
                      </div>
                      <div className="text-center p-3 bg-orange-50 rounded">
                        <div className="text-2xl font-bold text-orange-600">
                          {currentSession.analysis.report.contradictions?.length ?? 0}
                        </div>
                        <div className="text-sm text-gray-600">Contradictions</div>
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-gray-50 rounded">
                      <div className="text-sm text-gray-600">
                        Language: <span className="font-medium">{currentSession.analysis.report.detected_language ?? 'Unknown'}</span> |
                        Format: <span className="font-medium">{currentSession.analysis.report.format_valid ? '✓ Valid' : '✗ Invalid'}</span> |
                        Translated: <span className="font-medium">{currentSession.analysis.report.translated ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Patch List */}
                {currentSession.analysis.patches && currentSession.analysis.patches.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      Improvement Suggestions
                      {currentSession.analysis.patches.some(p => p.type === 'safe') && (
                        <Button variant="outline" size="sm" onClick={applySafePatches}>
                          Apply All Safe Fixes
                        </Button>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {currentSession.analysis.patches.map((patch) => (
                        <div
                          key={patch.id}
                          className={`p-3 border rounded cursor-pointer transition-colors ${
                            selectedPatches.includes(patch.id)
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                          onClick={() => handlePatchSelection(patch.id)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`px-2 py-1 text-xs rounded ${
                                  patch.type === 'safe'
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-yellow-100 text-yellow-700'
                                }`}>
                                  {patch.type}
                                </span>
                                <span className="text-sm font-medium">{patch.category}</span>
                              </div>
                              <p className="text-sm text-gray-600 mb-1">{patch.description}</p>
                              <p className="text-xs text-gray-500">{patch.rationale}</p>
                            </div>
                            {selectedPatches.includes(patch.id) && (
                              <CheckCircle className="h-5 w-5 text-blue-500" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    {selectedPatches.length > 0 && (
                      <Button
                        onClick={handleApplyPatches}
                        disabled={isLoading}
                        className="w-full mt-4"
                      >
                        Apply Selected Patches ({selectedPatches.length})
                      </Button>
                    )}
                  </CardContent>
                </Card>
                )}

                {/* Clarification Questions */}
                {currentSession.analysis.questions && currentSession.analysis.questions.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <MessageSquare className="mr-2 h-5 w-5" />
                        Clarification Questions
                      </CardTitle>
                      <CardDescription>
                        Answer these questions to improve your prompt
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {currentSession.analysis.questions.map((question) => (
                          <div key={question.id} className="p-3 border rounded">
                            <div className="flex items-center gap-2 mb-2">
                              <span className={`px-2 py-1 text-xs rounded ${
                                question.priority === 'critical'
                                  ? 'bg-red-100 text-red-700'
                                  : question.priority === 'important'
                                  ? 'bg-yellow-100 text-yellow-700'
                                  : 'bg-gray-100 text-gray-700'
                              }`}>
                                {question.priority}
                              </span>
                              <span className="text-xs text-gray-500">{question.category}</span>
                            </div>
                            <p className="text-sm">{question.text}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}

            {/* Loading State */}
            {isLoading && !currentSession?.analysis && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600 mb-4" />
                    <p className="text-gray-600">Analyzing your prompt...</p>
                    <p className="text-sm text-gray-500 mt-2">
                      This usually takes 35-40 seconds
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Empty State */}
            {!currentSession && !isLoading && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center">
                    <Play className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                    <p className="text-gray-600">Enter a prompt and click analyze to get started</p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
