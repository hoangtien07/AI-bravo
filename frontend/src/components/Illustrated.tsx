// Tái dựng đoạn help NGUYÊN VĂN: text + ảnh xen kẽ ĐÚNG vị trí token ⟦IMG:key⟧
// (port từ _render_illustrated trong app.py). Ảnh render từ URL gốc — KHÔNG qua LLM.
import type { Hit, ImageRef } from "../types";
import { Markdown } from "./Markdown";

const IMG_TOKEN = /⟦IMG:([^⟧]+)⟧/;
const PATH_PREFIX = /^\[[^\]]*\]\n/; // tiền tố breadcrumb "[path]\n" do ingest thêm

export function Illustrated({ hit }: { hit: Hit }) {
  const imgByKey = new Map<string, ImageRef>((hit.images || []).map((im) => [im.key, im]));
  const text = hit.text.replace(PATH_PREFIX, "");
  // split giữ lại capture group (key ảnh) — phần tử lẻ là key, chẵn là text.
  const parts = text.split(IMG_TOKEN);

  return (
    <div className="space-y-3">
      {parts.map((part, i) => {
        const im = imgByKey.get(part);
        if (im) {
          return (
            <figure key={i} className="my-2">
              <img
                src={im.url}
                alt={im.alt || ""}
                loading="lazy"
                className="max-w-full rounded-lg border border-line"
              />
              {im.alt && (
                <figcaption className="mt-1 text-xs text-ink-400">{im.alt}</figcaption>
              )}
            </figure>
          );
        }
        return part.trim() ? <Markdown key={i}>{part.trim()}</Markdown> : null;
      })}
    </div>
  );
}
