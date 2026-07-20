import type { Conversation } from '@/lib/types';
import { ConversationItem } from './ConversationItem';

interface ConversationListProps {
  conversations: Conversation[];
}

function groupConversations(conversations: Conversation[]) {
  const now = Date.now();
  const today: Conversation[] = [];
  const thisWeek: Conversation[] = [];

  for (const conversation of conversations) {
    const updatedAt = conversation.updated_at ? new Date(conversation.updated_at).getTime() : now;
    const ageInDays = (now - updatedAt) / 86400000;

    if (ageInDays <= 1) {
      today.push(conversation);
    } else {
      thisWeek.push(conversation);
    }
  }

  return { today, thisWeek };
}

function ConversationList({ conversations }: ConversationListProps) {
  const { today, thisWeek } = groupConversations(conversations);

  if (conversations.length === 0) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="font-display text-lg italic text-parchment">Nothing recorded yet...</p>
        <p className="mt-2 font-sans text-sm text-text-muted">New conversations will appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 px-3 py-3" role="list">
      {today.length > 0 ? (
        <section>
          <p className="mb-2 px-2 font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">Today</p>
          <div className="space-y-2">
            {today.map((conversation, index) => (
              <div key={conversation.id} role="listitem">
                <ConversationItem conversation={conversation} index={index} />
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {thisWeek.length > 0 ? (
        <section>
          <p className="mb-2 px-2 font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">This Week</p>
          <div className="space-y-2">
            {thisWeek.map((conversation, index) => (
              <div key={conversation.id} role="listitem">
                <ConversationItem conversation={conversation} index={index + today.length} />
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

export { ConversationList };
