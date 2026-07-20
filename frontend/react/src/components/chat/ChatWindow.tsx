import { useEffect, useMemo } from 'react';
import { useAutoScroll } from '@/hooks/useAutoScroll';
import { useChat } from '@/hooks/useChat';
import useAppStore, { useActiveConversation, useChatMessages, useIsStreaming } from '@/store/useAppStore';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { EmptyState } from './EmptyState';
import { MessageComposer } from './MessageComposer';
import { TopBar } from '@/components/layout/TopBar';
import { playMessageSound } from '@/lib/soundEngine';

interface ChatWindowProps {
  onToggleSidebar?: () => void;
  onToggleMemory?: () => void;
}

function ChatWindow({ onToggleSidebar, onToggleMemory }: ChatWindowProps) {
  const messages = useChatMessages();
  const isStreaming = useIsStreaming();
  const activeConversation = useActiveConversation();
  const { draft, setDraft, sendMessage, isPending } = useChat();
  const viewportRef = useAutoScroll<HTMLDivElement>({ enabled: true, dependency: messages.length });
  const soundEnabled = useAppStore((state) => state.soundEnabled);

  useEffect(() => {
    if (messages.length > 0 && isStreaming && soundEnabled) {
      playMessageSound();
    }
  }, [isStreaming, messages.length, soundEnabled]);

  const content = useMemo(() => {
    if (messages.length === 0) {
      return <EmptyState />;
    }

    return (
      <div className="space-y-1 py-2">
        {messages.map((message, index) => (
          <MessageBubble key={message.id} message={message} index={index} isStreaming={isStreaming && message.role === 'assistant' && message.id === messages[messages.length - 1]?.id} />
        ))}
        {isPending ? <TypingIndicator /> : null}
      </div>
    );
  }, [isPending, isStreaming, messages]);

  return (
    <section className="flex h-full flex-col overflow-hidden rounded-panel border border-hairline bg-ink">
      <TopBar
        title={activeConversation?.title ?? 'Synapse transcript'}
        status={isStreaming ? 'connected' : 'idle'}
        className="m-3"
        {...(onToggleSidebar ? { onToggleSidebar } : {})}
        {...(onToggleMemory ? { onToggleMemory } : {})}
      />
      <div className="flex-1 overflow-hidden">
        <ScrollArea ref={viewportRef} className="h-full">
          <div className="min-h-full px-2 py-2">{content}</div>
        </ScrollArea>
      </div>
      <MessageComposer value={draft} onChange={setDraft} onSend={sendMessage} disabled={isPending} />
    </section>
  );
}

export { ChatWindow };
