import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Render markdown câu trả lời RAG. Link mở tab mới. Style ở .prose-answer (index.css).
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-answer text-base">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ ...props }) => <a target="_blank" rel="noreferrer" {...props} />,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
