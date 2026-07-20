import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { NewConversationButton } from '@/components/conversations/NewConversationButton';
import { ConversationList } from '@/components/conversations/ConversationList';
import useAppStore from '@/store/useAppStore';

function Sidebar() {
  const conversations = useAppStore((state) => state.conversations);

  return (
    <aside className="flex h-full flex-col border-r border-hairline bg-ink-raised">
      <div className="flex items-center justify-between border-b border-hairline px-4 py-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-text-muted">Workspace</p>
          <h2 className="font-display text-xl text-parchment">Threads</h2>
        </div>
        <Button variant="ghost" size="sm" className="px-2 py-1">
          <Plus className="mr-1 size-4" />
          <span className="font-mono text-[10px] uppercase tracking-[0.2em]">new</span>
        </Button>
      </div>

      <div className="border-b border-hairline p-3">
        <NewConversationButton />
      </div>

      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <ConversationList conversations={conversations} />
        </ScrollArea>
      </div>
    </aside>
  );
}

export default Sidebar;
