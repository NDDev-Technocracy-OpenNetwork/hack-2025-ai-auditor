'use client';

import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, Plus, Edit, Trash2, Database, Filter } from 'lucide-react';

interface Prompt {
  id: string;
  name: string;
  description: string;
  content: string;
  format_type: string;
  language: string;
  tags: string[];
  created_at: string;
}

export default function PromptBasePage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Mock data for demo
  useEffect(() => {
    setPrompts([
      {
        id: '1',
        name: 'Python Coding Assistant',
        description: 'A comprehensive prompt for Python code generation and debugging',
        content: 'You are an expert Python developer. Help users write clean, efficient Python code...',
        format_type: 'text',
        language: 'en',
        tags: ['python', 'coding', 'assistant'],
        created_at: '2024-01-15T10:30:00Z',
      },
      {
        id: '2',
        name: 'JavaScript Helper',
        description: 'Frontend development assistance with JavaScript and React',
        content: 'You are a frontend development expert specializing in JavaScript and React...',
        format_type: 'markdown',
        language: 'en',
        tags: ['javascript', 'web', 'frontend', 'react'],
        created_at: '2024-01-14T15:45:00Z',
      },
      {
        id: '3',
        name: 'Article Writing Template',
        description: 'Template for generating high-quality technical articles',
        content: 'Write a comprehensive technical article about [TOPIC]. Include introduction...',
        format_type: 'xml',
        language: 'en',
        tags: ['writing', 'content', 'technical'],
        created_at: '2024-01-13T09:20:00Z',
      },
    ]);
  }, []);

  const allTags = Array.from(new Set(prompts.flatMap(p => p.tags)));

  const filteredPrompts = prompts.filter(prompt => {
    const matchesSearch = searchQuery === '' ||
      prompt.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.content.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesTags = selectedTags.length === 0 ||
      selectedTags.some(tag => prompt.tags.includes(tag));

    return matchesSearch && matchesTags;
  });

  const toggleTag = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Prompt-base</h1>
            <p className="text-gray-600">Manage and organize your prompt library</p>
          </div>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Add New Prompt
          </Button>
        </div>

        {/* Search and Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  type="text"
                  placeholder="Search prompts by name, description, or content..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Tag Filters */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Filter className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-700">Filter by tags:</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {allTags.map(tag => (
                    <button
                      key={tag}
                      onClick={() => toggleTag(tag)}
                      className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                        selectedTags.includes(tag)
                          ? 'bg-blue-100 border-blue-300 text-blue-700'
                          : 'bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>Total: {prompts.length} prompts</span>
                <span>Filtered: {filteredPrompts.length} prompts</span>
                {selectedTags.length > 0 && (
                  <button
                    onClick={() => setSelectedTags([])}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Prompt List */}
        <div className="grid gap-4">
          {filteredPrompts.map((prompt) => (
            <Card key={prompt.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      <Database className="h-5 w-5 text-blue-600" />
                      {prompt.name}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {prompt.description}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="outline" size="sm">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Content Preview */}
                  <div className="bg-gray-50 p-3 rounded text-sm">
                    <p className="text-gray-700 line-clamp-2">
                      {prompt.content.length > 150
                        ? `${prompt.content.substring(0, 150)}...`
                        : prompt.content
                      }
                    </p>
                  </div>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1">
                    {prompt.tags.map(tag => (
                      <span
                        key={tag}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* Metadata */}
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <div className="flex gap-4">
                      <span>Format: {prompt.format_type}</span>
                      <span>Language: {prompt.language}</span>
                    </div>
                    <span>Created: {new Date(prompt.created_at).toLocaleDateString()}</span>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-2 border-t">
                    <Button variant="outline" size="sm">
                      Analyze
                    </Button>
                    <Button variant="outline" size="sm">
                      Check Conflicts
                    </Button>
                    <Button variant="outline" size="sm">
                      View Relations
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Empty State */}
        {filteredPrompts.length === 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <Database className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">
                  {searchQuery || selectedTags.length > 0
                    ? 'No prompts match your search criteria'
                    : 'Your prompt-base is empty'
                  }
                </p>
                <p className="text-sm text-gray-500">
                  {searchQuery || selectedTags.length > 0
                    ? 'Try adjusting your search or filters'
                    : 'Add your first prompt to get started'
                  }
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
