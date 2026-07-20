import { useMemo } from 'react';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { Conversation, Message, RetrievedMemory } from '@/lib/types';

type ConversationsSlice = {
  conversations: Conversation[];
  activeId: string | null;
  setActive: (id: string | null) => void;
  addConversation: (conversation: Conversation) => void;
};

type ChatSlice = {
  messagesByConversation: Record<string, Message[]>;
  isStreaming: boolean;
  lastRetrievedContext: RetrievedMemory[];
  lastProceduralSkills: string[];
  apiLatencyMs: number | null;
  setMessages: (conversationId: string, messages: Message[]) => void;
  appendMessage: (conversationId: string, message: Message) => void;
  setStreaming: (value: boolean) => void;
  setLastRetrieval: (context: RetrievedMemory[]) => void;
  setLastProceduralSkills: (skills: string[]) => void;
  setApiLatencyMs: (value: number | null) => void;
};

type SoundSlice = {
  soundEnabled: boolean;
  setSoundEnabled: (value: boolean) => void;
  toggleSoundEnabled: () => void;
};

type AppState = ConversationsSlice & ChatSlice & SoundSlice;

export const EMPTY_MESSAGES: Message[] = [];
const EMPTY_RETRIEVAL: RetrievedMemory[] = [];

const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      conversations: [],
      activeId: null,
      messagesByConversation: {},
      isStreaming: false,
      lastRetrievedContext: [],
      lastProceduralSkills: [],
      apiLatencyMs: null,
      soundEnabled: false,
      setActive: (id) => set({ activeId: id }),
      addConversation: (conversation) =>
        set((state) => ({
          conversations: state.conversations.some((item) => item.id === conversation.id)
            ? state.conversations
            : [...state.conversations, conversation],
        })),
      setMessages: (conversationId, messages) =>
        set((state) => ({
          messagesByConversation: {
            ...state.messagesByConversation,
            [conversationId]: messages,
          },
        })),
      appendMessage: (conversationId, message) =>
        set((state) => ({
          messagesByConversation: {
            ...state.messagesByConversation,
            [conversationId]: [...(state.messagesByConversation[conversationId] ?? []), message],
          },
        })),
      setStreaming: (value) => set({ isStreaming: value }),
      setLastRetrieval: (context) => set({ lastRetrievedContext: context }),
      setLastProceduralSkills: (skills) => set({ lastProceduralSkills: skills }),
      setApiLatencyMs: (value) => set({ apiLatencyMs: value }),
      setSoundEnabled: (value) => set({ soundEnabled: value }),
      toggleSoundEnabled: () => set((state) => ({ soundEnabled: !state.soundEnabled })),
    }),
    {
      name: 'synapse-sound-settings',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ soundEnabled: state.soundEnabled }),
    },
  ),
);

export function useActiveConversation() {
  return useAppStore((state) => state.conversations.find((conversation) => conversation.id === state.activeId) ?? null);
}

export function useChatMessages() {
  return useAppStore((state) => {
    if (!state.activeId) {
      return EMPTY_MESSAGES;
    }

    return state.messagesByConversation[state.activeId] ?? EMPTY_MESSAGES;
  });
}

export function useLastRetrieval() {
  return useAppStore((state) => state.lastRetrievedContext ?? EMPTY_RETRIEVAL);
}

export function useIsStreaming() {
  return useAppStore((state) => state.isStreaming);
}

export function useSoundEnabled() {
  return useAppStore((state) => state.soundEnabled);
}

export function useConversationActions() {
  const setActive = useAppStore((state) => state.setActive);
  const addConversation = useAppStore((state) => state.addConversation);
  const setMessages = useAppStore((state) => state.setMessages);
  const appendMessage = useAppStore((state) => state.appendMessage);
  const setStreaming = useAppStore((state) => state.setStreaming);
  const setLastRetrieval = useAppStore((state) => state.setLastRetrieval);
  const setLastProceduralSkills = useAppStore((state) => state.setLastProceduralSkills);

  return useMemo(
    () => ({
      setActive,
      addConversation,
      setMessages,
      appendMessage,
      setStreaming,
      setLastRetrieval,
      setLastProceduralSkills,
    }),
    [addConversation, appendMessage, setActive, setLastProceduralSkills, setLastRetrieval, setMessages, setStreaming],
  );
}

export default useAppStore;
