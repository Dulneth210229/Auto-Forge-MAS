import { useMemo } from "react";
import { html as diff2html } from "diff2html";
import "diff2html/bundles/css/diff2html.min.css";
import MarkdownViewer from "./MarkdownViewer";

const MAX_DIFF_TEXT_CHARS = 20_000; // mirrors diff_builder.py's own truncation cap

// The code_diff artifact is a single markdown "merge report" (see diff_builder.py's
// build_merge_report_markdown): everything above "## Full diff" is normal prose (verification
// status, steps, files changed); the diff itself is a fenced ```diff block at the end.
function splitMergeReport(markdown) {
  const match = markdown.match(/```diff\n([\s\S]*?)```/);

  if (!match) {
    return { prose: markdown, diffText: null };
  }

  const diffStart = markdown.indexOf(match[0]);
  return { prose: markdown.slice(0, diffStart), diffText: match[1] };
}

export default function DiffViewer({ content }) {
  const { prose, diffText } = useMemo(() => splitMergeReport(content), [content]);

  const diffHtml = useMemo(() => {
    if (!diffText) return null;

    try {
      return diff2html(diffText, {
        drawFileList: true,
        matching: "lines",
        outputFormat: "line-by-line",
      });
    } catch {
      return null;
    }
  }, [diffText]);

  const isTruncated = diffText && diffText.length >= MAX_DIFF_TEXT_CHARS;

  return (
    <div>
      <MarkdownViewer content={prose} />

      {isTruncated && (
        <p className="bg-yellow-50 dark:bg-yellow-500/10 text-yellow-800 dark:text-yellow-300 text-xs p-2 rounded mt-2 mb-2">
          This diff was truncated by the backend at {MAX_DIFF_TEXT_CHARS.toLocaleString()} characters
          -- the full diff is not available via this view.
        </p>
      )}

      {diffHtml ? (
        // diff2html's own bundled CSS renders a light-themed table regardless of app theme --
        // wrapped in a light card so it stays legible rather than half-blending into a dark page.
        <div className="mt-4 text-xs bg-white rounded-lg p-2 overflow-x-auto" dangerouslySetInnerHTML={{ __html: diffHtml }} />
      ) : (
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-4">No diff content found in this artifact.</p>
      )}
    </div>
  );
}
