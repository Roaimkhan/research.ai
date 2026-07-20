import { useMutation } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { sendChatMessage } from '@/lib/api';
import type { ChatRequest, Message } from '@/lib/types';
import useAppStore from '@/store/useAppStore';

export function useChat() {
  const [draft, setDraft] = useState('');
  const activeId = useAppStore((state) => state.activeId);
  const appendMessage = useAppStore((state) => state.appendMessage);
  const setMessages = useAppStore((state) => state.setMessages);
  const setStreaming = useAppStore((state) => state.setStreaming);
  const setLastRetrieval = useAppStore((state) => state.setLastRetrieval);
  const setLastProceduralSkills = useAppStore((state) => state.setLastProceduralSkills);

  const mutation = useMutation({
    mutationFn: async (payload: ChatRequest) => sendChatMessage(payload),
    onMutate: async (payload) => {
      if (!activeId) {
        return;
      }

      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: payload.message,
        created_at: new Date().toISOString(),
      };

      appendMessage(activeId, userMessage);
      setStreaming(true);
      return { userMessage };
    },
    onSuccess: (data) => {
      if (!activeId) {
        return;
      }

      const assistantMessage: Message = {
        id: `msg-${Date.now()}-assistant`,
        role: 'assistant',
        content: data.response.messages?.[data.response.messages.length - 1]?.content ?? '',
        created_at: new Date().toISOString(),
        metadata: {
          retrieval: data.response.retrieved_context,
          skills: data.response.retrieved_procedural_skills,
        },
      };

      appendMessage(activeId, assistantMessage);
      setMessages(activeId, [...(useAppStore.getState().messagesByConversation[activeId] ?? []), assistantMessage]);
      setLastRetrieval(data.response.retrieved_context);
      setLastProceduralSkills(data.response.retrieved_procedural_skills);
      setStreaming(false);
      setDraft('');
    },
    onError: (_error, payload) => {
      if (!activeId) {
        return;
      }

      setStreaming(false);
      setDraft(payload.message);
    },
  });

  return useMemo(
    () => ({
      draft,
      setDraft,
      sendMessage: (message: string) => {
        if (!activeId) {
          return;
        }

        mutation.mutate({
          message,
          user_id: 'local-user',
          conversation_id: activeId,
        });
      },
      isPending: mutation.isPending,
      isError: mutation.isError,
      error: mutation.error,
    }),
    [activeId, draft, mutation.error, mutation.isError, mutation.isPending, mutation],
  );
}
