import { useEffect, useRef, useState } from 'react';
import { SendHorizontal } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { cn } from '@/lib/utils';

interface MessageComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (value: string) => void;
  disabled?: boolean;
}

function MessageComposer({ value, onChange, onSend, disabled = false }: MessageComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [rows, setRows] = useState(1);

  useEffect(() => {
    const lines = value.split('\n').length;
    setRows(Math.min(6, Math.max(1, lines)));
  }, [value]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if (value.trim()) {
        onSend(value);
      }
    }
  };

  return (
    <div className="border-t border-hairline bg-ink-raised/90 px-3 py-3">
      <div className="flex items-end gap-2 rounded-panel border border-hairline bg-ink/70 p-2">
        <textarea
          ref={textareaRef}
          value={value}
          aria-label="Message composer"
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={rows}
          placeholder="Transmit to Synapse"
          className="max-h-36 min-h-10 flex-1 resize-none border-none bg-transparent px-2 py-2 font-sans text-sm leading-6 text-text outline-none placeholder:text-text-muted"
        />
        <IconButton
          label="Send message"
          icon={<SendHorizontal className="size-4" />}
          onClick={() => {
            if (value.trim()) {
              onSend(value);
            }
          }}
          disabled={disabled || !value.trim()}
          className={cn('opacity-70', !disabled && value.trim() ? 'opacity-100' : 'opacity-40')}
        />
      </div>
    </div>
  );
}

export { MessageComposer };
