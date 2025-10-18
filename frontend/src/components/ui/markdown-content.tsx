/**
 * Markdown Content Component
 *
 * Renders markdown text with proper formatting for:
 * - Headers (##, ###)
 * - Bold (**text**)
 * - Italic (*text*)
 * - Lists (numbered and bulleted)
 * - Code blocks
 */

'use client';

import { useMemo } from 'react';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  const htmlContent = useMemo(() => {
    if (!content) return '';

    let html = content;

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3 class="text-sm font-semibold mb-2 mt-3">$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 class="text-base font-semibold mb-2 mt-4">$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1 class="text-lg font-bold mb-3 mt-4">$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>');

    // Italic
    html = html.replace(/\*([^*]+?)\*/g, '<em class="italic">$1</em>');

    // Numbered lists
    html = html.replace(/^\d+\.\s+(.+)$/gm, '<li class="ml-4">$1</li>');
    html = html.replace(/(<li class="ml-4">.*<\/li>\n?)+/g, '<ol class="list-decimal list-inside space-y-1 my-2">$&</ol>');

    // Bullet lists
    html = html.replace(/^[-*]\s+(.+)$/gm, '<li class="ml-4">$1</li>');
    html = html.replace(/(<li class="ml-4">.*<\/li>\n?)+/g, '<ul class="list-disc list-inside space-y-1 my-2">$&</ul>');

    // Paragraphs (wrap text blocks that aren't already wrapped)
    html = html
      .split('\n\n')
      .map((block) => {
        if (
          block.startsWith('<h') ||
          block.startsWith('<ul') ||
          block.startsWith('<ol') ||
          block.startsWith('<li') ||
          block.trim() === ''
        ) {
          return block;
        }
        return `<p class="mb-2">${block}</p>`;
      })
      .join('\n');

    return html;
  }, [content]);

  return (
    <div
      className={`prose prose-sm max-w-none dark:prose-invert ${className}`}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}
