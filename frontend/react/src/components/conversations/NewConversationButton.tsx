import { PlusCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

function NewConversationButton() {
  return (
    <Button variant="primary" className="w-full justify-start gap-2 px-3">
      <PlusCircle className="size-4" />
      <span className="font-sans text-sm">Start a new thread</span>
    </Button>
  );
}

export { NewConversationButton };
